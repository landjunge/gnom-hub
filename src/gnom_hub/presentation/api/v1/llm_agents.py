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
    db = SQLiteStateRepository()
    data = await req.json()
    db.set_value("llm_agents", data)
    preset = db.get_value("active_preset", "Web Development")
    if isinstance(preset, str):
        preset = preset.strip('"\'')
    db.set_value(f"llm_preset_{preset}", data)
    return {"status": "ok"}

@router.post("/api/llm/test_agent")
async def test_agent(req: Request):
    j = await req.json()
    p, m = j.get("provider"), j.get("model")
    kdb = SQLiteStateRepository().get_value("llm_keys", {})
    if p == "auto":
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        p, m = SmartRouter.resolve_stage(m, kdb, j.get("agent", "Test"))
    k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p and x.get("valid")), None)
    if not k:
        k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p), None)
    if not k:
        if p == "deepseek" and DS_KEY: k = DS_KEY
        elif p == "openrouter" and OR_KEY: k = OR_KEY
    if not k and p != "lokal": return {"valid": False, "info": f"Kein gültiger Key für {p}", "resolved_provider": p, "resolved_model": m, "caps": []}
    # Caps vom Key oder Provider bestimmen
    key_caps = []
    if p == "lokal":
        key_caps = ["text", "vision", "tools"]
    else:
        for x in (kdb.values() if isinstance(kdb, dict) else kdb):
            if x.get("provider") == p and x.get("valid") and x.get("caps"):
                key_caps = x["caps"]
                break
    if not key_caps:
        key_caps = ["text", "tools"]
    try:
        loop = asyncio.get_running_loop()
        ans = await loop.run_in_executor(None, _call, p, m, k or "", [{"role":"user", "content":"Ping. Reply OK."}], "Test")
        return {"valid": bool(ans), "info": "OK" if ans else "Keine Antwort", "resolved_provider": p, "resolved_model": m, "caps": key_caps if ans else []}
    except Exception as e: return {"valid": False, "info": str(e), "resolved_provider": p, "resolved_model": m, "caps": []}

@router.get("/api/llm/routing_insights")
async def get_routing_insights():
    db = SQLiteStateRepository()
    kdb = db.get_value("llm_keys", {})
    adb = db.get_value("llm_agents", {})
    from gnom_hub.infrastructure.router.router_stage import SmartRouter
    return SmartRouter.get_routing_insights(kdb, adb)
