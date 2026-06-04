import sqlite3
import json
import logging
from gnom_hub.db.connection import get_db_conn, get_db_connection

logger = logging.getLogger(__name__)

def init_message_queue() -> None:
    """Schema-Migration: einmalig beim Hub-Start aufrufen."""
    with get_db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_messages (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sender        TEXT    NOT NULL,
                recipient     TEXT    NOT NULL,
                payload       TEXT    NOT NULL,           -- JSON
                priority      INTEGER NOT NULL DEFAULT 5, -- 1=hoch, 10=niedrig
                status        TEXT    NOT NULL DEFAULT 'pending',
                retry_count   INTEGER NOT NULL DEFAULT 0,
                created_at    REAL    NOT NULL,
                deliver_after REAL    NOT NULL DEFAULT 0, -- für Retry-Backoff
                context_id    TEXT,                       -- Konversations-Thread-ID
                depth         INTEGER NOT NULL DEFAULT 0, -- Rekursionstiefe
                processing_since REAL DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_aq_recipient_status
                ON agent_messages(recipient, status, deliver_after);

            CREATE INDEX IF NOT EXISTS idx_aq_context
                ON agent_messages(context_id, depth);

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
        """)
        # Dynamic migration to add processing_since if missing
        try:
            conn.execute("ALTER TABLE agent_messages ADD COLUMN processing_since REAL DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
