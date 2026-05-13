from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from .db import get_db, save_db
from .models import AgentEntry
router = APIRouter()
@router.get("/api/agents")
def list_agents(): return get_db("agents")
@router.get("/api/agents/search")
def search_agents(q: str): return [a for a in get_db("agents") if q.lower() in str(a).lower()]
@router.get("/api/agents/{a_id}")
def get_agent(a_id: str): return next((a for a in get_db("agents") if a.get("id") == a_id), {})
@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str): return {"status": next((a.get("status") for a in get_db("agents") if a.get("id") == a_id), "offline")}
@router.post("/api/agents")
def create_agent(a: AgentEntry):
    d = get_db("agents")
    if any(x.get("name") == a.name for x in d): raise HTTPException(400, "")
    n = {"id": str(uuid.uuid4()), "name": a.name, "description": a.description, "status": a.status, "created_at": datetime.utcnow().isoformat() + "Z"}
    save_db("agents", d + [n]); return n
@router.put("/api/agents/{a_id}/status")
def set_status(a_id: str, status: str):
    d = get_db("agents")
    for a in d:
        if a.get("id") == a_id: a["status"] = status; save_db("agents", d); return a
@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str):
    save_db("agents", [a for a in get_db("agents") if a.get("id") != a_id])
    save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != a_id])
@router.get("/api/stats")
def get_system_stats(): return {"agents": len(get_db("agents")), "memory": len(get_db("memory"))}
