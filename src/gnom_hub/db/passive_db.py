# passive_db.py — Portable passive archiving database for SuperGNOM & emergency queries
import os
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from gnom_hub.core.config import DATA_DIR
from gnom_hub.core.logger import get_logger

PASSIVE_DB_PATH = DATA_DIR / "passive_archive.db"
logger = get_logger("passive_db")

def get_passive_conn():
    """Returns a raw SQLite connection to the passive archive database."""
    conn = sqlite3.connect(PASSIVE_DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-20000")
    return conn

def init_passive_db():
    """Idempotently initializes the passive_archive table."""
    try:
        with get_passive_conn() as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS archive_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        category TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_archive_content ON archive_log(content)")
    except sqlite3.Error as e:
        logger.error(f"[PassiveDB] Failed to init: {e}")

def archive_record(category: str, sender: str, content: str, metadata: dict = None):
    """Saves a record to the passive database."""
    try:
        init_passive_db()
        meta_val = json.dumps(metadata or {})
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with get_passive_conn() as conn:
            with conn:
                conn.execute("""
                    INSERT INTO archive_log (timestamp, category, sender, content, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (ts, category, sender, content, meta_val))
    except sqlite3.Error as e:
        logger.error(f"[PassiveDB] Failed to insert record: {e}")

def emergency_search(query: str, limit: int = 10) -> list:
    """Searches the passive database for matching terms (Emergency fallback)."""
    try:
        init_passive_db()
        with get_passive_conn() as conn:
            rows = conn.execute("""
                SELECT timestamp, category, sender, content FROM archive_log
                WHERE content LIKE ? OR sender LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[PassiveDB] Search failed: {e}")
        return []
