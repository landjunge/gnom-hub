from fastapi import APIRouter, HTTPException, Request; from datetime import datetime, timezone; import json, os; from .models import AgentEntry
router = APIRouter()
@router.get("/api/agents")
def list_agents():
    from .db import get_all_agents; ags = get_all_agents()
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
    from .db import create_agent_record; n = create_agent_record(a.name, a.description, a.status)
    if not n: raise HTTPException(400, "Already exists"); return n
@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
async def set_status(a_id: str, request: Request, status: str = None):
    if status is None:
        try: body = await request.json(); status = body.get("status") if isinstance(body, dict) else None
        except Exception: pass
    if not status: raise HTTPException(422, "Missing 'status'")
    from .db import set_agent_status; a = set_agent_status(a_id, status)
    if not a: raise HTTPException(404, "Agent not found"); return a
@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str):
    from .db import delete_agent_by_id, delete_agent_memories; delete_agent_by_id(a_id); delete_agent_memories(a_id)
from .soul_initializer import SOULS; SYS = {k for k, v in SOULS.items() if v.get("role") not in ("writer","coder","researcher","editor")}
@router.get("/api/stats")
def get_system_stats():
    from .config import TOKENS_FILE; from .db import get_chat_count, get_state_value; d = json.load(open(str(TOKENS_FILE))) if os.path.exists(str(TOKENS_FILE)) else {}
    ags = list_agents(); sa = sum(1 for a in ags if a.get("name","").lower() in SYS)
    tfb = get_state_value("tokens", [{}])[0].get("total", 0) if get_state_value("tokens") else 0
    cc = get_chat_count()
    return {"agents": len(ags), "sys_agents": sa, "work_agents": len(ags) - sa, "memory": cc, "chat": cc, "tokens": d.get("total", tfb), "tokens_free": d.get("total_free", 0), "tokens_pay": d.get("total_pay", 0)}
@router.get("/api/health")
def health(): return {"status": "ok", "agents": len(list_agents()), "uptime": "alive"}
