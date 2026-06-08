# soul.py — SoulAG Gedächtnis & Automatische Lerneinheit (v3)
import json, threading, os, re, uuid, logging, time
from datetime import datetime
from gnom_hub.db import save_soul_fact, add_chat_message, get_active_project
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.core.config import WORKSPACE_DIR
from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts

_log = logging.getLogger("soul")

# ── Konfiguration ──────────────────────────────────────────────────────────
MAX_SOUL_FACTS       = 50      # Hartes Limit
MIN_VALUE_LENGTH     = 15      # Minimale Fakt-Länge (Zeichen)
DEDUP_THRESHOLD      = 0.88    # FAISS-Ähnlichkeits-Schwelle
HIGH_PRIO_MAX_AGE_DAYS = 30    # High-Fakten leben max 30 Tage
MED_PRIO_MAX_AGE_DAYS  = 14    # Medium-Fakten leben max 14 Tage
LOW_PRIO_MAX_AGE_DAYS  = 7     # Low-Fakten leben max 7 Tage

# Patterns, die NIEMALS gespeichert werden
BLOCKED_PATTERNS = [
    r"nicht\s+(?:schreib|erstel|ausführ|mach|erzeug)", r"(?:nur|ausschließlich)\s+(?:showbox|sb)\s",
    r"vorher\s+(?:frag|bestätig|erlaubnis)", r"um\s+erlaubnis\s+(?:frag|bitt)",
    r"(?:darf|kann|soll)\s+nicht\s+(?:schreib|editier|ausführ)",
    r"kein(?:e|en)?\s+(?:write|datei|schreib|zugriff)", r"frag\s+erst",
    r"blockade|verweigert", r"nicht\s+(?:als|im|in)\s+(?:\[WRITE|\[SHELL)",
]

BLOCKED_RE = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)

# ── Fact Scoring ───────────────────────────────────────────────────────────
PRIO_SCORE = {"high": 30, "medium": 15, "low": 5}

def _compute_score(priority: str, age_days: float, injection_count: int = 0) -> float:
    """Berechnet die Relevanz eines Fakts: höher = wichtiger."""
    age_penalty = age_days * 1.5  # älter = weniger relevant
    usage_bonus = min(injection_count * 3, 30)  # oft injiziert = relevanter (max 30)
    return PRIO_SCORE.get(priority, 10) + usage_bonus - age_penalty


# ── Periodische Hausputz-Funktion ─────────────────────────────────────────
_last_cleanup_time = 0
CLEANUP_INTERVAL = 3600  # 1 Stunde zwischen Hausputz

def _periodic_cleanup():
    """Löscht überalterte Fakten und reduziert Duplikate. Läuft max 1x/Stunde."""
    global _last_cleanup_time
    now = time.time()
    if now - _last_cleanup_time < CLEANUP_INTERVAL:
        return
    _last_cleanup_time = now

    try:
        from gnom_hub.db.connection import get_db_conn
        with get_db_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]
            if total == 0:
                return

            now_iso = datetime.now().isoformat()[:19]
            deleted = 0

            # 1. Alter-basierte Löschung
            for prio, max_days in [("low", LOW_PRIO_MAX_AGE_DAYS),
                                    ("medium", MED_PRIO_MAX_AGE_DAYS),
                                    ("high", HIGH_PRIO_MAX_AGE_DAYS)]:
                cutoff = datetime.now().isoformat()[:10]
                aged = conn.execute(
                    "SELECT key FROM soul_memory WHERE priority = ? AND timestamp < ?",
                    (prio, cutoff)
                ).fetchall()
                for a in aged:
                    conn.execute("DELETE FROM soul_memory WHERE key = ?", (a["key"],))
                if aged:
                    _log.info("[Soul] Aging: %d %s-priority facts deleted (>%dd old)", len(aged), prio, max_days)
                    deleted += len(aged)

            # 2. Score-basierte Löschung (nur wenn über Limit)
            remaining = conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]
            if remaining > MAX_SOUL_FACTS:
                rows = conn.execute(
                    "SELECT key, priority, timestamp FROM soul_memory ORDER BY timestamp ASC"
                ).fetchall()
                # Score berechnen und die schlechtesten löschen
                scored = []
                for r in rows:
                    try:
                        ts = r["timestamp"]
                        age_d = (datetime.now() - datetime.fromisoformat(ts.replace("Z", "+00:00").replace("T", " ")[:19])).days if ts else 0
                    except Exception:
                        age_d = 0
                    scored.append((r["key"], _compute_score(r["priority"], age_d, 0)))
                scored.sort(key=lambda x: x[1])
                to_delete = remaining - MAX_SOUL_FACTS
                for key, _score in scored[:to_delete]:
                    conn.execute("DELETE FROM soul_memory WHERE key = ?", (key,))
                _log.info("[Soul] Score-pruning: %d low-score facts deleted", to_delete)
                deleted += to_delete

            if deleted:
                conn.commit()
                _log.info("[Soul] Cleanup complete: %d facts removed (%d remaining)", deleted,
                         conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0])
    except Exception as e:
        _log.warning("[Soul] Periodic cleanup failed: %s", e)


# ── SoulAG Hauptklasse ────────────────────────────────────────────────────
class SoulAG:
    def __init__(self):
        self.name = "SoulAG"
        self._injections = {}
        self._recent_facts_cache = {}  # key -> (timestamp, value_hash) für schnelles Dedup

    def on_message(self, m: str, s: str):
        from gnom_hub.core.config import Config
        if Config.SUPERGNOM_MODE:
            return
        # SoulAG lernt aus JEDER Nachricht (nicht nur User), mit Rate-Limit
        import hashlib
        msg_hash = hashlib.md5(m.encode()).hexdigest()[:16]
        now = time.time()
        if not hasattr(self, '_last_seen_hash'):
            self._last_seen_hash = {}
        # Dedup: gleiche Nachricht nicht mehrfach lernen
        last = self._last_seen_hash.get(msg_hash, 0)
        if now - last < 15:
            return
        self._last_seen_hash[msg_hash] = now
        if len(self._last_seen_hash) > 500:
            oldest = min(self._last_seen_hash, key=self._last_seen_hash.get)
            del self._last_seen_hash[oldest]
        # User: immer, Agent: 80% Sampling (vorher 50%)
        if s.lower() == "user" or hash(msg_hash) % 100 < 80:
            self._pulse_status()
            threading.Thread(target=self._ex, args=(m,), daemon=True).start()

    def _pulse_status(self):
        """Macht SoulAG kurz sichtbar — Status auf busy → Karte pulsiert einmal."""
        try:
            import requests, os
            port = os.environ.get('GNOM_HUB_PORT', '3002')
            requests.put(f"http://127.0.0.1:{port}/api/agents/SoulAG/status?status=busy", timeout=2)
            # Timer für online in 2s (non-blocking)
            def _back():
                import time; time.sleep(2)
                try: requests.put(f"http://127.0.0.1:{port}/api/agents/SoulAG/status?status=online", timeout=2)
                except: pass
            threading.Thread(target=_back, daemon=True).start()
        except:
            pass

    def _val(self, k: str, v: str) -> bool:
        """Prüft ob ein Fakt gespeichert werden darf."""
        kl = k.lower()
        if len(v.strip()) < MIN_VALUE_LENGTH:
            return False
        if BLOCKED_RE.search(v):
            _log.info("[Soul] Blocked by pattern: %s", k)
            return False
        if k == "active_preset":
            return v in ["Web Development", "Graphic Design", "Audio Production",
                         "Video Production", "Marketing & Copy", "Content Creation",
                         "Research & Analysis"]
        return True

    def _is_dup(self, text: str) -> bool:
        """Prüft via FAISS ob ein semantisch ähnlicher Fakt existiert."""
        try:
            from gnom_hub.memory.embeddings import get_embedder
            return get_embedder().has_similar(text, threshold=DEDUP_THRESHOLD)
        except Exception:
            return False

    def _ex(self, m: str):
        """Extrahiert Fakten aus einer Chat-Nachricht (LLM-basiert)."""
        try:
            # 1. Periodischen Hausputz laufen lassen
            _periodic_cleanup()

            # 2. LLM-Call zur Fakt-Extraktion
            prompt = (
                f"Nachricht:\n\"\"\"\n{m}\n\"\"\"\n\n"
                "Extrahiere NUR relevante, langfristig nützliche Fakten.\n"
                "Keine Begrüßungen, keine flüchtigen Fehler, keine Wiederholungen.\n"
                "Antworte als JSON-Array:\n"
                '[\n  {"key": "prafix_schluessel", "value": "Präziser Fakt.", "priority": "high|medium|low", "target_agent": "CoderAG|WriterAG|ResearcherAG|EditorAG|all"}\n]\n'
                "Leeres Array [] wenn nichts relevant."
            )
            res = ask_router(
                prompt,
                sys=(
                    "SoulAG Fakt-Extraktor. Extrahiere präzise, eigenständige Fakten. "
                    "Priority: high=Projekt-entscheidend, medium=nützlich, low=kontextuell. "
                    "target_agent: 'all' oder spezifischer Worker. "
                    "NUR JSON-Array ausgeben."
                ),
                agent_name="SoulAG"
            ).content

            s, e = res.find("["), res.rfind("]")
            if s == -1 or e == -1:
                _log.debug("[Soul] No JSON array in LLM response")
                return

            facts = json.loads(res[s:e+1])
            saved = 0
            for f in facts:
                k, v = f.get("key", ""), f.get("value", "")
                p = f.get("priority", "medium").lower()
                target = f.get("target_agent", "all")
                if p not in ("high", "medium", "low"):
                    p = "medium"

                # Qualitäts-Check
                if not self._val(k, v):
                    continue

                # Dedup
                if self._is_dup(f"{k}: {v}"):
                    continue

                # Kurzzeit-Dedup Cache (gleicher Key in letzten 300s)
                cache_entry = self._recent_facts_cache.get(k)
                now = time.time()
                if cache_entry and (now - cache_entry[0] < 300) and cache_entry[1] == hash(v):
                    continue
                self._recent_facts_cache[k] = (now, hash(v))
                if len(self._recent_facts_cache) > 200:
                    oldest = min(self._recent_facts_cache, key=lambda x: self._recent_facts_cache[x][0])
                    del self._recent_facts_cache[oldest]

                # Speichern
                agent_name = "SoulAG" if target.lower() == "all" else target
                save_soul_fact(k, v, agent=agent_name, priority=p)
                saved += 1
                _log.debug("[Soul] Saved: %s [%s -> %s]", k, p, agent_name)

            if saved:
                _log.info("[Soul] %d facts saved", saved)
                try:
                    add_chat_message(get_active_project(), "SoulAG", "soulag", "chat",
                                     f"🧠 {saved} Fakten gelernt", {"type": "soul"})
                except:
                    pass

        except json.JSONDecodeError as e:
            _log.warning("[Soul] JSON error: %s", e)
        except Exception as e:
            _log.error("[Soul] Extraction failed: %s", e, exc_info=True)

    def inject_context(self, sys: str, msg: str, agent_name: str = None) -> str:
        """Reichert das System-Prompt mit relevanten Soul-Fakten an."""
        top_k = 6  # Reduziert (war 8)
        if agent_name:
            try:
                from gnom_hub.db import get_state_value
                settings = get_state_value("agent_settings", {}).get(agent_name.lower(), {})
                top_k = {1: 2, 2: 4, 3: 6, 4: 8, 5: 12}.get(settings.get("memory_strength", 3), 6)
            except Exception:
                pass

        # Nur Fakten mit Score > 0 holen (veraltete/low-score ignorieren)
        facts = retrieve_relevant_facts(msg, agent_name=agent_name, top_k=top_k)
        if agent_name and facts:
            for f in facts:
                key = (agent_name.lower(), f)
                self._injections[key] = self._injections.get(key, 0) + 1

            if len(self._injections) > 2000:
                keys_to_remove = sorted(self._injections.keys())[:1000]
                for k in keys_to_remove:
                    del self._injections[k]

        ctx = sys + ("\n\n=== RELEVANTE ERINNERUNGEN ===\n" + "\n".join(f"- {f}" for f in facts) if facts else "")
        m_ctx = [f"[Ref: @{d['name']} - {d['description']}]"
                 for k, d in self.get_definitions().items()
                 if k.lower() in [x.lower() for x in re.findall(r'@(\w+)', msg)]]
        return ctx + ("\n\n=== ERWÄHNTE AGENTEN ===\n" + "\n".join(m_ctx) if m_ctx else "")

    def emit_directive(self, target_agent: str, directive: str, ttl: int = 3600):
        """Sendet eine ZWC-Direktive fuer einen Ziel-Agenten.

        Die Direktive wird als Chat-Nachricht gepostet und ist fuer andere
        Agents via decode_soul() lesbar. SoulAG kann damit Agenten
        ausrichten oder an wichtige Regeln erinnern.
        """
        from gnom_hub.soul.zwc_soul import add_directive as _add_dir
        from gnom_hub.db import add_chat_message, get_active_project
        zwc = _add_dir(target_agent, directive, ttl)
        add_chat_message(get_active_project(), "SoulAG", "soulag", "directive",
                         f"🧠 Direktive fuer {target_agent}: {directive[:80]}{zwc}",
                         {"type": "directive", "target": target_agent})
        _log.info("[Soul] Directive emitted: %s -> %s: %s", target_agent, directive[:60], ttl)

    def get_definitions(self) -> dict:
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        return AGENT_DEFINITIONS


soul_instance = SoulAG()


# ── Evolution & Feedback (unverändert) ─────────────────────────────────────
def _save_rules(res: str, prefix=""):
    s, e = res.find("["), res.rfind("]")
    if s != -1 and e != -1:
        try:
            rules = json.loads(res[s:e+1])
            for f in rules:
                if f.get("agent") and f.get("rule"):
                    agent_name = f["agent"]
                    rule_text = prefix + f["rule"]
                    save_soul_fact(f"evolution_{agent_name}_{uuid.uuid4().hex[:6]}", rule_text, agent="GeneralAG")
                    add_chat_message(get_active_project(), "GeneralAG", "generalag", "chat",
                                     f"@user @SoulAG: Regel für {agent_name} gelernt: '{f['rule']}'")
                    try:
                        from gnom_hub.core.utils.evolution_v2 import create_version
                        create_version(agent_name, rule_text)
                    except Exception as ex:
                        logging.getLogger("db").error(f"[Soul] Failed promp version for {agent_name}: {ex}")
        except Exception as ex:
            logging.getLogger("db").error(f"[Soul] Failed to parse and save rules: {ex}")


def run_evolution(task: str, hist: str):
    from gnom_hub.core.config import Config
    if Config.SUPERGNOM_MODE:
        return
    try:
        _save_rules(ask_router(
            f"Analysiere '{task}' und Verlauf:\n{hist}\nVerbesserungen vorschlagen. NUR JSON: [{{\"agent\": \"Name\", \"rule\": \"Regel\"}}]",
            sys="Du bist Optimierer.", agent_name="GeneralAG"
        ).content)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in run_evolution: %s', e)


def handle_user_feedback(vote: str, comment: str):
    from gnom_hub.core.config import Config
    save_soul_fact(f"feedback_{uuid.uuid4().hex[:6]}", f"Vote: {vote} | {comment}", agent="User")
    add_chat_message(get_active_project(), "System", "system", "chat", f"@user Feedback: {vote} | {comment}")
    if Config.SUPERGNOM_MODE:
        return

    try:
        from gnom_hub.core.utils.evolution_v2 import update_version_score
        from gnom_hub.db import get_chat_history
        active_agents = set()
        history = get_chat_history(limit=40)
        for msg in history:
            sender = msg.get("sender")
            if sender and sender.lower() not in ["user", "system", "generalag", "soulag", "watchdogag", "securityag"]:
                from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
                for ag_key, ag_def in AGENT_DEFINITIONS.items():
                    if ag_def["name"].lower() == sender.lower():
                        active_agents.add(ag_def["name"])
        if not active_agents:
            active_agents = {"CoderAG", "WriterAG", "ResearcherAG", "EditorAG"}
        for agent in active_agents:
            update_version_score(agent, vote)
    except Exception as ex:
        logging.getLogger("db").error(f"[Soul] Failed version scores: {ex}")

    if comment.strip():
        try:
            _save_rules(ask_router(
                f"User-Feedback: '{comment}'. Verbesserungen vorschlagen. NUR JSON: [{{\"agent\": \"Name\", \"rule\": \"Regel\"}}]",
                sys="Du bist Optimierer.", agent_name="GeneralAG"
            ).content, "User-Feedback: ")
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in handle_user_feedback: %s', e)
