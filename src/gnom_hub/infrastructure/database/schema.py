import sqlite3
from ...core.config import Config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, status TEXT NOT NULL DEFAULT 'stopped',
    pid INTEGER, model TEXT, last_seen TIMESTAMP, port INTEGER DEFAULT 0, description TEXT,
    capabilities TEXT DEFAULT '[]', role TEXT DEFAULT 'normal', active_job TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
    model TEXT, token_count INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS flexsoul (
    agent_id TEXT PRIMARY KEY, short_term TEXT, long_term_summary TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS chat (
    id TEXT PRIMARY KEY, project TEXT NOT NULL DEFAULT 'default', sender TEXT NOT NULL,
    agent_id TEXT NOT NULL, msg_type TEXT NOT NULL DEFAULT 'chat', content TEXT NOT NULL,
    timestamp TEXT NOT NULL, metadata TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS soul_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL, value TEXT NOT NULL, timestamp TEXT NOT NULL, UNIQUE(key)
);
"""

def create_tables() -> None:
    with sqlite3.connect(str(Config.DB_PATH)) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('active_project', '\"default\"')")
