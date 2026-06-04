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
        """)
        # Dynamic migration to add processing_since if missing
        try:
            conn.execute("ALTER TABLE agent_messages ADD COLUMN processing_since REAL DEFAULT NULL")
        except sqlite3.OperationalError:
            pass
