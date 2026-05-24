from fastapi import APIRouter, HTTPException, Request; from datetime import datetime, timezone; import uuid, os, json; from .db import get_db, save_db; from .models import AgentEntry
router = APIRouter()
@router.get("/api/agents")
def list_agents():
    ags = get_db("agents")
    for a in ags:
        if a.get("active_job"): a["status"] = "busy"
    return ags
@router.get("/api/agents/search")
def search_agents(q: str): return [a for a in list_agents() if q.lower() in str(a).lower()]
@router.get("/api/agents/{a_id}")
def get_agent(a_id: str): return next((a for a in list_agents() if a.get("id") == a_id or a.get("name") == a_id), {})
@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str): return {"status": get_agent(a_id).get("status", "offline")}
@router.post("/api/agents")
def create_agent(a: AgentEntry):
    d = get_db("agents")
    if any(x.get("name") == a.name for x in d): raise HTTPException(400, "")
    n = {"id": str(uuid.uuid4()), "name": a.name, "description": a.description, "status": a.status, "created_at": datetime.now(timezone.utc).isoformat() + "Z"}
    save_db("agents", d + [n]); return n
@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
async def set_status(a_id: str, request: Request, status: str = None):
    if status is None:
        try: body = await request.json(); status = body.get("status") if isinstance(body, dict) else None
        except Exception: pass
    if not status: raise HTTPException(422, "Missing 'status' — pass as ?status=... or JSON body {\"status\": \"...\"}")
    d = get_db("agents")
    for a in d:
        if a.get("id") == a_id or a.get("name") == a_id: a["status"] = status; save_db("agents", d); return a
@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str): save_db("agents", [a for a in get_db("agents") if a.get("id") != a_id]); save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != a_id])
from .soul_initializer import SOULS; SYS = {k for k, v in SOULS.items() if v.get("role") not in ("writer","coder","researcher","editor")}
@router.get("/api/stats")
def get_system_stats():
    from .config import TOKENS_FILE; d = json.load(open(str(TOKENS_FILE))) if os.path.exists(str(TOKENS_FILE)) else {}
    ags = get_db("agents"); sa = sum(1 for a in ags if a.get("name","").lower() in SYS)
    tdb = get_db("tokens"); tfb = tdb[0].get("total", 0) if tdb else 0
    return {"agents": len(ags), "sys_agents": sa, "work_agents": len(ags) - sa, "memory": len(get_db("memory")), "chat": len(get_db("chat")), "tokens": d.get("total", tfb), "tokens_free": d.get("total_free", 0), "tokens_pay": d.get("total_pay", 0)}
@router.get("/api/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "uptime": "alive"}
