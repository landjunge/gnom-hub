import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from .config import DATA_DIR
from .log import get_logger

# =====================================================================
# CONFIGURATION & CONSTANTS
# =====================================================================

DB_PATH = DATA_DIR / "gnomhub.db"
logger = get_logger("db")


# =====================================================================
# CONNECTION MANAGER
# =====================================================================

@contextmanager
def get_db_conn():
    """Öffnet eine rohe Verbindung zu SQLite und konfiguriert grundlegende Pragmas."""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


# =====================================================================
# INITIALIZATION & SEEDING
# =====================================================================

def _seed_agents(conn):
    """Initialisiert die 8 Standard-Agenten direkt in der übergebenen Verbindung."""
    from .soul import soul_instance
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



def init_db():
    """Erstellt alle benötigten Tabellen idempotent und führt Seeding bei Bedarf aus."""
    try:
        with get_db_conn() as conn:
            with conn:
                conn.executescript("""
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
                        last_seen TEXT NOT NULL
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
                    CREATE INDEX IF NOT EXISTS idx_agent_event ON audit_log(agent, event_type);
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp DESC);
                """)
                try:
                    conn.execute("ALTER TABLE soul_memory ADD COLUMN priority TEXT DEFAULT 'medium'")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE soul_memory ADD COLUMN agent TEXT DEFAULT 'System'")
                except sqlite3.OperationalError:
                    pass
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('active_project', '\"default\"')")
                conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('language', '\"en\"')")
                
                # Wenn agents Tabelle leer ist, führe Seeding aus
                if not conn.execute("SELECT 1 FROM agents").fetchone():
                    _seed_agents(conn)
                else:
                    from .agent_definitions import AGENT_DEFINITIONS
                    for v in AGENT_DEFINITIONS.values():
                        conn.execute("UPDATE agents SET role = ? WHERE name = ?", (v["role"], v["name"]))
        logger.info("[DB] Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"[DB] Database initialization failed: {e}")


# =====================================================================
# MODERNE RELATIONALE API
# =====================================================================

def _row_to_msg(row):
    """Konvertiert eine Zeile der chat-Tabelle in ein Message-Dictionary."""
    d = dict(row)
    try:
        d["metadata"] = json.loads(d["metadata"])
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to parse metadata JSON for message {d.get('id')}: {e}")
        d["metadata"] = {}
    return d

def add_chat_message(project: str, sender: str, agent_id: str, msg_type: str, content: str, metadata: dict = None):
    """Fügt eine Nachricht direkt und relational in die chat-Tabelle ein (transaktionssicher)."""
    try:
        with get_db_conn() as conn:
            with conn:
                msg_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, project, sender, agent_id, msg_type, content,
                      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                      json.dumps(metadata or {})))
                return msg_id
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to add chat message: {e}")
        return None

def get_chat_history(project: str = "default", limit: int = 30):
    """Lädt die letzten X Nachrichten eines Projekts aus der chat-Tabelle."""
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM chat 
                WHERE project = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (project, limit)).fetchall()
            return [_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to retrieve chat history: {e}")
        return []

def update_agent_status(name: str, status: str, active_job: str = None):
    """Aktualisiert atomar und transaktionssicher den Online-Status eines Agenten."""
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = ?, active_job = ?, last_seen = ? 
                    WHERE name = ?
                """, (status, active_job, datetime.now(timezone.utc).isoformat(), name))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to update agent status for {name}: {e}")

def get_all_agents():
    """Gibt alle Agenten aus der agents-Tabelle zurück."""
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM agents").fetchall()
            if not rows:
                with conn:
                    _seed_agents(conn)
                rows = conn.execute("SELECT * FROM agents").fetchall()
            
            res = []
            for r in rows:
                d = dict(r)
                try:
                    d["capabilities"] = json.loads(d["capabilities"])
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"[DB] Failed to parse capabilities JSON for agent {d.get('name')}: {e}")
                    d["capabilities"] = []
                res.append(d)
            return res
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to retrieve agents list: {e}")
        return []


# =====================================================================
# SYSTEM & PROJECT HELPER
# =====================================================================

def get_active_project() -> str:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM state WHERE key='active_project'").fetchone()
            return json.loads(row["value"]) if row else "default"
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to get active project: {e}")
        return "default"

def set_active_project(name: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('active_project', ?)", (json.dumps(name.strip()),))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set active project: {e}")

def get_language() -> str:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM state WHERE key='language'").fetchone()
            return json.loads(row["value"]) if row else "en"
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to get language: {e}")
        return "en"

def set_language(lang: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('language', ?)", (json.dumps(lang.strip().lower()),))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set language: {e}")
def agent_exists(agent_id: str) -> bool:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT 1 FROM agents WHERE id = ? OR name = ?", (agent_id, agent_id)).fetchone()
            return row is not None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to check agent existence: {e}")
        return False

def get_agent_memories(agent_id: str, limit: int = 100) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM chat 
                WHERE agent_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (agent_id, limit)).fetchall()
            return [_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get agent memories: {e}")
        return []

def count_agent_memories(agent_id: str) -> int:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = ?", (agent_id,)).fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to count agent memories: {e}")
        return 0

def add_agent_memory(agent_id: str, content: str, timestamp: str = None, sender: str = "user", project: str = "default", msg_type: str = "chat", metadata: dict = None) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                msg_id = str(uuid.uuid4())
                ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                meta = metadata or {"sender": sender, "type": msg_type}
                conn.execute("""
                    INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, project, sender, agent_id, msg_type, content, ts, json.dumps(meta)))
                return {"id": msg_id, "agent_id": agent_id, "content": content, "timestamp": ts, "project": project, "metadata": meta}
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to add agent memory: {e}")
        return None

def update_memory_content(msg_id: str, content: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE chat SET content = ? WHERE id = ?", (content, msg_id))
                row = conn.execute("SELECT * FROM chat WHERE id = ?", (msg_id,)).fetchone()
                return _row_to_msg(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to update memory content: {e}")
        return None

def delete_memory_by_id(msg_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE id = ?", (msg_id,))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete memory {msg_id}: {e}")

def delete_agent_memories(agent_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = ?", (agent_id,))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete agent memories for {agent_id}: {e}")

def search_memories(query: str, project: str = "default") -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM chat 
                WHERE project = ? AND content LIKE ? 
                ORDER BY timestamp DESC
            """, (project, f"%{query}%")).fetchall()
            return [_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to search memories: {e}")
        return []

def get_state_value(key: str, default=None):
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return json.loads(row["value"]) if row else default
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to get state value for {key}: {e}")
        return default

def set_state_value(key: str, value):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set state value for {key}: {e}")

def create_agent_record(name: str, description: str = "", status: str = "offline", role: str = "normal", capabilities: list = None) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                agent_id = str(uuid.uuid4())
                caps = capabilities or []
                conn.execute("""
                    INSERT INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen)
                    VALUES (?, ?, 0, ?, ?, ?, ?, NULL, ?)
                """, (name, agent_id, description, status, json.dumps(caps), role, datetime.now(timezone.utc).isoformat()))
                return {"id": agent_id, "name": name, "description": description, "status": status, "capabilities": caps, "role": role}
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to create agent record: {e}")
        return None

def set_agent_status(agent_ref: str, status: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = ?, last_seen = ? 
                    WHERE id = ? OR name = ?
                """, (status, datetime.now(timezone.utc).isoformat(), agent_ref, agent_ref))
                row = conn.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (agent_ref, agent_ref)).fetchone()
                if row:
                    d = dict(row)
                    d["capabilities"] = json.loads(d["capabilities"])
                    return d
                return None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set agent status for {agent_ref}: {e}")
        return None

def delete_agent_by_id(agent_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM agents WHERE id = ? OR name = ?", (agent_id, agent_id))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete agent {agent_id}: {e}")

def get_chat_count(agent_id: str = None) -> int:
    try:
        with get_db_conn() as conn:
            if agent_id:
                row = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = ?", (agent_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM chat").fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to count chat messages: {e}")
        return 0

def delete_non_system_agents(system_agents: list):
    try:
        with get_db_conn() as conn:
            with conn:
                placeholders = ",".join("?" for _ in system_agents)
                conn.execute(f"DELETE FROM agents WHERE LOWER(name) NOT IN ({placeholders})", [n.lower() for n in system_agents])
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete non-system agents: {e}")

def clear_project_chat(project: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = 'war-room' AND project = ?", (project,))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to clear project chat: {e}")

def clear_project_chat_by_sender(project: str, sender: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = 'war-room' AND project = ? AND LOWER(sender) = ?", (project, sender.lower()))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to clear project chat by sender: {e}")

def clear_agent_jobs(agent_name: str = None):
    try:
        with get_db_conn() as conn:
            with conn:
                if agent_name:
                    conn.execute("UPDATE agents SET active_job = NULL WHERE LOWER(name) = ?", (agent_name.lower(),))
                else:
                    conn.execute("UPDATE agents SET active_job = NULL")
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to clear agent jobs: {e}")

def update_agent_active_job(name: str, active_job: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE agents SET active_job = ? WHERE LOWER(name) = ?", (active_job or None, name.lower()))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to update agent active job for {name}: {e}")

def pulse_agent_alive(name: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = 'online', last_seen = ? 
                    WHERE name = ?
                """, (datetime.now(timezone.utc).isoformat(), name))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to pulse agent alive: {e}")

def register_agent_in_db(name: str, port: int, description: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
                now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                if row:
                    conn.execute("""
                        UPDATE agents 
                        SET status = 'online', port = ?, description = ?, last_seen = ? 
                        WHERE name = ?
                    """, (port, description or str(port), now_str, name))
                else:
                    agent_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen)
                        VALUES (?, ?, ?, ?, 'online', '[]', 'normal', NULL, ?)
                    """, (name, agent_id, port, description or str(port), now_str))
                
                updated = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
                if updated:
                    d = dict(updated)
                    d["capabilities"] = json.loads(d["capabilities"])
                    return d
                return None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to register agent {name}: {e}")
        return None

def delete_offline_agents():
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM agents WHERE status = 'offline'")
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete offline agents: {e}")

def set_agent_role(agent_ref: str, role: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                if role == "general":
                    conn.execute("UPDATE agents SET role = 'normal' WHERE role = 'general'")
                conn.execute("UPDATE agents SET role = ? WHERE id = ? OR name = ?", (role, agent_ref, agent_ref))
                row = conn.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (agent_ref, agent_ref)).fetchone()
                return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set agent role for {agent_ref}: {e}")
        return None

def update_agent_role_memory(agent_id: str, role_content: str = None):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = ? AND msg_type = 'role'", (agent_id,))
                if role_content:
                    msg_id = str(uuid.uuid4())
                    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    meta = {"type": "role", "sender": "System"}
                    conn.execute("""
                        INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                        VALUES (?, 'default', 'System', ?, 'role', ?, ?, ?)
                    """, (msg_id, agent_id, role_content, ts, json.dumps(meta)))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to update agent role memory: {e}")

# =====================================================================
# SOUL AG
# =====================================================================

def save_soul_fact(key: str, value: str, agent: str = "System"):
    ag = (agent or "System").strip()
    limits = {
        "active_preset": ["GeneralAG", "SoulAG", "System"],
        "approved_system_paths": ["SecurityAG", "WatchdogAG", "System"],
        "approved_security_writes": ["SecurityAG", "WatchdogAG", "System"],
        "approved_security_commands": ["SecurityAG", "WatchdogAG", "System"]
    }
    for rk, allowed in limits.items():
        if key == rk and ag not in allowed:
            add_chat_message("default", "SecurityAG", "securityag", "chat", f"@user @WatchdogAG: Warnung! {ag} hat versucht, den Schlüssel '{key}' zu schreiben. Blockiert.")
            raise PermissionError(f"Agent {ag} is not allowed to write key '{key}'")
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO soul_memory (key, value, timestamp) VALUES (?, ?, ?)", 
                             (key, value, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save soul fact: {e}")

def add_to_soul_memory(fact: str, priority: str = "medium", agent: str = "System"):
    key = f"fact_{agent.lower()}_{uuid.uuid4().hex[:8]}"
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO soul_memory (key, value, timestamp, priority, agent) VALUES (?, ?, ?, ?, ?)",
                    (key, fact, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), priority, agent)
                )
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to add to soul memory: {e}")

def get_relevant_facts(user_message: str) -> list:
    try:
        from .soul_retrieval import retrieve_relevant_facts
        return retrieve_relevant_facts(user_message)
    except Exception as e:
        logger.error(f"[DB] Failed to get relevant facts: {e}")
        return []

def log_audit_event(agent: str, event_type: str, details: dict, trace_id: str = None):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    INSERT INTO audit_log (timestamp, agent, event_type, details, trace_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                       agent, event_type, json.dumps(details), trace_id))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save audit log: {e}")

def cleanup_old_data(days_chat: int = 7, days_soul: int = 30):
    try:
        from datetime import timedelta
        limit_chat = (datetime.now(timezone.utc) - timedelta(days=days_chat)).isoformat().replace("+00:00", "Z")
        limit_soul = (datetime.now(timezone.utc) - timedelta(days=days_soul)).isoformat().replace("+00:00", "Z")
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE timestamp < ? AND msg_type != 'role'", (limit_chat,))
                protected = ["active_preset", "approved_system_paths", "approved_security_writes", "approved_security_commands"]
                placeholders = ",".join("?" for _ in protected)
                conn.execute(f"DELETE FROM soul_memory WHERE timestamp < ? AND key NOT IN ({placeholders})", (limit_soul, *protected))
        logger.info("[DB] Old chats and soul facts cleaned up successfully.")
    except Exception as e:
        logger.error(f"[DB] Cleanup failed: {e}")

