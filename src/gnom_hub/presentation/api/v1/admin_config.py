from fastapi import APIRouter, Request
from pydantic import BaseModel
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository as SR
from gnom_hub.infrastructure.database.agent_role import set_agent_role, update_agent_role_memory

router = APIRouter(prefix="/api/admin")
ROLES = {
    "de": {"general": "SYSTEM-ROLLE: GENERAL. Task-Verteilung, Koordination. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen."}, "en": {"general": "SYSTEM ROLE: GENERAL. Task distribution and coordination. Analyze @job and distribute tasks via @Name -> Task. No explanations."}}

@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    if role not in ("general", "normal"): return {"error": "Invalid role"}
    a = set_agent_role(agent_id, role)
    if not a: return {"error": "Agent not found"}
    c = ROLES[SR().get_language()].get(role)
    update_agent_role_memory(a["id"], c)
    from gnom_hub.agents.role_prompt import implant
    return {"agent": a["name"], "role": role, "file": implant(a["name"], c) if c else None}

@router.get("/language")
def get_sys_language(): return {"language": SR().get_language()}

@router.post("/language")
async def set_sys_language(req: Request):
    SR().set_language((await req.json()).get("language", "en"))
    return {"status": "ok"}

class PresetPayload(BaseModel): preset: str

@router.get("/preset")
def get_preset(): return {"preset": (SR().get_value("active_preset", "Web Development") or "").strip('"\'')}

@router.post("/preset")
def set_preset(p: PresetPayload):
    from gnom_hub.preset_service import handle_preset_change
    handle_preset_change(p.preset)
    return {"status": "ok", "preset": p.preset}
