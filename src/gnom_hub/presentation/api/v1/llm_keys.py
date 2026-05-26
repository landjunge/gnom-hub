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
    # Speichere alle konfigurierten Keys, damit sie nicht verschwinden
    keys_to_save = {kid: v for kid, v in j.items() if isinstance(v, dict) and v.get("key")}
    SQLiteStateRepository().set_value("llm_keys", keys_to_save)
    write_keys_to_desktop(j)
    
    # Trigger model verification in background
    import asyncio
    from gnom_hub.presentation.api.v1.llm_models import check_and_update_models
    asyncio.create_task(check_and_update_models())
    
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
    kdb = db.get_value("llm_keys", {})
    
    for a in agents:
        role = a.role or "normal"
        if role == "normal":
            name_lower = a.name.lower()
            if "coder" in name_lower:
                role = "coder"
            elif "writer" in name_lower:
                role = "writer"
            elif "editor" in name_lower:
                role = "editor"
            elif "researcher" in name_lower:
                role = "researcher"
            elif "security" in name_lower or "watchdog" in name_lower:
                role = "security"
            elif "soul" in name_lower:
                role = "soul"
                
        if role != a.role:
            a.role = role
            rep.save(a)
            
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        pvd, mdl = SmartRouter.get_best_specific_assignment(role, kdb)
        maps[a.name.lower()] = {"provider": pvd, "model": mdl}
        
    db.set_value("llm_agents", maps)
    return {"status": "ok"}
