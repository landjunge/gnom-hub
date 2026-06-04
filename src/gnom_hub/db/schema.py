import sqlite3
import json
import uuid
from datetime import datetime, timezone
from gnom_hub.core.config import Config
from gnom_hub.core.logger import get_logger

logger = get_logger("db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY,
    id TEXT NOT NULL UNIQUE,
    port INTEGER DEFAULT 0,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'offline',
    capabilities TEXT DEFAULT '[]',
    role TEXT DEFAULT 'normal',
    active_job TEXT DEFAULT NULL,
    last_seen TEXT NOT NULL,
    circuit_state TEXT DEFAULT 'CLOSED',
    consecutive_failures INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat (
    id TEXT PRIMARY KEY,
    project TEXT NOT NULL DEFAULT 'default',
    sender TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    msg_type TEXT NOT NULL DEFAULT 'chat',
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS soul_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    priority TEXT DEFAULT 'medium',
    agent TEXT DEFAULT 'System',
    UNIQUE(key)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL,
    trace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    base_prompt TEXT NOT NULL,
    modifications TEXT NOT NULL,
    performance_score REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    feedback_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 0,
    parent_id TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    resource TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS showbox_presentations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slides TEXT NOT NULL,
    sender TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS explainable_outputs (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    task TEXT NOT NULL,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graceful_degradation_failures (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    fallback_agent TEXT,
    task TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS token_budget_logs (
    operation_id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    model TEXT NOT NULL,
    cost REAL NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS token_budget_alerts (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    acknowledged INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_agent_event ON audit_log(agent, event_type);
CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_soul_memory_key ON soul_memory(key);
CREATE INDEX IF NOT EXISTS idx_soul_memory_timestamp ON soul_memory(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_project_ts ON chat(project, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_agent ON chat(agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_project_agent ON chat(project, agent_id);

CREATE TABLE IF NOT EXISTS agent_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sender        TEXT    NOT NULL,
    recipient     TEXT    NOT NULL,
    payload       TEXT    NOT NULL,
    priority      INTEGER NOT NULL DEFAULT 5,
    status        TEXT    NOT NULL DEFAULT 'pending',
    retry_count   INTEGER NOT NULL DEFAULT 0,
    created_at    REAL    NOT NULL,
    deliver_after REAL    NOT NULL DEFAULT 0,
    context_id    TEXT,
    depth         INTEGER NOT NULL DEFAULT 0,
    processing_since REAL DEFAULT NULL,
    parent_msg_id INTEGER DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_aq_recipient_status ON agent_messages(recipient, status, deliver_after);
CREATE INDEX IF NOT EXISTS idx_aq_context ON agent_messages(context_id, depth);

CREATE TABLE IF NOT EXISTS swarm_callbacks (
    idempotency_key  TEXT PRIMARY KEY,
    context_id       TEXT NOT NULL,
    agent_name       TEXT NOT NULL,
    result_json      TEXT NOT NULL,
    received_at      REAL NOT NULL,
    http_status      INTEGER DEFAULT 200
);
CREATE INDEX IF NOT EXISTS idx_cb_context ON swarm_callbacks(context_id);

CREATE TABLE IF NOT EXISTS agent_capabilities (
    agent_name   TEXT NOT NULL,
    capability   TEXT NOT NULL,
    confidence   REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (agent_name, capability)
);
"""

def _seed_agents(conn):
    """Initialisiert die 8 Standard-Agenten direkt in der übergebenen Verbindung."""
    from gnom_hub.soul import soul_instance
    try:
        for k, v in soul_instance.get_definitions().items():
            conn.execute("""
                INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (v["name"], str(uuid.uuid4()), 0, v["description"], "online", 
                  json.dumps(v["capabilities"]), v["role"], None, datetime.now(timezone.utc).isoformat()))
        logger.info("[DB] Default 8 agents successfully seeded.")
    except sqlite3.Error as e:
        logger.error(f"[DB] Error seeding agents: {e}")

def _seed_chat_history(conn):
    """Initialisiert eine realistische Chat-Historie mit Showbox-Slides."""
    from datetime import datetime, timedelta
    try:
        now = datetime.now(timezone.utc)
        def iso_time(offset_minutes):
            t = now - timedelta(minutes=offset_minutes)
            return t.isoformat().replace("+00:00", "Z")
        messages = [
            ("User", "generalag", "chat", "@GeneralAG Analysiere die Server-Performance und erstelle mir einen Report in Showbox 1.", iso_time(10), "{}"),
            ("GeneralAG", "generalag", "chat", "@user Ich habe die Aufgabe erfasst und an CoderAG delegiert, um die System-Performance-Metriken live in Showbox 1 zu visualisieren.", iso_time(9), "{}"),
            ("CoderAG", "coderag", "chat", "@user @GeneralAG Hier ist die Live-Statistik des Hub-Servers. Die Visualisierung wurde direkt in Showbox 1 geladen. <SHOWBOX:1>[\"<div style='padding: 20px; text-align: center;'><h2 style='color: #00FF88; font-weight: 500; font-size: 1.1rem;'>🚀 Gnom-Hub Status</h2><p style='color: #888; font-size: 0.8rem; margin-top: 10px;'>All systems operational. Low-latency polling active.</p><div style='margin-top: 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;'><div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 4px;'><div style='color: #0066FF; font-size: 1.2rem; font-weight: 600;'>8</div><div style='color: #666; font-size: 0.65rem;'>Agents</div></div><div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 4px;'><div style='color: #39FF14; font-size: 1.2rem; font-weight: 600;'>0.18s</div><div style='color: #666; font-size: 0.65rem;'>Latency</div></div><div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 4px;'><div style='color: #cc33ff; font-size: 1.2rem; font-weight: 600;'>100%</div><div style='color: #666; font-size: 0.65rem;'>Local</div></div></div></div>\"]</SHOWBOX>", iso_time(8), "{}"),
            ("User", "researcherag", "chat", "@ResearcherAG Finde heraus, wie quantisiertes Offline-Retrieval mit FAISS funktioniert und lade die Notizen in Showbox 2.", iso_time(5), "{}"),
            ("ResearcherAG", "researcherag", "chat", "@user Ich habe die Vorteile von FAISS mit PQ-Quantisierung analysiert und in Showbox 2 geladen. <SHOWBOX:2>[\"<div style='padding: 20px;'><h3 style='color: #FFaa00; font-weight: 500; font-size: 1rem;'>🧠 Quantisiertes Offline-Retrieval (FAISS)</h3><p style='color: #9ca9be; font-size: 0.75rem; margin-top: 8px; line-height: 1.4;'>FAISS (Facebook AI Similarity Search) ermöglicht extrem schnelles Durchsuchen hochdimensionaler Vektoren direkt im lokalen RAM.</p><ul style='color: #bbb; font-size: 0.7rem; margin-top: 10px; padding-left: 15px;'><li style='margin-bottom: 5px;'><b>75% RAM-Reduktion</b> durch PQ</li><li style='margin-bottom: 5px;'><b>O(1) Latenz</b> für semantische Suchen</li><li><b>TF-IDF Fallback</b> bei fehlenden nativen Bibliotheken</li></ul></div>\"]</SHOWBOX>", iso_time(4), "{}")
        ]
        for msg in messages:
            conn.execute("""
                INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                VALUES (?, 'default', ?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), msg[0], msg[1], msg[2], msg[3], msg[4], msg[5]))
        logger.info("[DB] Default chat history successfully seeded.")
    except sqlite3.Error as e:
        logger.error(f"[DB] Error seeding chat history: {e}")

def _seed_showboxes(conn):
    """Initialisiert die standardmäßigen Showbox-Präsentationen."""
    try:
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        defaults = [
            ("Standard", [
                "<h1>Willkommen im Gnom-Hub</h1><p style='font-size:0.4em;color:var(--text-muted);'>Verwende den Editor, um eigene Folien zu erstellen.</p>"
            ])
        ]
        for name, slides in defaults:
            conn.execute("""
                INSERT OR IGNORE INTO showbox_presentations (id, name, slides, sender, updated_at)
                VALUES (?, ?, ?, 'System', ?)
            """, (str(uuid.uuid4()), name, json.dumps(slides), now_str))
        logger.info("[DB] Default showbox presentations seeded successfully.")
    except sqlite3.Error as e:
        logger.error(f"[DB] Error seeding showboxes: {e}")

def init_database() -> None:
    """Erstellt alle benötigten Tabellen und Indizes, und führt das Seeding durch."""
    from gnom_hub.db.connection import get_db_connection
    try:
        with get_db_connection() as conn:
            with conn:
                conn.executescript(SCHEMA_SQL)
                
                # Dynamic migration to add processing_since to agent_messages if it is missing
                try:
                    conn.execute("ALTER TABLE agent_messages ADD COLUMN processing_since REAL DEFAULT NULL")
                except sqlite3.OperationalError:
                    pass
                
                # Dynamic migration for Phase 4 columns
                try:
                    conn.execute("ALTER TABLE agents ADD COLUMN circuit_state TEXT DEFAULT 'CLOSED'")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE agents ADD COLUMN consecutive_failures INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE agent_messages ADD COLUMN parent_msg_id INTEGER DEFAULT NULL")
                except sqlite3.OperationalError:
                    pass
                
                # Default states
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('active_project', '\"default\"')")
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('language', '\"en\"')")
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('active_showbox', '\"\"')")
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('enable_confirmations', 'false')")
                
                # Seeding agents
                if not conn.execute("SELECT 1 FROM agents").fetchone():
                    _seed_agents(conn)
                else:
                    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
                    for v in AGENT_DEFINITIONS.values():
                        conn.execute("UPDATE agents SET role = ? WHERE name = ?", (v["role"], v["name"]))
                
                # Seeding chat
                # Disabled to ensure new installations start with a clean slate

                # Seeding showbox presentations
                if not conn.execute("SELECT 1 FROM showbox_presentations").fetchone():
                    _seed_showboxes(conn)
                    
        logger.info("[DB] Database initialized successfully.")
    except Exception as e:
        logger.error(f"[DB] Database initialization failed: {e}")

def create_tables() -> None:
    """Kompatibilitäts-Wrapper für die alte API."""
    init_database()
