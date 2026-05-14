"""Admin-Routes — Dynamic Tool Registration, Rollen, System-Verwaltung."""
from fastapi import APIRouter
from pydantic import BaseModel
from .db import get_db, save_db
import uuid
from datetime import datetime
router = APIRouter(prefix="/api/admin")

class ToolDef(BaseModel):
    name: str; description: str = ""; method: str = "GET"; path: str = ""

@router.get("/tools")
def list_tools(): return get_db("tools")
@router.post("/tools")
def register_tool(t: ToolDef):
    tools = [x for x in get_db("tools") if x["name"] != t.name] + [t.dict()]
    save_db("tools", tools); return {"registered": t.name, "total": len(tools)}
@router.delete("/tools/{name}")
def remove_tool(name: str): save_db("tools", [t for t in get_db("tools") if t["name"] != name]); return {"removed": name}
@router.post("/cleanup")
def cleanup_offline():
    agents = get_db("agents"); online = [a for a in agents if a.get("status") == "online"]
    save_db("agents", online); return {"removed": len(agents) - len(online), "remaining": len(online)}
@router.get("/health")
def health(): return {"status": "ok", "agents": len(get_db("agents")), "memory": len(get_db("memory")), "tools": len(get_db("tools"))}

GENERAL = ("Du bist der General. Deine einzige Aufgabe: Jobs verteilen. Kein Diskutieren, kein Brainstormen. "
    "Bei @job: 1. Aufgabe in 2 Sätzen analysieren. 2. Max 3 Teilaufgaben. 3. Per Nudge an existierende Agenten. "
    "4. Kurzer Satz wer was bekam. Nur existierende Agenten, keine neuen erfinden.")
ROLES = {"general": GENERAL, "summarizer": "Du bist der Summarizer. Fasse Diskussionen zusammen. Sammle @idea-Einträge separat."}

@router.put("/agents/{agent_id}/role")
def set_role(agent_id: str, role: str):
    if role not in ("general", "summarizer", "normal"): return {"error": f"Ungültige Rolle: {role}"}
    agents = get_db("agents")
    agent = next((a for a in agents if a["id"] == agent_id), None)
    if not agent: return {"error": "Agent nicht gefunden"}
    for x in agents:
        if x.get("role") == role and role != "normal": x["role"] = "normal"
    agent["role"] = role; save_db("agents", agents)
    mem = [m for m in get_db("memory") if not (m.get("agent_id") == agent_id and m.get("type") == "role")]
    if role in ROLES:
        mem.append({"id": str(uuid.uuid4()), "agent_id": agent_id, "content": f"[SYSTEM-ROLLE] {ROLES[role]}", "type": "role", "timestamp": datetime.utcnow().isoformat()+"Z"})
    save_db("memory", mem)
    return {"agent": agent["name"], "role": role, "prompt_set": role in ROLES}