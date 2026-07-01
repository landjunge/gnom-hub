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
    import logging
    logger = logging.getLogger("gnom_hub.api.registry")
    logger.info(f"=== REGISTER REQUEST: name={p.name!r}, port={p.port} ===")
    repo = SQLiteAgentRepository()
    a = repo.get_by_name(p.name)
    if a:
        logger.info(f"Agent {p.name!r} found in DB. Role: {a.role!r}")
        a.port, a.description, a.status, a.last_seen = p.port, p.description or str(p.port), "online", datetime.now(timezone.utc)
    else:
        logger.info(f"Agent {p.name!r} NOT found in DB. Creating new agent with role='normal'")
        a = Agent(name=p.name, id=str(uuid4()), port=p.port, description=p.description or str(p.port), status="online", capabilities=[], role="normal", active_job=None, last_seen=datetime.now(timezone.utc))
    try:
        repo.save(a)
        logger.info(f"Agent {p.name!r} saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save agent {p.name!r}: {e}")
        raise
    return a.__dict__

@router.post("/api/agents/{a_id}/heartbeat")
def heartbeat(a_id: str):
    repo = SQLiteAgentRepository()
    a = repo.get_by_id(a_id)
    if not a:
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        key = a_id.lower()
        if key in AGENT_DEFINITIONS:
            defn = AGENT_DEFINITIONS[key]
            a = Agent(
                name=defn["name"],
                id=str(uuid4()),
                port=0,
                description=defn["description"],
                status="online",
                capabilities=defn.get("capabilities", []),
                role=defn["role"],
                active_job=None,
                last_seen=datetime.now(timezone.utc)
            )
            repo.save(a)
        else:
            return {"error": "not found"}
    repo.update_status(a.name, "online")
    return {"status": "online"}
