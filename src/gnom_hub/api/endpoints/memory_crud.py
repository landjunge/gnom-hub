import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from gnom_hub.api.endpoints.auth import verify_admin
from gnom_hub.api.endpoints.nudge import nudge
from gnom_hub.chat.entities import ChatMessage
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository

router = APIRouter()
class MemoryEntry(BaseModel):
    agent_id: str; content: str; timestamp: str | None = None

@router.post("/api/memory")
@router.post("/api/tools/save_memory")
def add_memory(e: MemoryEntry):
    if not SQLiteAgentRepository().get_by_name(e.agent_id): raise HTTPException(404, "Agent not found")
    m = ChatMessage(agent_id=uuid.UUID(e.agent_id), role="user", content=e.content, id=uuid.uuid4(), timestamp=datetime.now(timezone.utc))
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
def save_soul_fact(req: SoulSaveRequest, _=Depends(verify_admin)):
    """
    Save a SoulAG fact via the Smart-Dedup engine.

    MIN_VALUE_LENGTH check + Jaccard/prefix dedup are delegated to
    ``save_soul_fact_smart`` (see gnom_hub.db.soul_repo).

    The engine returns:
      - the canonical (normalized) key on success (inserted/merged/updated);
      - ``None`` when the fact was rejected (too short or empty).

    HTTP response shape:
        success:  {"status": "ok",      "action": "saved", "key": "<canonical key>"}
        reject:   {"status": "rejected", "action": "rejected", "key": "<original key>"}
    """
    from gnom_hub.db.soul_repo import save_soul_fact_smart

    effective_key = save_soul_fact_smart(
        req.key, req.value, agent="SoulAG", priority=req.priority,
    )

    if effective_key is None:
        # Engine rejected: too short (< MIN_VALUE_LENGTH) or empty after normalize
        return {"status": "rejected", "action": "rejected", "key": req.key}

    return {"status": "ok", "action": "saved", "key": effective_key}


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
def delete_soul_fact(req: SoulDeleteRequest, _=Depends(verify_admin)):
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM soul_memory WHERE key = ?", (req.key,))
    return {"status": "ok"}
