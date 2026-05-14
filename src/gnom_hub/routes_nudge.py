from fastapi import APIRouter
import requests
from .db import get_db
router = APIRouter()

def nudge(agent_id: str):
    """Informiert den Agenten über neue Daten."""
    agent = next((a for a in get_db("agents") if a["id"] == agent_id), None)
    if not agent or agent.get("status") != "online": return False
    try:
        requests.post(f"http://127.0.0.1:{agent['port']}/nudge", timeout=1)
        return True
    except: return False

@router.post("/api/agents/{a_id}/nudge")
def nudge_agent(a_id: str): return {"nudged": nudge(a_id)}
