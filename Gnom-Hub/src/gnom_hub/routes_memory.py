from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from .db import get_db, save_db
from .models import MemoryEntry, AgentIdReq, SearchReq
from .routes_nudge import nudge
router = APIRouter()
@router.post("/api/memory")
@router.post("/api/tools/save_memory")
def add_memory(e: MemoryEntry):
    if not any(a.get("id") == e.agent_id for a in get_db("agents")): raise HTTPException(404, "")
    e.timestamp = e.timestamp or (datetime.utcnow().isoformat() + "Z")
    n = {"id": str(uuid.uuid4()), **e.dict()}; save_db("memory", get_db("memory") + [n])
    nudge(e.agent_id)
    return n
@router.get("/api/memory/search")
def search_memory(q: str): return sorted([e for e in get_db("memory") if q.lower() in str(e.get("content", "")).lower()], key=lambda x: x.get("timestamp", ""), reverse=True)
@router.get("/api/agents/{a_id}/memory")
def get_agent_memory(a_id: str): return sorted([m for m in get_db("memory") if m.get("agent_id") == a_id], key=lambda x: x.get("timestamp", ""), reverse=True)
@router.get("/api/agents/{a_id}/memory/count")
def count_memory(a_id: str): return {"count": sum(1 for m in get_db("memory") if m.get("agent_id") == a_id)}
@router.post("/api/tools/get_memory")
def proxy_get_memory(r: AgentIdReq): return get_agent_memory(r.agent_id)
@router.post("/api/tools/search_memory")
def proxy_search_memory(r: SearchReq): return search_memory(r.query)
@router.put("/api/memory/{m_id}")
def update_memory(m_id: str, content: str):
    d = get_db("memory")
    for m in d:
        if m.get("id") == m_id: m["content"] = content; save_db("memory", d); return m
@router.delete("/api/memory/{m_id}")
def delete_memory(m_id: str): save_db("memory", [m for m in get_db("memory") if m.get("id") != m_id])
@router.delete("/api/agents/{a_id}/memory")
def clear_agent_memory(a_id: str): save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != a_id])
