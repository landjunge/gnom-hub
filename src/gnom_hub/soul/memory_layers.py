"""
SoulAG Memory Layers — 3-stufiges Gedächtnis-System

Layer 1: Cache      — In-Memory, Top-50 Fakten nach Score, sofortiger Zugriff (<1ms)
Layer 2: Normal DB  — Aktuelle soul_memory SQLite (bestehend), alle relevanten Fakten
Layer 3: Passive DB — Langzeit-Archiv SQLite, nur Lesezugriff, Fallback wenn Layer 1+2 leer

Zusätzliche Spezial-DBs:
  - rules_db        — Erlaubnis/Blockade-Regeln für WatchdogAG + SecurityAG
  - coordination_db — Worker-Fähigkeiten + Job-History für GeneralAG
"""

import sqlite3, threading, time, logging, os
from pathlib import Path
from datetime import datetime
from typing import Optional

_log = logging.getLogger("soul.memory_layers")

# ── Pfade ──────────────────────────────────────────────────────────────────
def _db_dir() -> Path:
    from gnom_hub.core.config import DB_PATH
    return Path(DB_PATH).parent

def passive_db_path() -> Path:
    return _db_dir() / "soul_passive.db"

def rules_db_path() -> Path:
    return _db_dir() / "rules.db"

def coordination_db_path() -> Path:
    return _db_dir() / "coordination.db"


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — IN-MEMORY CACHE
# ══════════════════════════════════════════════════════════════════════════════
class SoulCache:
    """
    Superschneller In-Memory Cache.
    Hält die Top-50 Fakten nach Score im RAM.
    Wird beim Hub-Start aus der normalen DB befüllt und bei jedem neuen Fakt aktualisiert.
    """
    MAX_SIZE = 50

    def __init__(self):
        self._lock = threading.Lock()
        self._facts: dict[str, dict] = {}  # key → {value, priority, agent, score, ts}
        self._loaded = False

    def warm_up(self):
        """Befülle Cache beim Start aus der normalen DB."""
        try:
            from gnom_hub.db.connection import get_db_conn
            with get_db_conn() as conn:
                rows = conn.execute(
                    "SELECT key, value, priority, agent, timestamp FROM soul_memory "
                    "ORDER BY priority DESC, timestamp DESC LIMIT 100"
                ).fetchall()
            scored = []
            for r in rows:
                score = self._score(r["priority"], r["timestamp"])
                scored.append((r["key"], dict(r), score))
            scored.sort(key=lambda x: x[2], reverse=True)
            with self._lock:
                self._facts = {k: {**d, "score": s} for k, d, s in scored[:self.MAX_SIZE]}
                self._loaded = True
            _log.info("[Cache] Warm-up: %d Fakten geladen", len(self._facts))
        except Exception as e:
            _log.warning("[Cache] Warm-up fehlgeschlagen: %s", e)

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            return self._facts.get(key)

    def get_top(self, n: int = 10, agent: str = None) -> list[dict]:
        """Gibt die n relevantesten Fakten zurück, optional gefiltert nach Agent."""
        with self._lock:
            facts = list(self._facts.values())
        if agent:
            agent_lower = agent.lower()
            facts = [f for f in facts if
                     f.get("agent", "").lower() in (agent_lower, "all", "system", "soulag")]
        facts.sort(key=lambda f: f.get("score", 0), reverse=True)
        return facts[:n]

    def put(self, key: str, value: str, priority: str, agent: str):
        """Neuen Fakt in Cache aufnehmen. Verdrängt niedrig-scored Fakten wenn voll."""
        score = self._score(priority, datetime.now().isoformat())
        entry = {"key": key, "value": value, "priority": priority,
                 "agent": agent, "score": score, "ts": time.time()}
        with self._lock:
            self._facts[key] = entry
            if len(self._facts) > self.MAX_SIZE:
                # Niedrigsten Score rauswerfen
                worst = min(self._facts.items(), key=lambda x: x[1].get("score", 0))
                if worst[1].get("score", 0) < score:
                    del self._facts[worst[0]]
                else:
                    del self._facts[key]  # Neuer ist schlechter → nicht aufnehmen

    def invalidate(self, key: str):
        with self._lock:
            self._facts.pop(key, None)

    @staticmethod
    def _score(priority: str, timestamp: str) -> float:
        base = {"high": 30, "medium": 15, "low": 5}.get(priority, 10)
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00").replace(" ", "T")[:19])
            age_days = (datetime.now() - ts).days
            return base - age_days * 0.5
        except Exception:
            return base


# Singleton
_cache = SoulCache()

def get_cache() -> SoulCache:
    return _cache


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3 — PASSIVE LANGZEIT-ARCHIV
# ══════════════════════════════════════════════════════════════════════════════
class PassiveDB:
    """
    Langzeit-Archiv. Nur Lesezugriff für Agenten.
    SoulAG schreibt hier Fakten rein wenn sie aus der normalen DB verdrängt werden.
    Wird nur abgefragt wenn Layer 1+2 keine Treffer liefern.
    """

    def __init__(self):
        self._path = str(passive_db_path())
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS soul_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    priority TEXT DEFAULT 'medium',
                    agent TEXT DEFAULT 'System',
                    archived_at TEXT NOT NULL,
                    source TEXT DEFAULT 'auto'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_key ON soul_archive(key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_priority ON soul_archive(priority)")
            conn.commit()

    def archive(self, key: str, value: str, priority: str, agent: str):
        """Fakt ins Archiv schreiben (nur SoulAG darf das)."""
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO soul_archive (key, value, priority, agent, archived_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (key, value, priority, agent, datetime.now().isoformat())
                )
                conn.commit()
        except Exception as e:
            _log.warning("[PassiveDB] Archive fehlgeschlagen: %s", e)

    def search(self, keywords: list[str], limit: int = 5) -> list[dict]:
        """Suche im Archiv nach Keywords — nur als Fallback."""
        try:
            results = []
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                for kw in keywords[:3]:  # Max 3 Keywords um DB nicht zu belasten
                    rows = conn.execute(
                        "SELECT key, value, priority, agent FROM soul_archive "
                        "WHERE key LIKE ? OR value LIKE ? "
                        "ORDER BY priority DESC LIMIT ?",
                        (f"%{kw}%", f"%{kw}%", limit)
                    ).fetchall()
                    results.extend([dict(r) for r in rows])
            # Deduplizieren
            seen = set()
            unique = []
            for r in results:
                if r["key"] not in seen:
                    seen.add(r["key"])
                    unique.append(r)
            return unique[:limit]
        except Exception as e:
            _log.warning("[PassiveDB] Search fehlgeschlagen: %s", e)
            return []

    def get(self, key: str) -> Optional[dict]:
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM soul_archive WHERE key = ?", (key,)
                ).fetchone()
                return dict(row) if row else None
        except Exception:
            return None


# Singleton
_passive_db = PassiveDB()

def get_passive_db() -> PassiveDB:
    return _passive_db


# ══════════════════════════════════════════════════════════════════════════════
# RULES DB — WatchdogAG + SecurityAG
# ══════════════════════════════════════════════════════════════════════════════
class RulesDB:
    """
    Zentrale Regeldatenbank für WatchdogAG und SecurityAG.
    Speichert: erlaubte Pfade, blockierte Befehle, User-Entscheidungen.
    Nur WatchdogAG/SecurityAG lesen — User und Agenten schreiben über API.
    """

    def __init__(self):
        self._path = str(rules_db_path())
        self._init_db()
        self._cache: dict[str, list] = {}  # In-Memory Cache für häufige Lookups
        self._cache_ts: float = 0

    def _init_db(self):
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_type TEXT NOT NULL,       -- 'allow_path', 'block_path', 'allow_cmd', 'block_cmd', 'user_decision'
                    pattern TEXT NOT NULL,          -- Pfad, Befehl oder Pattern
                    agent TEXT DEFAULT 'all',       -- Für welchen Agenten
                    reason TEXT DEFAULT '',         -- Warum diese Regel
                    created_by TEXT DEFAULT 'user', -- 'user', 'watchdog', 'security', 'system'
                    created_at TEXT NOT NULL,
                    expires_at TEXT DEFAULT NULL,   -- NULL = permanent
                    active INTEGER DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_type ON rules(rule_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_agent ON rules(agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_active ON rules(active)")

            # Basis-Regeln eintragen falls noch leer
            count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
            if count == 0:
                _bootstrap_rules(conn)

            conn.commit()

    def _load_cache(self):
        """Cache alle aktiven Regeln — max alle 60s neu laden."""
        if time.time() - self._cache_ts < 60:
            return
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM rules WHERE active = 1 AND "
                    "(expires_at IS NULL OR expires_at > ?)",
                    (datetime.now().isoformat(),)
                ).fetchall()
            cache: dict[str, list] = {}
            for r in rows:
                rt = r["rule_type"]
                cache.setdefault(rt, []).append(dict(r))
            self._cache = cache
            self._cache_ts = time.time()
        except Exception as e:
            _log.warning("[RulesDB] Cache-Reload fehlgeschlagen: %s", e)

    def check(self, rule_type: str, pattern: str, agent: str = "all") -> Optional[str]:
        """
        Prüft ob eine Regel greift.
        Returns: 'allow', 'block', oder None (keine Regel)
        """
        self._load_cache()
        agent_lower = agent.lower()
        for rule in self._cache.get(rule_type, []):
            rule_agent = rule.get("agent", "all").lower()
            if rule_agent not in ("all", agent_lower):
                continue
            rp = rule.get("pattern", "")
            if rp in pattern or pattern.startswith(rp):
                return "allow" if "allow" in rule_type else "block"
        return None

    def add_rule(self, rule_type: str, pattern: str, agent: str = "all",
                 reason: str = "", created_by: str = "user", expires_hours: int = None):
        """Neue Regel hinzufügen."""
        expires_at = None
        if expires_hours:
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT INTO rules (rule_type, pattern, agent, reason, created_by, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (rule_type, pattern, agent, reason, created_by,
                     datetime.now().isoformat(), expires_at)
                )
                conn.commit()
            self._cache_ts = 0  # Cache invalidieren
            _log.info("[RulesDB] Neue Regel: %s | %s | %s", rule_type, pattern, agent)
        except Exception as e:
            _log.warning("[RulesDB] Add rule fehlgeschlagen: %s", e)

    def get_rules_for_agent(self, agent: str) -> list[dict]:
        """Alle Regeln für einen Agenten — für Prompt-Injection."""
        self._load_cache()
        agent_lower = agent.lower()
        result = []
        for rules in self._cache.values():
            for r in rules:
                if r.get("agent", "all").lower() in ("all", agent_lower):
                    result.append(r)
        return result


def _bootstrap_rules(conn):
    """Standard-Regeln beim ersten Start."""
    now = datetime.now().isoformat()
    defaults = [
        ("block_path", "src/gnom_hub/", "all", "Systemcode geschützt", "system"),
        ("block_path", "config/", "all", "Konfiguration geschützt", "system"),
        ("block_path", ".env", "all", ".env geschützt", "system"),
        ("block_path", "run.sh", "all", "Startup-Script geschützt", "system"),
        ("allow_path", "gnom_workspace/", "all", "Workspace immer erlaubt", "system"),
        ("allow_path", "/tmp/", "all", "Temp immer erlaubt", "system"),
        ("allow_cmd", "pytest", "all", "Tests immer erlaubt", "system"),
        ("allow_cmd", "pip install", "all", "Package-Install erlaubt", "system"),
        ("allow_cmd", "npm install", "all", "NPM-Install erlaubt", "system"),
        ("block_cmd", "git push", "all", "Nur User darf pushen", "system"),
        ("block_cmd", "rm -rf /", "all", "Root-Delete verboten", "system"),
        ("block_cmd", "curl|bash", "all", "Pipe-to-shell verboten", "system"),
    ]
    for rule_type, pattern, agent, reason, created_by in defaults:
        conn.execute(
            "INSERT INTO rules (rule_type, pattern, agent, reason, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rule_type, pattern, agent, reason, created_by, now)
        )


# Singleton
_rules_db = RulesDB()

def get_rules_db() -> RulesDB:
    return _rules_db


# ══════════════════════════════════════════════════════════════════════════════
# COORDINATION DB — GeneralAG
# ══════════════════════════════════════════════════════════════════════════════
class CoordinationDB:
    """
    GeneralAGs Gedächtnis für Koordination.
    Speichert: Worker-Fähigkeiten, Job-History, Erfolgsraten, aktuelle Aufgaben.
    """

    def __init__(self):
        self._path = str(coordination_db_path())
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_stats (
                    agent_name TEXT PRIMARY KEY,
                    total_jobs INTEGER DEFAULT 0,
                    successful_jobs INTEGER DEFAULT 0,
                    failed_jobs INTEGER DEFAULT 0,
                    avg_duration_s REAL DEFAULT 0,
                    last_job_at TEXT,
                    last_job_type TEXT,
                    strengths TEXT DEFAULT '[]',    -- JSON array
                    weaknesses TEXT DEFAULT '[]'    -- JSON array
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT,
                    worker TEXT NOT NULL,
                    task_summary TEXT NOT NULL,
                    result TEXT DEFAULT 'unknown',  -- 'success', 'failed', 'timeout'
                    duration_s REAL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delegation_rules (
                    task_type TEXT PRIMARY KEY,     -- 'code', 'text', 'research', 'review'
                    preferred_worker TEXT NOT NULL,
                    fallback_worker TEXT DEFAULT NULL,
                    reason TEXT DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_worker ON job_history(worker)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_result ON job_history(result)")

            # Bootstrap Delegation-Regeln
            count = conn.execute("SELECT COUNT(*) FROM delegation_rules").fetchone()[0]
            if count == 0:
                _bootstrap_delegation(conn)

            conn.commit()

    def record_job(self, worker: str, task_summary: str, result: str,
                   duration_s: float, context_id: str = None, notes: str = ""):
        """Job-Ergebnis speichern und Worker-Statistik aktualisieren."""
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT INTO job_history (context_id, worker, task_summary, result, duration_s, created_at, notes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (context_id, worker, task_summary[:200], result, duration_s,
                     datetime.now().isoformat(), notes)
                )
                # Stats updaten
                conn.execute("""
                    INSERT INTO worker_stats (agent_name, total_jobs, successful_jobs, failed_jobs, last_job_at, last_job_type)
                    VALUES (?, 1, ?, ?, ?, ?)
                    ON CONFLICT(agent_name) DO UPDATE SET
                        total_jobs = total_jobs + 1,
                        successful_jobs = successful_jobs + (CASE WHEN ? = 'success' THEN 1 ELSE 0 END),
                        failed_jobs = failed_jobs + (CASE WHEN ? = 'failed' THEN 1 ELSE 0 END),
                        last_job_at = ?,
                        last_job_type = ?
                """, (
                    worker,
                    1 if result == "success" else 0,
                    1 if result == "failed" else 0,
                    datetime.now().isoformat(),
                    task_summary[:50],
                    result, result,
                    datetime.now().isoformat(),
                    task_summary[:50]
                ))
                conn.commit()
        except Exception as e:
            _log.warning("[CoordDB] record_job fehlgeschlagen: %s", e)

    def get_best_worker(self, task_type: str) -> tuple[str, Optional[str]]:
        """Gibt preferred + fallback Worker für einen Task-Typ zurück."""
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT preferred_worker, fallback_worker FROM delegation_rules WHERE task_type = ?",
                    (task_type,)
                ).fetchone()
                if row:
                    return row["preferred_worker"], row["fallback_worker"]
        except Exception:
            pass
        # Fallbacks
        defaults = {
            "code": ("CoderAG", "WriterAG"),
            "text": ("WriterAG", "EditorAG"),
            "research": ("ResearcherAG", "WriterAG"),
            "review": ("EditorAG", "SecurityAG"),
        }
        return defaults.get(task_type, ("CoderAG", None))

    def get_worker_summary(self) -> str:
        """Kurze Zusammenfassung aller Worker für GeneralAG Prompt-Injection."""
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT agent_name, total_jobs, successful_jobs, failed_jobs, last_job_type "
                    "FROM worker_stats ORDER BY total_jobs DESC"
                ).fetchall()
            if not rows:
                return ""
            lines = []
            for r in rows:
                total = r["total_jobs"] or 1
                rate = round((r["successful_jobs"] / total) * 100)
                lines.append(
                    f"  {r['agent_name']}: {r['total_jobs']} Jobs, {rate}% Erfolg"
                    + (f", zuletzt: {r['last_job_type'][:30]}" if r["last_job_type"] else "")
                )
            return "\n".join(lines)
        except Exception:
            return ""

    def get_recent_failures(self, worker: str, limit: int = 3) -> list[str]:
        """Letzte Fehler eines Workers — für GeneralAG Kontext."""
        try:
            with sqlite3.connect(self._path) as conn:
                rows = conn.execute(
                    "SELECT task_summary, notes FROM job_history "
                    "WHERE worker = ? AND result = 'failed' "
                    "ORDER BY created_at DESC LIMIT ?",
                    (worker, limit)
                ).fetchall()
            return [f"{r[0]}: {r[1]}" for r in rows]
        except Exception:
            return []


def _bootstrap_delegation(conn):
    """Standard-Delegation-Regeln."""
    rules = [
        ("code", "CoderAG", "WriterAG", "Code schreiben und ausführen"),
        ("text", "WriterAG", "EditorAG", "Texte und Dokumentation"),
        ("research", "ResearcherAG", "CoderAG", "Web-Recherche und Fakten"),
        ("review", "EditorAG", "SecurityAG", "Qualitätsprüfung"),
        ("security", "SecurityAG", "WatchdogAG", "Sicherheitsprüfungen"),
    ]
    for task_type, preferred, fallback, reason in rules:
        conn.execute(
            "INSERT INTO delegation_rules (task_type, preferred_worker, fallback_worker, reason) "
            "VALUES (?, ?, ?, ?)",
            (task_type, preferred, fallback, reason)
        )


# Singleton
_coordination_db = CoordinationDB()

def get_coordination_db() -> CoordinationDB:
    return _coordination_db


# ══════════════════════════════════════════════════════════════════════════════
# HAUPT-INTERFACE — wird von soul.py genutzt
# ══════════════════════════════════════════════════════════════════════════════
def query_memory(msg: str, agent_name: str, top_k: int = 6) -> list[str]:
    """
    3-Layer Memory Query:
    1. Cache (sofort, <1ms)
    2. Normal DB via retrieve_relevant_facts (FAISS, ~10ms)
    3. Passive DB als Fallback (nur wenn 1+2 leer, ~50ms)
    """
    results = []

    # Layer 1 — Cache
    cached = get_cache().get_top(n=top_k, agent=agent_name)
    if cached:
        results = [f"{f['key']}: {f['value']}" for f in cached]
        if len(results) >= top_k:
            return results  # Cache war ausreichend

    # Layer 2 — Normal DB (FAISS)
    if len(results) < top_k:
        try:
            from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts
            db_facts = retrieve_relevant_facts(msg, agent_name=agent_name,
                                               top_k=top_k - len(results))
            for f in db_facts:
                if f not in results:
                    results.append(f)
        except Exception as e:
            _log.debug("[Memory] Layer 2 fehlgeschlagen: %s", e)

    # Layer 3 — Passive DB Fallback
    if not results:
        keywords = [w for w in msg.split() if len(w) > 4][:5]
        archive_facts = get_passive_db().search(keywords, limit=top_k)
        if archive_facts:
            results = [f"[Archiv] {f['key']}: {f['value']}" for f in archive_facts]
            _log.info("[Memory] Layer 3 Fallback: %d Archiv-Fakten gefunden", len(archive_facts))

    return results[:top_k]


def save_fact_all_layers(key: str, value: str, priority: str, agent: str):
    """
    Fakt in allen relevanten Layern speichern.
    Layer 1 (Cache) immer.
    Layer 2 (Normal DB) immer — via bestehenden save_soul_fact.
    Layer 3 (Passive) nur für high-priority Fakten als Backup.
    """
    # Layer 1
    get_cache().put(key, value, priority, agent)

    # Layer 2 — bestehend
    try:
        from gnom_hub.db import save_soul_fact
        save_soul_fact(key, value, agent=agent, priority=priority)
    except Exception as e:
        _log.warning("[Memory] Layer 2 save fehlgeschlagen: %s", e)

    # Layer 3 — nur high priority als Backup
    if priority == "high":
        get_passive_db().archive(key, value, priority, agent)


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXT DB — GeneralAG Task-Koordination über Neustarts hinweg
# ══════════════════════════════════════════════════════════════════════════════
class ContextDB:
    """
    GeneralAGs Arbeitsgedächtnis für laufende Tasks.
    Überlebt Hub-Neustarts — GeneralAG weiß nach Restart was er koordiniert hatte.
    """

    def __init__(self):
        self._path = str(_db_dir() / "context.db")
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contexts (
                        context_id TEXT PRIMARY KEY,
                        original_task TEXT NOT NULL,
                        status TEXT DEFAULT 'active',   -- active, completed, failed, abandoned
                        created_by TEXT DEFAULT 'user',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        workers_involved TEXT DEFAULT '[]',  -- JSON array
                        last_result TEXT DEFAULT '',
                        notes TEXT DEFAULT ''
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS context_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        context_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,   -- 'delegated', 'completed', 'failed', 'retry'
                        agent TEXT NOT NULL,
                        detail TEXT DEFAULT '',
                        ts TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ctx_status ON contexts(status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ctx_events ON context_events(context_id)")
                conn.commit()
        except Exception as e:
            _log.warning("[ContextDB] Init fehlgeschlagen: %s", e)

    def open_context(self, context_id: str, task: str, created_by: str = "user"):
        try:
            now = datetime.now().isoformat()
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO contexts "
                    "(context_id, original_task, created_by, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (context_id, task[:500], created_by, now, now)
                )
                conn.commit()
        except Exception as e:
            _log.debug("[ContextDB] open_context: %s", e)

    def add_event(self, context_id: str, event_type: str, agent: str, detail: str = ""):
        try:
            now = datetime.now().isoformat()
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT INTO context_events (context_id, event_type, agent, detail, ts) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (context_id, event_type, agent, detail[:300], now)
                )
                conn.execute(
                    "UPDATE contexts SET updated_at=? WHERE context_id=?",
                    (now, context_id)
                )
                conn.commit()
        except Exception as e:
            _log.debug("[ContextDB] add_event: %s", e)

    def close_context(self, context_id: str, status: str = "completed", result: str = ""):
        try:
            now = datetime.now().isoformat()
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "UPDATE contexts SET status=?, last_result=?, updated_at=? WHERE context_id=?",
                    (status, result[:500], now, context_id)
                )
                conn.commit()
        except Exception as e:
            _log.debug("[ContextDB] close_context: %s", e)

    def get_active_contexts(self) -> list[dict]:
        """Gibt alle aktiven Contexts zurück — für GeneralAG nach Neustart."""
        try:
            with sqlite3.connect(self._path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM contexts WHERE status = 'active' "
                    "ORDER BY updated_at DESC LIMIT 10"
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_summary_for_generalag(self) -> str:
        """Kurze Zusammenfassung offener Tasks für GeneralAG Prompt."""
        active = self.get_active_contexts()
        if not active:
            return ""
        lines = ["=== OFFENE TASKS (nach Neustart) ==="]
        for ctx in active[:5]:
            age = ""
            try:
                ts = datetime.fromisoformat(ctx["updated_at"])
                mins = int((datetime.now() - ts).total_seconds() / 60)
                age = f" (vor {mins}m)"
            except Exception:
                pass
            lines.append(f"  [{ctx['context_id'][:8]}] {ctx['original_task'][:80]}{age}")
        return "\n".join(lines)

    def cleanup_old(self, days: int = 7):
        """Alte abgeschlossene Contexts aufräumen."""
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "DELETE FROM contexts WHERE status != 'active' AND updated_at < ?",
                    (cutoff,)
                )
                conn.commit()
        except Exception:
            pass


# Singleton
_context_db = ContextDB()

def get_context_db() -> ContextDB:
    return _context_db
