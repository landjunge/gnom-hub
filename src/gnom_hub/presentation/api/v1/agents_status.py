from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from gnom_hub.domain.agent.entities import Agent
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.database.chat_repo import SQLiteChatRepository

router = APIRouter()

class AgentEntry(BaseModel):
    name: str
    description: str
    status: str

class StatusUpdate(BaseModel):
    status: str

@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str):
    repo = SQLiteAgentRepository()
    a = repo.get_by_id(a_id)
    st = a.status if a else "offline"
    if st == "running": st = "online"
    return {"status": st}

@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
async def set_status(a_id: str, request: Request, update: Optional[StatusUpdate] = None, status: Optional[str] = Query(None)):
    real_status = status
    if not real_status and request.method == "POST":
        try:
            body = await request.json()
            real_status = body.get("status") if isinstance(body, dict) else None
        except Exception: pass
    if not real_status and update:
        real_status = update.status
    if not real_status: raise HTTPException(422, "Missing 'status'")
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    repo.update_status(agent.name, real_status)
    return {"status": real_status}

@router.post("/api/agents")
def create_agent(a: AgentEntry):
    repo = SQLiteAgentRepository()
    agent = Agent(name=a.name, id=str(uuid4()), port=0, description=a.description, status=a.status, capabilities=[], role="normal", active_job=None, last_seen=datetime.now(timezone.utc))
    repo.save(agent)
    return agent.__dict__

@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str):
    SQLiteAgentRepository().delete_by_id(a_id)
    SQLiteChatRepository().delete_by_agent(a_id)
    return {"status": "deleted"}
