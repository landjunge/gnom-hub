from fastapi import APIRouter, HTTPException, Request; from datetime import datetime; import uuid, os, json; from .db import get_db, save_db; from .models import AgentEntry
router = APIRouter()
@router.get("/api/agents")
def list_agents(): return get_db("agents")
@router.get("/api/agents/search")
def search_agents(q: str): return [a for a in get_db("agents") if q.lower() in str(a).lower()]
@router.get("/api/agents/{a_id}")
def get_agent(a_id: str): return next((a for a in get_db("agents") if a.get("id") == a_id or a.get("name") == a_id), {})
@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str): return {"status": next((a.get("status") for a in get_db("agents") if a.get("id") == a_id or a.get("name") == a_id), "offline")}
@router.post("/api/agents")
def create_agent(a: AgentEntry):
    d = get_db("agents")
    if any(x.get("name") == a.name for x in d): raise HTTPException(400, "")
    n = {"id": str(uuid.uuid4()), "name": a.name, "description": a.description, "status": a.status, "created_at": datetime.utcnow().isoformat() + "Z"}
    save_db("agents", d + [n]); return n
@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
async def set_status(a_id: str, request: Request, status: str = None):
    # Accept status from query param, JSON body, or form data
    if status is None:
        try:
            body = await request.json()
            status = body.get("status") if isinstance(body, dict) else None
        except: pass
    if not status: raise HTTPException(422, "Missing 'status' — pass as ?status=... or JSON body {\"status\": \"...\"}")
    d = get_db("agents")
    for a in d:
        if a.get("id") == a_id or a.get("name") == a_id: a["status"] = status; save_db("agents", d); return a
@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str): save_db("agents", [a for a in get_db("agents") if a.get("id") != a_id]); save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != a_id])
from .soul_initializer import SOULS; SYS = {k for k, v in SOULS.items() if v.get("role") not in ("writer","coder","researcher","editor","web_crawler","data_crawler","smart_crawler")}
@router.get("/api/stats")
def get_system_stats(): 
    tf = os.path.join(os.path.dirname(__file__), "../../.gnom-hub-tokens.json"); d = json.load(open(tf)) if os.path.exists(tf) else {}
    ags = get_db("agents"); sa = sum(1 for a in ags if a.get("name","").lower() in SYS)
    return {"agents": len(ags), "sys_agents": sa, "work_agents": len(ags) - sa, "memory": len(get_db("memory")), "chat": len(get_db("chat")), "tokens": d.get("total", get_db("tokens")[0].get("total", 0) if get_db("tokens") else 0), "tokens_free": d.get("total_free", 0), "tokens_pay": d.get("total_pay", 0)}
@router.get("/api/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "uptime": "alive"}
