"""Chat & memory repository — CRUD operations for chat messages and agent memories.

This module contains two layers:
1. The OOP ChatRepository / SQLiteChatRepository (used by newer code paths)
2. Legacy functional API (re-exported from legacy_db.py for backward compatibility)
"""

import json; from datetime import datetime; from uuid import UUID; from typing import List, Optional
from abc import ABC, abstractmethod
from gnom_hub.chat.entities import ChatMessage, FlexSoul

class ChatRepository(ABC):
    @abstractmethod
    def get_messages(self, agent_id: UUID, limit: int = 50) -> List[ChatMessage]: pass
    @abstractmethod
    def save_message(self, message: ChatMessage) -> ChatMessage: pass
    @abstractmethod
    def get_flexsoul(self, agent_id: UUID) -> Optional[FlexSoul]: pass
    @abstractmethod
    def save_flexsoul(self, flexsoul: FlexSoul) -> FlexSoul: pass
    @abstractmethod
    def clear_history(self, agent_id: UUID) -> bool: pass
from .connection import get_db_connection, Await, parse_dt
def _row_to_msg(r) -> ChatMessage:
    role = "user" if r["sender"] == "user" else "assistant"
    try: aid = UUID(r["agent_id"])
    except Exception:
        import uuid; aid = uuid.NAMESPACE_DNS
    meta = json.loads(r["metadata"] or "{}") if "metadata" in r else {}
    return ChatMessage(id=UUID(r["id"]), agent_id=aid, role=role, content=r["content"], timestamp=parse_dt(r["timestamp"]), model=meta.get("model"), token_count=meta.get("token_count", 0))
class SQLiteChatRepository(ChatRepository):
    def get_messages(self, agent_id: UUID, limit: int = 50) -> Await:
        with get_db_connection() as conn: return Await([_row_to_msg(r) for r in conn.execute("SELECT * FROM chat WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?", (str(agent_id), limit)).fetchall()][::-1])
    def save_message(self, m: ChatMessage) -> Await:
        with get_db_connection() as conn:
            snd = "user" if m.role == "user" else "assistant"
            if snd != "user":
                row = conn.execute("SELECT name FROM agents WHERE id = ? OR name = ?", (str(m.agent_id), str(m.agent_id))).fetchone()
                if row: snd = row["name"]
            meta = json.dumps({"model": m.model, "token_count": m.token_count})
            conn.execute("INSERT OR REPLACE INTO chat VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (str(m.id), "default", snd, str(m.agent_id), "chat", m.content, m.timestamp.isoformat(), meta)); conn.commit()
        return Await(m)
    def get_flexsoul(self, agent_id: UUID) -> Await:
        with get_db_connection() as conn:
            r = conn.execute("SELECT * FROM soul_memory WHERE key = ?", (f"flexsoul:{agent_id}",)).fetchone()
            if not r: return Await(None)
            d = json.loads(r["value"]); return Await(FlexSoul(agent_id, [_row_to_msg(m) for m in d.get("short_term", [])], d.get("long_term"), parse_dt(r["timestamp"])))
    def save_flexsoul(self, fs: FlexSoul) -> Await:
        with get_db_connection() as conn:
            v = json.dumps({"short_term": [{"id": str(m.id), "agent_id": str(m.agent_id), "role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in fs.short_term], "long_term": fs.long_term_summary})
            conn.execute("INSERT OR REPLACE INTO soul_memory (key, value, timestamp) VALUES (?, ?, ?)", (f"flexsoul:{fs.agent_id}", v, fs.last_updated.isoformat())); conn.commit()
        return Await(fs)
    def clear_history(self, agent_id: UUID) -> Await:
        with get_db_connection() as conn: conn.execute("DELETE FROM chat WHERE agent_id = ?", (str(agent_id),)); conn.commit(); return Await(True)
    def get_history(self, project: str = "default", limit: int = 50) -> Await:
        with get_db_connection() as conn: return Await([_row_to_msg(r) for r in conn.execute("SELECT * FROM chat ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()])
    def count_messages(self) -> Await:
        with get_db_connection() as conn: return Await(conn.execute("SELECT COUNT(*) FROM chat").fetchone()[0])
    def add_message(self, m) -> Await:
        """Alias for save_message, used by memory_crud.py."""
        return self.save_message(m)
    def get_agent_memories(self, agent_id, limit: int = 100) -> Await:
        """Get memories for a specific agent."""
        with get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM chat WHERE agent_id = ? OR sender = ? ORDER BY timestamp DESC LIMIT ?", (str(agent_id), str(agent_id), limit)).fetchall()
            return Await([_row_to_msg(r) for r in rows])
    def count_messages_for_agent(self, agent_id) -> Await:
        """Count messages for a specific agent."""
        with get_db_connection() as conn:
            return Await(conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = ? OR sender = ?", (str(agent_id), str(agent_id))).fetchone()[0])
    def update_message_content(self, msg_id: str, content: str) -> Await:
        """Update the content of a specific message."""
        with get_db_connection() as conn:
            conn.execute("UPDATE chat SET content = ? WHERE id = ?", (content, msg_id))
            conn.commit()
            r = conn.execute("SELECT * FROM chat WHERE id = ?", (msg_id,)).fetchone()
            return Await(_row_to_msg(r) if r else None)
    def delete_by_id(self, msg_id: str) -> Await:
        """Delete a specific message by ID."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM chat WHERE id = ?", (msg_id,))
            conn.commit()
            return Await(True)
    def delete_by_agent(self, agent_id: str) -> Await:
        """Delete all messages for a specific agent."""
        with get_db_connection() as conn:
            conn.execute("DELETE FROM chat WHERE agent_id = ? OR sender = ?", (str(agent_id), str(agent_id)))
            conn.commit()
            return Await(True)


# =====================================================================
# LEGACY FUNCTIONAL API
# Functions moved here from legacy_db.py for decomposition.
# =====================================================================

import sqlite3
import uuid
from datetime import timezone

from gnom_hub.core.logger import get_logger
from gnom_hub.db.connection import get_db_conn

_logger = get_logger("db")


def _legacy_row_to_msg(row):
    """Konvertiert eine Zeile der chat-Tabelle in ein Message-Dictionary."""
    d = dict(row)
    try:
        meta = json.loads(d["metadata"])
        if isinstance(meta, str):
            meta = json.loads(meta)
        d["metadata"] = meta if isinstance(meta, dict) else {}
    except (json.JSONDecodeError, TypeError) as e:
        _logger.error(f"[DB] Failed to parse metadata JSON for message {d.get('id')}: {e}")
        d["metadata"] = {}
    return d

def add_chat_message(project: str, sender: str, agent_id: str, msg_type: str, content: str, metadata: dict = None):
    """Fügt eine Nachricht direkt und relational in die chat-Tabelle ein (transaktionssicher)."""
    try:
        with get_db_conn() as conn:
            with conn:
                msg_id = str(uuid.uuid4())
                meta_val = metadata or {}
                if isinstance(meta_val, str):
                    try:
                        meta_val = json.loads(meta_val)
                    except Exception:
                        meta_val = {}
                conn.execute("""
                    INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, project, sender, agent_id, msg_type, content,
                      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                      json.dumps(meta_val)))
                try:
                    from gnom_hub.db.passive_db import archive_record
                    archive_record("chat", sender, content, {"project": project, "agent_id": agent_id, "msg_type": msg_type})
                except Exception as ex:
                    _logger.warning(f"[DB] Passive archive message logging failed: {ex}")
                return msg_id
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to add chat message: {e}")
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
            return [_legacy_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to retrieve chat history: {e}")
        return []

def get_agent_memories(agent_id: str, limit: int = 100) -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM chat 
                WHERE agent_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (agent_id, limit)).fetchall()
            return [_legacy_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to get agent memories: {e}")
        return []

def count_agent_memories(agent_id: str) -> int:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = ?", (agent_id,)).fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to count agent memories: {e}")
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
        _logger.error(f"[DB] Failed to add agent memory: {e}")
        return None

def update_memory_content(msg_id: str, content: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE chat SET content = ? WHERE id = ?", (content, msg_id))
                row = conn.execute("SELECT * FROM chat WHERE id = ?", (msg_id,)).fetchone()
                return _legacy_row_to_msg(row) if row else None
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to update memory content: {e}")
        return None

def delete_memory_by_id(msg_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE id = ?", (msg_id,))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete memory {msg_id}: {e}")

def delete_agent_memories(agent_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = ?", (agent_id,))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete agent memories for {agent_id}: {e}")

def search_memories(query: str, project: str = "default") -> list:
    try:
        with get_db_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM chat 
                WHERE project = ? AND content LIKE ? 
                ORDER BY timestamp DESC
            """, (project, f"%{query}%")).fetchall()
            return [_legacy_row_to_msg(r) for r in rows]
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to search memories: {e}")
        return []

def get_chat_count(agent_id: str = None) -> int:
    try:
        with get_db_conn() as conn:
            if agent_id:
                row = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = ?", (agent_id,)).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) FROM chat").fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to count chat messages: {e}")
        return 0

def clear_project_chat(project: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = 'war-room' AND project = ?", (project,))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to clear project chat: {e}")

def delete_project_completely(project: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE project = ?", (project,))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete project completely: {e}")

def clear_project_chat_by_sender(project: str, sender: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = 'war-room' AND project = ? AND LOWER(sender) = ?", (project, sender.lower()))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to clear project chat by sender: {e}")
