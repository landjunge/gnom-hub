from fastapi import APIRouter; from pydantic import BaseModel; from .db import register_agent_in_db, set_agent_status
router = APIRouter()
class RegisterPayload(BaseModel):
    name: str
    port: int
    description: str = ""
@router.post("/api/agents/register")
def register_agent(p: RegisterPayload):
    r = register_agent_in_db(p.name, p.port, p.description)
    if not r: from fastapi import HTTPException; raise HTTPException(500, "Registration failed")
    return r
@router.post("/api/agents/{a_id}/heartbeat")
def heartbeat(a_id: str):
    r = set_agent_status(a_id, "online")
    if not r: return {"error": "not found"}
    return r
