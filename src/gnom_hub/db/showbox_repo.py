# showbox_repo.py — Showbox presentation database operations
import json
import uuid
from datetime import datetime, timezone
from gnom_hub.db.connection import get_db_conn
from gnom_hub.core.logger import get_logger
import sqlite3

logger = get_logger("db.showbox")


def save_showbox_presentation(name: str, slides: list, sender: str = None) -> dict:
    """Erstellt oder aktualisiert eine Showbox-Präsentation."""
    try:
        with get_db_conn() as conn:
            with conn:
                pid = str(uuid.uuid4())
                ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                conn.execute("""
                    INSERT INTO showbox_presentations (id, name, slides, sender, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        slides = excluded.slides,
                        sender = excluded.sender,
                        updated_at = excluded.updated_at
                """, (pid, name, json.dumps(slides), sender, ts))
                return {"name": name, "slides": slides, "sender": sender, "updated_at": ts}
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to save showbox presentation: {e}")
        return None


def get_showbox_presentations() -> list:
    """Gibt alle gespeicherten Showbox-Präsentationen zurück."""
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM showbox_presentations ORDER BY name ASC").fetchall()
            res = []
            for r in rows:
                d = dict(r)
                d["slides"] = json.loads(d["slides"])
                res.append(d)
            return res
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get showbox presentations: {e}")
        return []


def delete_showbox_presentation(name: str) -> bool:
    """Löscht eine Showbox-Präsentation über ihren Namen."""
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM showbox_presentations WHERE name = ?", (name,))
                return True
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to delete showbox presentation: {e}")
        return False


def get_showbox_presentation_by_name(name: str) -> dict:
    """Gibt eine Showbox-Präsentation über ihren Namen zurück."""
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT * FROM showbox_presentations WHERE name = ?", (name,)).fetchone()
            if row:
                d = dict(row)
                d["slides"] = json.loads(d["slides"])
                return d
            return None
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to get showbox presentation: {e}")
        return None


def get_active_showbox() -> str:
    """Gibt den Namen der aktiven Showbox-Präsentation zurück."""
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM state WHERE key='active_showbox'").fetchone()
            return json.loads(row["value"]) if row else ""
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as e:
        logger.error(f"[DB] Failed to get active showbox: {e}")
        return ""


def set_active_showbox(name: str):
    """Setzt den Namen der aktiven Showbox-Präsentation."""
    try:
        if not name.startswith("Blockade:"):
            from gnom_hub.db.system_repo import get_state_value
            pending = get_state_value("pending_decisions", {})
            has_pending = any(d.get("status") == "pending" for d in pending.values())
            if has_pending:
                logger.info(f"[DB] Override active showbox to '{name}' blocked: pending decision in progress.")
                return
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('active_showbox', ?)", (json.dumps(name.strip()),))
    except sqlite3.Error as e:
        logger.error(f"[DB] Failed to set active showbox: {e}")
