from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel
from gnom_hub.agents.entities import Agent
from gnom_hub.db.agent_repo import SQLiteAgentRepository

router = APIRouter()

class RegisterPayload(BaseModel):
    name: str
    port: int
    description: str = ""

@router.post("/api/agents/register")
def register_agent(p: RegisterPayload):
    repo = SQLiteAgentRepository()
    a = repo.get_by_name(p.name)
    if a:
        a.port, a.description, a.status, a.last_seen = p.port, p.description or str(p.port), "online", datetime.now(timezone.utc)
    else:
        a = Agent(name=p.name, id=str(uuid4()), port=p.port, description=p.description or str(p.port), status="online", capabilities=[], role="normal", active_job=None, last_seen=datetime.now(timezone.utc))
    repo.save(a)
    return a.__dict__

@router.post("/api/agents/{a_id}/heartbeat")
def heartbeat(a_id: str):
    repo = SQLiteAgentRepository()
    a = repo.get_by_id(a_id)
    if not a: return {"error": "not found"}
    repo.update_status(a.name, "online")
    return {"status": "online"}
