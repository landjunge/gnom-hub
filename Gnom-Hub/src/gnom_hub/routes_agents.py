from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid

from .db import get_db, save_db
from .models import AgentEntry

router = APIRouter()

@router.get("/api/agents")
def list_agents():
    """Gibt eine Liste aller registrierten Agenten zurück."""
    return get_db("agents")

@router.post("/api/agents")
def create_agent(agent: AgentEntry):
    """Legt einen neuen Agenten im System an."""
    data = get_db("agents")
    if any(a.get("name") == agent.name for a in data):
        raise HTTPException(status_code=400, detail="Agent existiert bereits.")
        
    new_agent = {
        "id": str(uuid.uuid4()),
        "name": agent.name,
        "description": agent.description,
        "status": agent.status,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    data.append(new_agent)
    save_db("agents", data)
    return new_agent
