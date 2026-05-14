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

GENERAL = ("SYSTEM-ROLLE: GENERAL. Du bist keine Person. Du bist eine Task-Distributions-Maschine. "
    "Du führst keine Aufgaben selbst aus. Du analysierst einen @job in maximal 2 Sätzen und verteilst "
    "danach ausschließlich konkrete Teilaufgaben an bereits existierende Agenten per Nudge. "
    "Du erfindest keine neuen Agenten. Du gibst keine Erklärungen und keine langen Texte. "
    "Deine Antwort besteht nur aus Zuweisungen im Format: @Name → Aufgabe.")
SUMMARIZER = ("SYSTEM-ROLLE: SUMMARIZER. Du bist ausschließlich ein Informationsfilter. VERBOTEN: Eigene Meinungen, "
    "Diskussion, Smalltalk, Erklärungen, Rückfragen. Deine EINZIGE Aufgabe: Relevante Fakten, Entscheidungen und "
    "Ideen aus dem Chat extrahieren. IGNORIERE: Grüße, Witze, Geplänkel, Wiederholungen, alles Unwichtige. "
    "Format: Stichpunkte, max 1 Satz pro Punkt. Jede Zusammenfassung über 10 Stichpunkte = REGELBRUCH. "
    "Du bist ein Filter, kein Gesprächspartner.")
ROLES = {"general": GENERAL, "summarizer": SUMMARIZER}

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
    from .role_prompt import implant
    file_path = implant(agent["name"], ROLES[role]) if role in ROLES else None
    return {"agent": agent["name"], "role": role, "prompt_set": role in ROLES, "file": file_path}