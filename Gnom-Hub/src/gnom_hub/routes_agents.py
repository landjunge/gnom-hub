from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from .db import get_db, save_db
from .models import AgentEntry

router = APIRouter()

@router.get("/api/agents")
def list_agents(): return get_db("agents")

@router.post("/api/agents")
def create_agent(agent: AgentEntry):
    data = get_db("agents")
    if any(a.get("name") == agent.name for a in data): raise HTTPException(400, "Existiert.")
    n = {"id": str(uuid.uuid4()), "name": agent.name, "description": agent.description, "status": agent.status, "created_at": datetime.utcnow().isoformat() + "Z"}
    save_db("agents", data + [n])
    return n

@router.put("/api/agents/{a_id}/status")
def set_status(a_id: str, status: str):
    d = get_db("agents")
    for a in d:
        if a.get("id") == a_id:
            a["status"] = status
            save_db("agents", d)
            return a
    raise HTTPException(404, "Fehlt.")
