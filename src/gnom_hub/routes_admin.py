from fastapi import APIRouter, Request; from pydantic import BaseModel; import uuid, os, threading; from datetime import datetime, timezone
router = APIRouter(prefix="/api/admin")
class ToolDef(BaseModel): name: str; description: str = ""; method: str = "GET"; path: str = ""
@router.get("/tools")
def list_tools(): from .db import get_state_value; return get_state_value("tools", [])
@router.post("/tools")
def register_tool(t: ToolDef):
    from .db import get_state_value, set_state_value; set_state_value("tools", [x for x in get_state_value("tools", []) if x["name"] != t.name] + [t.dict()]); return {"registered": t.name}
@router.delete("/tools/{name}")
def remove_tool(name: str):
    from .db import get_state_value, set_state_value; set_state_value("tools", [t for t in get_state_value("tools", []) if t["name"] != name]); return {"removed": name}
@router.post("/cleanup")
def cleanup_offline(): from .db import delete_offline_agents; delete_offline_agents(); return {"status": "ok"}
@router.get("/health")
def health():
    from .db import get_all_agents, get_chat_count, get_state_value
    return {"status": "ok", "agents": len(get_all_agents()), "memory": get_chat_count(), "tools": len(get_state_value("tools", []))}
@router.post("/nuke")
def nuke_restart(request: Request):
    from agents.securityAG import _get_or_create_secret; from .proc_mgr import _kill_process, restart_hub
    if request.client and request.client.host not in ("127.0.0.1", "::1", "localhost") and request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex(): return {"error": "Unauthorized"}
    killed = [_kill_process(t) for t in ["generalAG", "soulAG", "watchdogAG", "securityAG", "writerAG", "editorAG", "researcherAG", "coderAG", os.environ.get("GNOM_HUB_PORT", "3002")]]
    threading.Timer(1.5, restart_hub).start(); return {"status": "nuked", "killed": killed}
ROLES = {"de": {"general": "SYSTEM-ROLLE: GENERAL. Task-Verteilung, Koordination. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen."}, "en": {"general": "SYSTEM ROLE: GENERAL. Task distribution and coordination. Analyze @job and distribute tasks via @Name -> Task. No explanations."}}
@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    from .db import get_language, set_agent_role, update_agent_role_memory; lang = get_language(); roles_dict = ROLES[lang]
    if role not in ("general", "normal"): return {"error": "Invalid role"}
    agent = set_agent_role(agent_id, role)
    if not agent: return {"error": "Agent not found"}
    role_content = roles_dict[role] if role in roles_dict else None
    update_agent_role_memory(agent["id"], role_content)
    from .role_prompt import implant; file_path = implant(agent["name"], role_content) if role_content else None
    return {"agent": agent["name"], "role": role, "file": file_path}
@router.get("/language")
def get_sys_language(): from .db import get_language; return {"language": get_language()}
@router.post("/language")
async def set_sys_language(req: Request): from .db import set_language; j = await req.json(); set_language(j.get("language", "en")); return {"status": "ok"}