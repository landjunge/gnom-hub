import json, os
from fastapi import APIRouter
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from gnom_hub.core.config import TOKENS_FILE

router = APIRouter(tags=["agents"])

@router.get("/api/agents")
def list_agents():
    repo = SQLiteAgentRepository()
    ags = [dict(a.__dict__) for a in repo.get_all()]
    for a in ags:
        if a.get("active_job"): a["status"] = "busy"
        elif a.get("status") == "running": a["status"] = "online"
    return ags

@router.get("/api/agents/search")
def search_agents(q: str):
    return [a for a in list_agents() if q.lower() in str(a).lower()]

@router.get("/api/agents/{a_id}")
def get_agent(a_id: str):
    return next((a for a in list_agents() if a.get("id") == a_id or a.get("name") == a_id), {})

@router.get("/api/stats")
def get_system_stats():
    from gnom_hub.soul import SOULS
    from gnom_hub.infrastructure.database.chat_repo import SQLiteChatRepository
    from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
    from gnom_hub.memory.smr.smr_stats import get_memory_stats
    sys_set = {k for k, v in SOULS.items() if v.get("role") not in ("writer","coder","researcher","editor")}
    d = json.load(open(str(TOKENS_FILE))) if os.path.exists(str(TOKENS_FILE)) else {}
    ags = list_agents()
    sa = sum(1 for a in ags if a.get("name","").lower() in sys_set)
    cc = SQLiteChatRepository().count_messages()
    mem = get_memory_stats().get("total_facts", 0)
    tfb = SQLiteStateRepository().get_value("tokens", [{}])[0].get("total", 0) if SQLiteStateRepository().get_value("tokens") else 0
    return {"agents": len(ags), "sys_agents": sa, "work_agents": len(ags) - sa, "memory": mem, "chat": cc, "tokens": d.get("total", tfb), "tokens_free": d.get("total_free", 0), "tokens_pay": d.get("total_pay", 0)}
