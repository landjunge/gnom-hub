from fastapi import APIRouter
from datetime import datetime
from .db import get_db, save_db
from pydantic import BaseModel
router = APIRouter()
class RegisterPayload(BaseModel):
    name: str
    port: int
    description: str = ""
@router.post("/api/agents/register")
def register_agent(p: RegisterPayload):
    agents = get_db("agents")
    for a in agents:
        if a.get("name") == p.name:
            a["status"] = "online"; a["port"] = p.port; a["description"] = p.description or str(p.port)
            a["last_seen"] = datetime.utcnow().isoformat() + "Z"
            save_db("agents", agents); return a
    import uuid
    n = {"id": str(uuid.uuid4()), "name": p.name, "port": p.port, "description": p.description or str(p.port),
         "status": "online", "created_at": datetime.utcnow().isoformat() + "Z", "last_seen": datetime.utcnow().isoformat() + "Z"}
    save_db("agents", agents + [n]); return n
@router.post("/api/agents/{a_id}/heartbeat")
def heartbeat(a_id: str):
    agents = get_db("agents")
    for a in agents:
        if a.get("id") == a_id:
            a["status"] = "online"; a["last_seen"] = datetime.utcnow().isoformat() + "Z"
            save_db("agents", agents); return a
    return {"error": "not found"}
