# system_repo.py — System state, audit, and maintenance operations
import json
import sys
import os
import sqlite3
from datetime import datetime, timezone
from gnom_hub.db.connection import get_db_conn
from gnom_hub.core.logger import get_logger

logger = get_logger("db.system")


def init_db():
    """Erstellt alle benötigten Tabellen idempotent und führt Seeding bei Bedarf aus."""
    from gnom_hub.db.schema import init_database
    init_database()


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


def is_testing() -> bool:
    if os.environ.get("FORCE_LIMIT_CHECK") == "1":
        return False
    if os.environ.get("GNOM_HUB_ENV") == "test" or os.environ.get("TESTING") in ("true", "1"):
        return True
    if "pytest" in sys.modules:
        return True
    return any("test" in arg or "pytest" in arg or "benchmark" in arg for arg in sys.argv)


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
