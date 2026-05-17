from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from .db import get_db, save_db
from .models import AgentEntry
router = APIRouter()
@router.get("/api/agents")
def list_agents(): return get_db("agents")
@router.get("/api/agents/search")
def search_agents(q: str): return [a for a in get_db("agents") if q.lower() in str(a).lower()]
@router.get("/api/agents/{a_id}")
def get_agent(a_id: str): return next((a for a in get_db("agents") if a.get("id") == a_id), {})
@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str): return {"status": next((a.get("status") for a in get_db("agents") if a.get("id") == a_id), "offline")}
@router.post("/api/agents")
def create_agent(a: AgentEntry):
    d = get_db("agents")
    if any(x.get("name") == a.name for x in d): raise HTTPException(400, "")
    n = {"id": str(uuid.uuid4()), "name": a.name, "description": a.description, "status": a.status, "created_at": datetime.utcnow().isoformat() + "Z"}
    save_db("agents", d + [n]); return n
@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
def set_status(a_id: str, status: str):
    d = get_db("agents")
    for a in d:
        if a.get("id") == a_id: a["status"] = status; save_db("agents", d); return a
@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str): save_db("agents", [a for a in get_db("agents") if a.get("id") != a_id]); save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != a_id])
SYS_NAMES = {'watchdogag', 'skillsag', 'backupag', 'cronjobag', 'soulag', 'summarizerag', 'generalag', 'securityag'}
@router.get("/api/stats")
def get_system_stats(): 
    tok = get_db("tokens")
    t_count = tok[0].get("total", 0) if tok else 0
    t_free = 0
    t_pay = 0
    import os, json
    tf = os.path.join(os.path.dirname(__file__), "../../.gnom-hub-tokens.json")
    if os.path.exists(tf):
        try:
            d = json.load(open(tf))
            t_free = d.get("total_free", 0)
            t_pay = d.get("total_pay", 0)
            t_count = d.get("total", t_count)
        except Exception as e: print(f"[STATS] Token-Datei Fehler: {e}")
    agents = get_db("agents")
    sys_a = sum(1 for a in agents if (a.get("name","").lower()) in SYS_NAMES)
    return {"agents": len(agents), "sys_agents": sys_a, "work_agents": len(agents) - sys_a, "memory": len(get_db("memory")), "chat": len(get_db("chat")), "tokens": t_count, "tokens_free": t_free, "tokens_pay": t_pay}
@router.get("/api/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "uptime": "alive"}
