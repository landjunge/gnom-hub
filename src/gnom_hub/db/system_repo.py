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
                _enforce_audit_cap(conn)
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save audit log: {e}")


AUDIT_LOG_MAX_ROWS = 1000
AUDIT_LOG_KEEP_ROWS = 800


def _enforce_audit_cap(conn):
    try:
        n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        if n > AUDIT_LOG_MAX_ROWS:
            conn.execute("""
                DELETE FROM audit_log
                WHERE id IN (
                    SELECT id FROM audit_log
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                )
            """, (n - AUDIT_LOG_KEEP_ROWS,))
    except sqlite3.Error as e:
        logger.error(f"[DB] audit_log cap failed: {e}")


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


# ── Blockade Log ──

def log_blockade(agent_name: str, action_type: str, detail: str, reason: str, status: str = "blocked", blocked_by: str = "Gatekeeper", content_snippet: str = ""):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    INSERT INTO blockade_log (timestamp, agent_name, blocked_by, action_type, detail, reason, content_snippet, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    agent_name, blocked_by,
                    action_type, detail[:500], reason[:500],
                    content_snippet[:200], status,
                ))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to log blockade: {e}")


def get_blockades_for_agent(agent_name: str, limit: int = 50):
    try:
        with get_db_conn() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, agent_name, blocked_by, action_type, detail, reason, content_snippet, status FROM blockade_log WHERE agent_name = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit)
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get blockades: {e}")
        return []


def delete_blockade(blockade_id: int):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM blockade_log WHERE id = ?", (blockade_id,))
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete blockade: {e}")
        return False


def clear_agent_blockades(agent_name: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM blockade_log WHERE agent_name = ?", (agent_name,))
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to clear blockades: {e}")
        return False


def clear_all_blockades():
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM blockade_log")
        return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to clear all blockades: {e}")
        return False


def get_blockade_count(agent_name: str) -> int:
    try:
        with get_db_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM blockade_log WHERE agent_name = ?",
                (agent_name,)
            ).fetchone()
            return row["cnt"] if row else 0
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to count blockades: {e}")
        return 0


def get_all_blockade_counts():
    try:
        with get_db_conn() as conn:
            rows = conn.execute(
                "SELECT agent_name, COUNT(*) as cnt FROM blockade_log GROUP BY agent_name ORDER BY cnt DESC"
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get blockade counts: {e}")
        return []


def get_all_blockades(limit: int = 200):
    try:
        with get_db_conn() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, agent_name, blocked_by, action_type, detail, reason, content_snippet, status FROM blockade_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get all blockades: {e}")
        return []
