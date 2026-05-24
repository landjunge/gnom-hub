from fastapi import APIRouter, Request; from pydantic import BaseModel; from .db import get_db, save_db; import uuid, os, threading; from datetime import datetime, timezone
router = APIRouter(prefix="/api/admin")
class ToolDef(BaseModel): name: str; description: str = ""; method: str = "GET"; path: str = ""
@router.get("/tools")
def list_tools(): return get_db("tools")
@router.post("/tools")
def register_tool(t: ToolDef): save_db("tools", [x for x in get_db("tools") if x["name"] != t.name] + [t.dict()]); return {"registered": t.name}
@router.delete("/tools/{name}")
def remove_tool(name: str): save_db("tools", [t for t in get_db("tools") if t["name"] != name]); return {"removed": name}
@router.post("/cleanup")
def cleanup_offline(): save_db("agents", [a for a in get_db("agents") if a.get("status") == "online"]); return {"status": "ok"}
@router.get("/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "memory": len(get_db("memory")), "tools": len(get_db("tools"))}
@router.post("/nuke")
def nuke_restart(request: Request):
    from agents.securityAG import _get_or_create_secret; from .proc_mgr import kill_process, restart_hub
    if request.client and request.client.host not in ("127.0.0.1", "::1", "localhost") and request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex(): return {"error": "Unauthorized"}
    killed = [kill_process(t) for t in ["generalAG", "soulAG", "watchdogAG", "securityAG", "writerAG", "editorAG", "researcherAG", "coderAG", os.environ.get("GNOM_HUB_PORT", "3002")]]
    threading.Timer(1.5, restart_hub).start(); return {"status": "nuked", "killed": killed}
ROLES = {"de": {"general": "SYSTEM-ROLLE: GENERAL. Task-Verteilung, Koordination. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen."}, "en": {"general": "SYSTEM ROLE: GENERAL. Task distribution and coordination. Analyze @job and distribute tasks via @Name -> Task. No explanations."}}
@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    from .db import get_language; lang = get_language(); roles_dict = ROLES[lang]
    if role not in ("general", "normal"): return {"error": "Invalid role"}
    agents = get_db("agents"); agent = next((a for a in agents if a["id"] == agent_id or a.get("name","").lower() == agent_id.lower()), None)
    if not agent: return {"error": "Agent not found"}
    for x in agents: x["role"] = "normal" if x.get("role") == role and role != "normal" else x.get("role", "normal")
    agent["role"] = role; save_db("agents", agents)
    mem = [m for m in get_db("memory") if not (m.get("agent_id") == agent.get("id") and m.get("type") == "role")]
    if role in roles_dict: mem.append({"id": str(uuid.uuid4()), "agent_id": agent.get("id"), "content": f"[SYSTEM] {roles_dict[role]}", "type": "role", "timestamp": datetime.now(timezone.utc).isoformat()+"Z"})
    save_db("memory", mem); from .role_prompt import implant; file_path = implant(agent["name"], roles_dict[role]) if role in roles_dict else None
    return {"agent": agent["name"], "role": role, "file": file_path}
@router.get("/language")
def get_sys_language(): from .db import get_language; return {"language": get_language()}
@router.post("/language")
async def set_sys_language(req: Request): from .db import set_language; j = await req.json(); set_language(j.get("language", "en")); return {"status": "ok"}
@router.get("/autodeploy")
def get_auto(): from .ftp_deploy import get_deploy; return {"auto_deploy": get_deploy()}
@router.post("/autodeploy")
async def set_auto(req: Request): from .ftp_deploy import set_deploy; j = await req.json(); set_deploy(j.get("auto_deploy", False)); return {"status": "ok"}