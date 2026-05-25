import asyncio
from fastapi import APIRouter, Request
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.router.router_config import DS_KEY, OR_KEY
from gnom_hub.infrastructure.router.router_call import _call

router = APIRouter()

@router.get("/api/llm/agents")
def get_agent_llm():
    d = SQLiteStateRepository().get_value("llm_agents", {})
    return d if isinstance(d, dict) else {}

@router.post("/api/llm/agents")
async def save_agent_llm(req: Request):
    SQLiteStateRepository().set_value("llm_agents", await req.json())
    return {"status": "ok"}

@router.post("/api/llm/test_agent")
async def test_agent(req: Request):
    j = await req.json()
    p, m = j.get("provider"), j.get("model")
    kdb = SQLiteStateRepository().get_value("llm_keys", {})
    if p == "auto":
        from gnom_hub.infrastructure.router.router_stage_compat import resolve_stage
        p, m = resolve_stage(m, kdb, j.get("agent", "Test"))
    k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p and x.get("valid")), None)
    if not k:
        if p == "deepseek" and DS_KEY: k = DS_KEY
        elif p == "openrouter" and OR_KEY: k = OR_KEY
    if not k and p != "lokal": return {"valid": False, "info": f"Kein gültiger Key für {p}", "resolved_provider": p, "resolved_model": m}
    try:
        loop = asyncio.get_running_loop()
        ans = await loop.run_in_executor(None, _call, p, m, k or "", [{"role":"user", "content":"Ping. Reply OK."}], "Test")
        return {"valid": bool(ans), "info": "OK" if ans else "Keine Antwort", "resolved_provider": p, "resolved_model": m}
    except Exception as e: return {"valid": False, "info": str(e), "resolved_provider": p, "resolved_model": m}
