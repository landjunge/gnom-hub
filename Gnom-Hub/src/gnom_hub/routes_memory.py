from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from .db import get_db, save_db
from .models import MemoryEntry, AgentIdReq

router = APIRouter()

@router.post("/api/memory")
def add_memory(entry: MemoryEntry):
    if not any(a.get("id") == entry.agent_id for a in get_db("agents")):
        raise HTTPException(status_code=404, detail="Agent nicht gefunden.")
    
    data = get_db("memory")
    new_entry = {
        "id": str(uuid.uuid4()),
        "agent_id": entry.agent_id,
        "content": entry.content,
        "timestamp": entry.timestamp or (datetime.utcnow().isoformat() + "Z")
    }
    data.append(new_entry)
    save_db("memory", data)
    return new_entry

@router.get("/api/memory/search")
def search_memory(q: str):
    return [e for e in get_db("memory") if q.lower() in str(e.get("content", "")).lower()]

@router.get("/api/agents/{agent_id}/memory")
def get_agent_memory(agent_id: str):
    mems = [m for m in get_db("memory") if m.get("agent_id") == agent_id]
    mems.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return mems

@router.post("/api/tools/get_memory")
def proxy_get_memory(req: AgentIdReq):
    return get_agent_memory(req.agent_id)
