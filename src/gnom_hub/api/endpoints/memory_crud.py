from datetime import datetime, timezone
import uuid; from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from gnom_hub.chat.entities import ChatMessage
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository
from gnom_hub.api.endpoints.nudge import nudge

router = APIRouter()
class MemoryEntry(BaseModel):
    agent_id: str; content: str; timestamp: Optional[str] = None

@router.post("/api/memory")
@router.post("/api/tools/save_memory")
def add_memory(e: MemoryEntry):
    if not SQLiteAgentRepository().get_by_name(e.agent_id): raise HTTPException(404, "Agent not found")
    m = ChatMessage(id=str(uuid.uuid4()), project="default", sender="user", agent_id=e.agent_id, msg_type="chat", content=e.content, timestamp=datetime.now(timezone.utc))
    SQLiteChatRepository().add_message(m); nudge(e.agent_id); return m.__dict__

@router.get("/api/agents/{a_id}/memory")
def get_agent_memory(a_id: str):
    return [dict(m.__dict__) for m in SQLiteChatRepository().get_agent_memories(a_id, 100)]

@router.get("/api/agents/{a_id}/memory/count")
def count_memory(a_id: str): return {"count": SQLiteChatRepository().count_messages_for_agent(a_id)}

@router.put("/api/memory/{m_id}")
async def update_memory(m_id: str, request: Request):
    body = await request.json(); content = body.get("content") if isinstance(body, dict) else None
    if not content: raise HTTPException(422, "Missing 'content'")
    m = SQLiteChatRepository().update_message_content(m_id, content)
    if not m: raise HTTPException(404, "Not found")
    return m.__dict__

@router.delete("/api/memory/{m_id}")
def delete_memory(m_id: str): SQLiteChatRepository().delete_by_id(m_id); return {"status": "ok"}

@router.delete("/api/agents/{a_id}/memory")
def clear_agent_memory(a_id: str): SQLiteChatRepository().delete_by_agent(a_id); return {"status": "ok"}

class SoulSaveRequest(BaseModel):
    key: str
    value: str
    priority: str = "medium"

@router.post("/api/soul/save")
def save_soul_fact(req: SoulSaveRequest):
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as conn:
        existing = conn.execute("SELECT key FROM soul_memory WHERE key = ?", (req.key,)).fetchone()
        if existing:
            conn.execute("UPDATE soul_memory SET value = ?, priority = ?, timestamp = ? WHERE key = ?",
                         (req.value, req.priority, __import__('datetime').datetime.now().isoformat(), req.key))
        else:
            conn.execute("INSERT INTO soul_memory (key, value, priority, timestamp, agent) VALUES (?, ?, ?, ?, ?)",
                         (req.key, req.value, req.priority, __import__('datetime').datetime.now().isoformat(), "System"))
    return {"status": "ok"}


@router.get("/api/soul/all/{agent_name}")
def get_all_soul_facts(agent_name: str):
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as conn:
        facts = conn.execute(
            "SELECT key, value, priority, timestamp, agent FROM soul_memory WHERE LOWER(agent) = LOWER(?) OR LOWER(agent) = 'system' OR agent = 'System' ORDER BY timestamp DESC LIMIT 100",
            (agent_name,)
        ).fetchall()
        return [{"key": f["key"], "value": f["value"], "priority": f["priority"],
                 "timestamp": f["timestamp"], "agent": f["agent"]} for f in facts]


class SoulDeleteRequest(BaseModel):
    key: str

@router.post("/api/soul/delete")
def delete_soul_fact(req: SoulDeleteRequest):
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as conn:
        conn.execute("DELETE FROM soul_memory WHERE key = ?", (req.key,))
    return {"status": "ok"}
