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
    except:
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
