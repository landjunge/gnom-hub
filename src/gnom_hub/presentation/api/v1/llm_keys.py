from fastapi import APIRouter, Request
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, verify_key
from gnom_hub.infrastructure.llm.desktop_syncer import sync_desktop_keys, write_keys_to_desktop

router = APIRouter()

@router.get("/api/llm/keys")
async def get_keys():
    d = SQLiteStateRepository().get_value("llm_keys", {})
    return await sync_desktop_keys(d if isinstance(d, dict) else {})

@router.post("/api/llm/keys")
async def save_keys(req: Request):
    j = await req.json()
    SQLiteStateRepository().set_value("llm_keys", j)
    write_keys_to_desktop(j)
    return {"status": "ok"}

@router.post("/api/llm/test")
async def test_key(req: Request):
    j = await req.json()
    k, p, l = j.get("key"), j.get("provider"), j.get("label", "")
    if p: return await verify_key(p, k)
    return await auto_detect_and_verify(k, l)

@router.post("/api/llm/auto_assign")
async def auto_assign():
    db, rep = SQLiteStateRepository(), SQLiteAgentRepository()
    agents, maps = rep.get_all(), {}
    for a in agents:
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        maps[a.name.lower()] = {"provider": "auto", "model": SmartRouter.get_stage_for_role(a.role or "normal")}
    db.set_value("llm_agents", maps)
    return {"status": "ok"}
