# soul.py — SoulAG Gedächtnis & Automatische Lerneinheit (v3)
import json, threading, os, re, uuid, logging, time
from datetime import datetime
from gnom_hub.db import add_chat_message, get_active_project
from gnom_hub.db.soul_repo import save_soul_fact_smart
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.core.config import WORKSPACE_DIR
from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts
from gnom_hub.soul.memory_layers import (
    get_cache, get_passive_db, get_rules_db, get_coordination_db,
    query_memory, save_fact_all_layers
)

_log = logging.getLogger("soul")

# JSON-Parser-Helper: toleriert Trailing-Content (Kommentare, Erklärungen
# hinter dem eigentlichen JSON-Array). Vor diesem Fix lieferte json.loads()
# "Extra data: line N column M (char X)" sobald das LLM nach dem JSON noch
# prose mitschickte — das wirkte wie "SoulAG antwortet nicht". raw_decode()
# liest EINEN JSON-Wert ab start_pos und ignoriert den Rest.
_JSON_DECODER = json.JSONDecoder()


def _parse_json_value(text: str, start_pos: int = 0):
    """Parst einen JSON-Wert ab start_pos. Gibt (obj, end_pos) oder (None, -1)."""
    if not text:
        return None, -1
    try:
        obj, end = _JSON_DECODER.raw_decode(text, start_pos)
        return obj, end
    except json.JSONDecodeError:
        return None, -1

# ── Konfiguration ──────────────────────────────────────────────────────────
MAX_SOUL_FACTS       = 100     # Hartes Limit (war 50)
MIN_VALUE_LENGTH     = 15      # Minimale Fakt-Länge (Zeichen)
DEDUP_THRESHOLD      = 0.85    # FAISS-Ähnlichkeits-Schwelle (war 0.88)
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
    age_penalty = age_days * 1.5
    usage_bonus = min(injection_count * 3, 30)
    return PRIO_SCORE.get(priority, 10) + usage_bonus - age_penalty


# ── Periodische Hausputz-Funktion ─────────────────────────────────────────
_last_cleanup_time = 0
CLEANUP_INTERVAL = 1800  # 30 Minuten zwischen Hausputz

def _periodic_cleanup():
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

            remaining = conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]
            if remaining > MAX_SOUL_FACTS:
                rows = conn.execute(
                    "SELECT key, priority, timestamp FROM soul_memory ORDER BY timestamp ASC"
                ).fetchall()
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
        # Layer 1 Cache beim Start befüllen
        threading.Thread(target=get_cache().warm_up, daemon=True).start()
        self._injections = {}
        self._recent_facts_cache = {}
        # v7.0: Stale-Task-Nudge-Loop — prüft alle 60s
        self._nudge_running = True
        threading.Thread(target=self._nudge_loop_runner, daemon=True).start()

    def _nudge_loop_runner(self):
        """Background-Loop: ruft _nudge_loop alle 60s auf."""
        while self._nudge_running:
            time.sleep(60)
            if self._nudge_running:
                try:
                    self._nudge_loop()
                except Exception as ex:
                    _log.error("[Soul] _nudge_loop_runner: %s", ex)

    def on_message(self, m: str, s: str):
        from gnom_hub.core.config import Config
        if Config.SUPERGNOM_MODE:
            return
        import hashlib
        msg_hash = hashlib.md5(m.encode()).hexdigest()[:16]
        now = time.time()
        if not hasattr(self, '_last_seen_hash'):
            self._last_seen_hash = {}

        # User-Messages: IMMER verarbeiten (kein 15s-Dedup)
        is_user = s.lower() == "user"
        if is_user:
            self._pulse_status()
            threading.Thread(target=self._ex, args=(m, True), daemon=True).start()
            return

        # Agent-Messages: 80% Sampling (war 65%)
        last = self._last_seen_hash.get(msg_hash, 0)
        if now - last < 15:
            return
        self._last_seen_hash[msg_hash] = now
        if len(self._last_seen_hash) > 500:
            oldest = min(self._last_seen_hash, key=self._last_seen_hash.get)
            del self._last_seen_hash[oldest]
        if hash(msg_hash) % 100 < 80:
            self._pulse_status()
            threading.Thread(target=self._ex, args=(m, False), daemon=True).start()

    def _pulse_status(self):
        try:
            import requests, os
            port = os.environ.get('GNOM_HUB_PORT', '3002')
            requests.put(f"http://127.0.0.1:{port}/api/agents/SoulAG/status?status=busy", timeout=2)
            def _back():
                import time; time.sleep(2)
                try: requests.put(f"http://127.0.0.1:{port}/api/agents/SoulAG/status?status=online", timeout=2)
                except: pass
            threading.Thread(target=_back, daemon=True).start()
        except:
            pass

    def _val(self, k: str, v: str) -> bool:
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
        try:
            from gnom_hub.memory.embeddings import get_embedder
            return get_embedder().has_similar(text, threshold=DEDUP_THRESHOLD)
        except Exception:
            return False

    def _ex(self, m: str, is_user: bool = False):
        """
        SoulAG v7.0 — PRIMARY: Task-Formulierung aus User-Input.
        SECONDARY: Fakten-Extraktion (bleibt für Kontext-Building).
        """
        import hashlib
        try:
            _periodic_cleanup()
            msg_hash = hashlib.md5(m.encode()).hexdigest()[:8]

            # ── TASK-FORMULIERUNG (PRIMARY, nur User-Messages) ──
            if is_user:
                task_prompt = (
                    f"User-Nachricht:\n\"\"\"\n{m}\n\"\"\"\n\n"
                    "Du bist SoulAG — der Orchestrator.\n"
                    "Analysiere: Was will der User WIRKLICH?\n"
                    "Formuliere daraus 1-3 konkrete Tasks.\n"
                    "Für jeden Task: Beschreibung + Ziel-Agent (CoderAG/WriterAG/ResearcherAG/EditorAG).\n"
                    "Antworte ALS REINES JSON-ARRAY:\n"
                    '[\n  {"task": "Konkrete Task-Beschreibung", "agent": "CoderAG"}\n]\n'
                    "Leeres Array [] wenn nichts zu tun ist."
                )
                try:
                    task_res = ask_router(
                        task_prompt,
                        sys=(
                            "SoulAG Task-Orchestrator v7.0. "
                            "Analysiere die wahre User-Absicht. "
                            "Formuliere präzise, ausführbare Tasks. "
                            "NUR JSON-Array ausgeben."
                        ),
                        agent_name="SoulAG"
                    ).content

                    task_s = task_res.find("[")
                    if task_s != -1:
                        tasks, _ = _parse_json_value(task_res, task_s)
                        if tasks is None:
                            tasks = []
                        for t in tasks:
                            task_desc = t.get("task", "").strip()
                            target = t.get("agent", "").strip()
                            if task_desc and target:
                                task_id = self._create_task(task_desc, m, target)
                                if task_id:
                                    self._dispatch_task(task_id, target, task_desc)
                                    _log.info("[Soul] Task erstellt + dispatcht: %s → %s", task_desc[:60], target)
                except Exception as ex:
                    _log.warning("[Soul] Task-Formulierung fehlgeschlagen: %s", ex)

            # ── FAKTEN-EXTRAKTION (SECONDARY) ──
            prompt = (
                f"Nachricht:\n\"\"\"\n{m}\n\"\"\"\n\n"
                "Extrahiere NUR relevante, langfristig nützliche Fakten.\n"
                "Keine Begrüßungen, keine flüchtigen Fehler, keine Wiederholungen.\n"
                "Antworte als JSON-Array:\n"
                '[\n  {"key": "praefix_schluessel", "value": "Praeziser Fakt.", "priority": "high|medium|low", "target_agent": "CoderAG|WriterAG|ResearcherAG|EditorAG|all"}\n]\n'
                "Leeres Array [] wenn nichts relevant."
            )
            res = ask_router(
                prompt,
                sys=(
                    "SoulAG Fakt-Extraktor. Extrahiere praezise, eigenstaendige Fakten. "
                    "Priority: high=Projekt-entscheidend, medium=nuetzlich, low=kontextuell. "
                    "target_agent: 'all' oder spezifischer Worker. "
                    "NUR JSON-Array ausgeben."
                ),
                agent_name="SoulAG"
            ).content

            s = res.find("[")
            if s == -1:
                _log.debug("[Soul] No JSON array in LLM response")
                return

            facts, _ = _parse_json_value(res, s)
            if facts is None:
                _log.debug("[Soul] JSON array parse failed, skipping")
                return
            saved = 0
            for f in facts:
                k, v = f.get("key", ""), f.get("value", "")
                p = f.get("priority", "medium").lower()
                target = f.get("target_agent", "all")
                if p not in ("high", "medium", "low"):
                    p = "medium"

                if not self._val(k, v):
                    continue

                if self._is_dup(f"{k}: {v}"):
                    continue

                cache_entry = self._recent_facts_cache.get(k)
                now = time.time()
                if cache_entry and (now - cache_entry[0] < 300) and cache_entry[1] == hash(v):
                    continue
                self._recent_facts_cache[k] = (now, hash(v))
                if len(self._recent_facts_cache) > 200:
                    oldest = min(self._recent_facts_cache, key=lambda x: self._recent_facts_cache[x][0])
                    del self._recent_facts_cache[oldest]

                agent_name = "SoulAG" if target.lower() == "all" else target
                save_fact_all_layers(k, v, p, agent_name)
                saved += 1
                _log.debug("[Soul] Saved: %s [%s -> %s]", k, p, agent_name)

            if saved:
                _log.info("[Soul] %d facts saved", saved)

        except json.JSONDecodeError as e:
            _log.warning("[Soul] JSON error: %s", e)
        except Exception as e:
            _log.error("[Soul] Extraction failed: %s", e, exc_info=True)

    def _create_task(self, description: str, source_message: str, assigned_to: str) -> str:
        """Erstellt einen Task in soul_tasks DB. Gibt Task-ID zurück."""
        try:
            import uuid
            from gnom_hub.db.connection import get_db_conn
            task_id = f"soul_{uuid.uuid4().hex[:10]}"
            now = time.time()
            with get_db_conn() as conn:
                conn.execute("""
                    INSERT INTO soul_tasks
                        (id, description, source_message, source_user, status,
                         assigned_to, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'open', ?, ?, ?)
                """, (task_id, description, source_message, "user", assigned_to, now, now))
                conn.commit()
            return task_id
        except Exception as ex:
            _log.error("[Soul] Task-Erstellung fehlgeschlagen: %s", ex)
            return None

    def _dispatch_task(self, task_id: str, target: str, description: str):
        """Dispatcht einen Task via swarm_comms dispatch_mention()."""
        try:
            from gnom_hub.agents.swarm.swarm_comms import dispatch_mention
            from gnom_hub.core.config import DB_PATH
            from gnom_hub.db import get_active_project
            proj = get_active_project() or "default"
            text = f"@{target} Task: {description} (ID: {task_id})"
            dispatch_mention(
                sender="SoulAG",
                text=text,
                context_id=proj,
                db_path=str(DB_PATH),
                current_depth=1,
            )
            _log.info("[Soul] Dispatcht: %s → %s", task_id, target)
        except Exception as ex:
            _log.error("[Soul] Task-Dispatch fehlgeschlagen: %s", ex)

    def _nudge_loop(self):
        """
        Prüft alle 60s ob Tasks stale sind (>5min open).
        Nudged Agenten bis 3x, dann status='blocked' → SecurityAG.
        """
        try:
            from gnom_hub.db.connection import get_db_conn
            now = time.time()
            stale_cutoff = now - 300  # 5 Minuten

            with get_db_conn() as conn:
                stale = conn.execute("""
                    SELECT id, description, assigned_to, nudge_count
                    FROM soul_tasks
                    WHERE status = 'open'
                      AND nudge_count < 3
                      AND (last_nudge_at IS NULL OR last_nudge_at < ?)
                    ORDER BY created_at ASC
                """, (stale_cutoff,)).fetchall()

                for row in stale:
                    task_id = row["id"]
                    agent = row["assigned_to"]
                    nudge_count = row["nudge_count"] + 1
                    conn.execute(
                        "UPDATE soul_tasks SET nudge_count=?, last_nudge_at=? WHERE id=?",
                        (nudge_count, now, task_id)
                    )
                    _log.info("[Soul] Nudge #%d für Task %s → %s", nudge_count, task_id[:12], agent)
                    # dispatch_mention als Nudge
                    try:
                        from gnom_hub.agents.swarm.swarm_comms import dispatch_mention
                        from gnom_hub.core.config import DB_PATH
                        from gnom_hub.db import get_active_project
                        proj = get_active_project() or "default"
                        dispatch_mention(
                            sender="SoulAG",
                            text=f"@{agent} NUDGE: Task noch offen — {row['description'][:100]} (ID: {task_id})",
                            context_id=proj,
                            db_path=str(DB_PATH),
                            current_depth=1,
                            priority="high",
                        )
                    except Exception as ex:
                        _log.warning("[Soul] Nudge-Dispatch fehlgeschlagen: %s", ex)

                # Nach 3 Nudges → blocked + SecurityAG benachrichtigen
                blocked = conn.execute("""
                    SELECT id, description, assigned_to
                    FROM soul_tasks
                    WHERE status = 'open' AND nudge_count >= 3
                """).fetchall()

                for row in blocked:
                    conn.execute(
                        "UPDATE soul_tasks SET status='blocked', updated_at=? WHERE id=?",
                        (now, row["id"])
                    )
                    _log.warning("[Soul] Task %s nach 3 Nudges → BLOCKED", row["id"])
                    try:
                        from gnom_hub.agents.swarm.swarm_comms import dispatch_mention
                        from gnom_hub.core.config import DB_PATH
                        from gnom_hub.db import get_active_project
                        proj = get_active_project() or "default"
                        dispatch_mention(
                            sender="SoulAG",
                            text=f"@SecurityAG BLOCKADE: Task {row['id']} ({row['description'][:80]}) nach 3 Nudges noch offen — Agent: {row['assigned_to']}",
                            context_id=proj,
                            db_path=str(DB_PATH),
                            current_depth=1,
                            priority="critical",
                        )
                    except Exception as ex:
                        _log.warning("[Soul] SecurityAG-Benachrichtigung fehlgeschlagen: %s", ex)

                if stale or blocked:
                    conn.commit()
        except Exception as ex:
            _log.error("[Soul] _nudge_loop fehlgeschlagen: %s", ex)

    def inject_context(self, sys: str, msg: str, agent_name: str = None) -> str:
        top_k = 6
        if agent_name:
            try:
                from gnom_hub.db import get_state_value
                settings = get_state_value("agent_settings", {}).get(agent_name.lower(), {})
                top_k = {1: 2, 2: 4, 3: 6, 4: 8, 5: 12}.get(settings.get("memory_strength", 3), 6)
            except Exception:
                pass

        # Zusätzlich: Immer User-Top-Level-Aufgaben (high priority) injizieren
        _user_facts = []
        try:
            from gnom_hub.db.connection import get_db_conn
            with get_db_conn() as _conn:
                _rows = _conn.execute(
                    "SELECT key, value FROM soul_memory WHERE agent = 'User' AND priority = 'high' ORDER BY timestamp DESC LIMIT 3"
                ).fetchall()
                _user_facts = [f"{r['key']}: {r['value']}" for r in _rows]
        except Exception:
            pass
        facts = query_memory(msg, agent_name=agent_name or "all", top_k=top_k)
        # User high-priority facts immer an erste Stelle
        if _user_facts:
            facts = _user_facts + [f for f in facts if f not in _user_facts]
        
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
        from gnom_hub.soul.zwc_soul import add_directive as _add_dir
        zwc = _add_dir(target_agent, directive, ttl)
        _log.info("[Soul] Directive emitted: %s -> %s: %s", target_agent, directive[:60], ttl)

    def get_definitions(self) -> dict:
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        return AGENT_DEFINITIONS


soul_instance = SoulAG()


# ── Evolution & Feedback (unverändert) ─────────────────────────────────────
def _save_rules(res: str, prefix=""):
    s = res.find("[")
    if s != -1:
        try:
            rules, _ = _parse_json_value(res, s)
            if rules is None:
                rules = []
            for f in rules:
                if f.get("agent") and f.get("rule"):
                    agent_name = f["agent"]
                    rule_text = prefix + f["rule"]
                    save_soul_fact_smart(f"evolution_{agent_name}_{uuid.uuid4().hex[:6]}", rule_text, agent="SoulAG")
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
    save_soul_fact_smart(f"feedback_{uuid.uuid4().hex[:6]}", f"Vote: {vote} | {comment}", agent="SoulAG")
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
