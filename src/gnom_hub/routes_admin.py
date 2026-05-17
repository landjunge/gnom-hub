from fastapi import APIRouter; from pydantic import BaseModel; from .db import get_db, save_db; import uuid; from datetime import datetime
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
def nuke_restart():
    from .proc_mgr import kill_process, restart_hub
    killed = []
    for target in ["gnom_hub", "generalAG", "summarizerAG", "cronjobAG", "backupAG", "soulAG", "watchdogAG", "skillsAG", "securityAG"]:
        r = kill_process(target); killed.append(r)
    import threading; threading.Timer(1.5, restart_hub).start()
    return {"status": "nuked", "killed": killed, "restart": "in 1.5s"}
ROLES = {"general": "SYSTEM-ROLLE: GENERAL. Task-Distributions-Maschine. Analysiere @job und verteile Aufgaben via @Name -> Aufgabe. Keine Erklärungen.",
         "summarizer": "SYSTEM-ROLLE: SUMMARIZER. Informationsfilter. Extrahiere Fakten/Entscheidungen. Stichpunkte, max 1 Satz pro Punkt."}
@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    if role not in ("general", "summarizer", "normal"): return {"error": f"Ungültige Rolle: {role}"}
    agents = get_db("agents"); agent = next((a for a in agents if a["id"] == agent_id or a.get("name","").lower() == agent_id.lower()), None)
    if not agent: return {"error": "Agent nicht gefunden"}
    for x in agents:
        if x.get("role") == role and role != "normal": x["role"] = "normal"
    agent["role"] = role; save_db("agents", agents)
    mem = [m for m in get_db("memory") if not (m.get("agent_id") == agent.get("id") and m.get("type") == "role")]
    if role in ROLES: mem.append({"id": str(uuid.uuid4()), "agent_id": agent.get("id"), "content": f"[SYSTEM] {ROLES[role]}", "type": "role", "timestamp": datetime.utcnow().isoformat()+"Z"})
    save_db("memory", mem); file_path = None
    if role in ROLES:
        from .role_prompt import implant; file_path = implant(agent["name"], ROLES[role])
    return {"agent": agent["name"], "role": role, "prompt_set": role in ROLES, "file": file_path}