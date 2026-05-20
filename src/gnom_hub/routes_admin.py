from fastapi import APIRouter, Request; from pydantic import BaseModel; from .db import get_db, save_db; import uuid; from datetime import datetime
router = APIRouter(prefix="/api/admin")
class ToolDef(BaseModel): name: str; description: str = ""; method: str = "GET"; path: str = ""
@router.get("/tools")
def list_tools(): return get_db("tools")
@router.post("/tools")
def register_tool(t: ToolDef): tools = [x for x in get_db("tools") if x["name"] != t.name] + [t.dict()]; save_db("tools", tools); return {"registered": t.name, "total": len(tools)}
@router.delete("/tools/{name}")
def remove_tool(name: str): save_db("tools", [t for t in get_db("tools") if t["name"] != name]); return {"removed": name}
@router.post("/cleanup")
def cleanup_offline(): online = [a for a in get_db("agents") if a.get("status") == "online"]; save_db("agents", online); return {"remaining": len(online)}
@router.get("/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "memory": len(get_db("memory")), "tools": len(get_db("tools"))}
@router.post("/nuke")
def nuke_restart(request: Request):
    import os, threading
    from .securityAG import _get_or_create_secret; from .proc_mgr import kill_process, restart_hub
    if request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex(): return {"error": "Unauthorized"}
    port = os.environ.get("GNOM_HUB_PORT", "3002")
    killed = [kill_process(t) for t in ["generalAG", "summarizerAG", "cronjobAG", "backupAG", "soulAG", "watchdogAG", "skillsAG", "securityAG", port]]
    threading.Timer(1.5, restart_hub).start()
    return {"status": "nuked", "killed": killed, "restart": "in 1.5s"}
ROLES_DE = {"general": "SYSTEM-ROLLE: GENERAL. Task-Verteilung, Koordination. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen.",
            "summarizer": "SYSTEM-ROLLE: SUMMARIZER. Informationsfilter. Extrahiere Fakten/Entscheidungen. Stichpunkte, max 1 Satz pro Punkt."}
ROLES_EN = {"general": "SYSTEM ROLE: GENERAL. Task distribution and coordination. Analyze @job and distribute tasks via @Name -> Task. No explanations.",
            "summarizer": "SYSTEM ROLE: SUMMARIZER. Information filter. Extract facts/decisions. Bullet points, max 1 sentence per point."}
@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    from .db import get_language
    lang = get_language()
    roles_dict = ROLES_EN if lang == "en" else ROLES_DE
    if role not in ("general", "summarizer", "normal"): return {"error": f"Ungültige Rolle: {role}" if lang == "de" else f"Invalid role: {role}"}
    agents = get_db("agents"); agent = next((a for a in agents if a["id"] == agent_id or a.get("name","").lower() == agent_id.lower()), None)
    if not agent: return {"error": "Agent nicht gefunden" if lang == "de" else "Agent not found"}
    for x in agents:
        if x.get("role") == role and role != "normal": x["role"] = "normal"
    agent["role"] = role; save_db("agents", agents)
    mem = [m for m in get_db("memory") if not (m.get("agent_id") == agent.get("id") and m.get("type") == "role")]
    if role in roles_dict: mem.append({"id": str(uuid.uuid4()), "agent_id": agent.get("id"), "content": f"[SYSTEM] {roles_dict[role]}", "type": "role", "timestamp": datetime.utcnow().isoformat()+"Z"})
    save_db("memory", mem); file_path = None
    if role in roles_dict:
        from .role_prompt import implant; file_path = implant(agent["name"], roles_dict[role])
    return {"agent": agent["name"], "role": role, "prompt_set": role in roles_dict, "file": file_path}

@router.get("/language")
def get_sys_language():
    from .db import get_language
    return {"language": get_language()}

@router.post("/language")
async def set_sys_language(request: Request):
    from .db import set_language
    j = await request.json()
    lang = j.get("language", "de")
    set_language(lang)
    return {"status": "ok", "language": lang}