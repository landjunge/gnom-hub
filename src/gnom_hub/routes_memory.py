from fastapi import APIRouter, HTTPException, Request
from .models import MemoryEntry, AgentIdReq, SearchReq
from .routes_nudge import nudge
router = APIRouter()
@router.post("/api/memory")
@router.post("/api/tools/save_memory")
def add_memory(e: MemoryEntry):
    from .db import agent_exists, add_agent_memory
    if not agent_exists(e.agent_id): raise HTTPException(404, "Agent not found")
    n = add_agent_memory(e.agent_id, e.content, e.timestamp)
    if not n: raise HTTPException(500, "Database error")
    nudge(e.agent_id); return n
@router.get("/api/memory/search")
def search_memory(q: str):
    from .db import search_memories; return search_memories(q)
@router.get("/api/agents/{a_id}/memory")
def get_agent_memory(a_id: str):
    from .db import get_agent_memories; return get_agent_memories(a_id)
@router.get("/api/agents/{a_id}/memory/count")
def count_memory(a_id: str):
    from .db import count_agent_memories; return {"count": count_agent_memories(a_id)}
@router.post("/api/tools/get_memory")
def proxy_get_memory(r: AgentIdReq): return get_agent_memory(r.agent_id)
@router.post("/api/tools/search_memory")
def proxy_search_memory(r: SearchReq): return search_memory(r.query)
@router.put("/api/memory/{m_id}")
async def update_memory(m_id: str, request: Request):
    body = await request.json(); content = body.get("content") if isinstance(body, dict) else None
    if not content: raise HTTPException(422, "Missing 'content'")
    from .db import update_memory_content; m = update_memory_content(m_id, content)
    if not m: raise HTTPException(404, "Not found"); return m
@router.delete("/api/memory/{m_id}")
def delete_memory(m_id: str):
    from .db import delete_memory_by_id; delete_memory_by_id(m_id)
@router.delete("/api/agents/{a_id}/memory")
def clear_agent_memory(a_id: str):
    from .db import delete_agent_memories; delete_agent_memories(a_id)
