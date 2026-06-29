from fastapi import APIRouter, Request, Depends
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, verify_key
from gnom_hub.infrastructure.llm.desktop_syncer import sync_desktop_keys, write_keys_to_desktop
from gnom_hub.api.endpoints.auth import verify_admin

router = APIRouter()

@router.get("/api/llm/keys")
async def get_keys():
    d = SQLiteStateRepository().get_value("llm_keys", {})
    return await sync_desktop_keys(d if isinstance(d, dict) else {})

@router.post("/api/llm/keys")
async def save_keys(req: Request, _=Depends(verify_admin)):
    j = await req.json()
    # Speichere alle konfigurierten Keys, damit sie nicht verschwinden
    keys_to_save = {kid: v for kid, v in j.items() if isinstance(v, dict) and v.get("key")}
    # MERGE mit existierenden Keys — vorher wurde alles überschrieben, was dazu
    # führte dass Inline-Keys (von Service-Cards / flushLlmPageChanges) ALLE
    # anderen Provider-Keys aus der DB gelöscht haben. Jetzt: neue/aktualisierte
    # Keys überschreiben existierende; Keys die nicht im Request sind bleiben.
    db = SQLiteStateRepository()
    existing = db.get_value("llm_keys", {}) or {}
    if not isinstance(existing, dict):
        existing = {}
    for kid, v in keys_to_save.items():
        if isinstance(v, dict) and v.get("key"):
            existing[kid] = v
    db.set_value("llm_keys", existing)
    write_keys_to_desktop(j)
    
    # Trigger model verification in background
    import asyncio
    from gnom_hub.api.endpoints.llm_models import check_and_update_models
    asyncio.create_task(check_and_update_models())
    
    return {"status": "ok"}

@router.post("/api/llm/keys/reverify")
async def reverify_keys():
    """Manueller Trigger für Key-Re-Verify.

    Hintergrund: Keys die in api_keys.txt als `# UNGÜLTIG:` markiert sind,
    werden beim normalen Sync ignoriert. Dieser Endpoint zwingt einen
    Re-Check aller ungültigen Keys — z.B. wenn der User weiß dass ein
    Billing-Limit abgelaufen ist und der Key wieder gehen sollte.

    Returns: {checked, recovered, still_invalid}
    """
    from gnom_hub.infrastructure.llm.desktop_syncer import reverify_invalid_keys
    return await reverify_invalid_keys(force=True)


@router.post("/api/llm/test")
async def test_key(req: Request):
    j = await req.json()
    k, p, l = j.get("key"), j.get("provider"), j.get("label", "")
    if p: return await verify_key(p, k)
    return await auto_detect_and_verify(k, l)

@router.post("/api/llm/auto_assign")
async def auto_assign(force_provider: str = None):
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
        pvd, mdl = SmartRouter.get_best_specific_assignment(role, kdb, force_provider)
        maps[a.name.lower()] = {"provider": pvd, "model": mdl}
        
    db.set_value("llm_agents", maps)
    preset = db.get_value("active_preset", "Web Development")
    if isinstance(preset, str):
        preset = preset.strip('"\'')
    db.set_value(f"llm_preset_{preset}", maps)
    return {"status": "ok"}
