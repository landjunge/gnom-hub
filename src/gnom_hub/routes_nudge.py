from fastapi import APIRouter
import requests
from .db import get_db
from .log import get_logger

router = APIRouter()
logger = get_logger("nudge")

def nudge(agent_id: str):
    """Informiert den Agenten über neue Daten (nur wenn Agent einen aktiven Port hat)."""
    agent = next((a for a in get_db("agents") if a["id"] == agent_id), None)
    if not agent or agent.get("status") != "online": return False
    port = agent.get("port", 0)
    if not port or port == 0:
        return False  # Agent hat keinen aktiven Server-Port (polling-basiert)
    try:
        requests.post(f"http://127.0.0.1:{port}/nudge", timeout=1)
        return True
    except Exception:
        return False

@router.post("/api/agents/{a_id}/nudge")
def nudge_agent(a_id: str): return {"nudged": nudge(a_id)}
