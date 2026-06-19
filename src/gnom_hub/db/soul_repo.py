"""Soul memory repository — operations for soul facts and semantic retrieval."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from gnom_hub.core.logger import get_logger
from gnom_hub.db.connection import get_db_conn

logger = get_logger("db")


def save_soul_fact(key: str, value: str, agent: str = "System", priority: str = "medium"):
    from gnom_hub.db.chat_repo import add_chat_message
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
                cursor = conn.execute("INSERT OR REPLACE INTO soul_memory (key, value, timestamp, priority, agent) VALUES (?, ?, ?, ?, ?)", 
                             (key, value, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), priority or "medium", ag))
                row_id = cursor.lastrowid
        try:
            from gnom_hub.db.passive_db import archive_record
            archive_record("fact", ag, f"{key}: {value}", {"priority": priority})
        except Exception as ex:
            logger.warning(f"[DB] Passive archive fact logging failed: {ex}")
        try:
            from gnom_hub.memory.embeddings import get_embedder
            scope = ag.lower() if ag.lower() in ["coderag", "researcherag", "writerag", "editorag"] else "global"
            get_embedder().add_fact(str(row_id), key, value, scope=scope)
        except Exception as e:
            logger.warning(f"[DB] Failed to add fact to FAISS index: {e}")
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
        from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts
        return retrieve_relevant_facts(user_message)
    except Exception as e:
        logger.error(f"[DB] Failed to get relevant facts: {e}")
        return []
