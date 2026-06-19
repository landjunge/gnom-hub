from fastapi import APIRouter
import requests
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.core.logger import get_logger

router = APIRouter()
logger = get_logger("nudge")

def nudge(agent_id: str):
    agent = SQLiteAgentRepository().get_by_id(agent_id)
    if not agent or agent.status != "online": return False
    port = agent.port
    if not port or port == 0: return False
    try:
        requests.post(f"http://127.0.0.1:{port}/nudge", timeout=1)
        return True
    except Exception:
        return False

@router.post("/api/agents/{a_id}/nudge")
def nudge_agent(a_id: str):
    return {"nudged": nudge(a_id)}
