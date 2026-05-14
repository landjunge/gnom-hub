"""Chat-Spezial-Befehle + Ideas-API + Job-System."""
import uuid
from datetime import datetime
from fastapi import APIRouter
from .db import get_db, save_db
from .brainstorm import dispatch
router = APIRouter()

def handle_idea(text):
    save_db("ideas", get_db("ideas") + [{"id": str(uuid.uuid4()), "content": text, "ts": datetime.utcnow().isoformat()+"Z"}])
    return {"status": "idea_saved", "content": text}

def handle_clear():
    save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != "war-room"])
    return {"status": "cleared"}

def handle_status():
    return {"status": "agents", "agents": [{"name":a["name"],"role":a.get("role","—"),"st":a["status"]} for a in get_db("agents")]}

def handle_job(task):
    agents = get_db("agents")
    general = next((a for a in agents if a.get("role") == "general" and a.get("status") == "online"), None)
    if not general: return {"status": "error", "msg": "Kein General online — erst @general @Name zuweisen"}
    job = {"id": str(uuid.uuid4()), "task": task, "general": general["name"],
        "status": "open", "assigned_to": None, "ts": datetime.utcnow().isoformat()+"Z"}
    save_db("jobs", get_db("jobs") + [job])
    prompt = (f"[JOB] Neue Aufgabe: {task}\n"
        f"Online-Agenten: {', '.join(a['name'] for a in agents if a.get('status')=='online' and a['name']!=general['name'])}\n"
        f"Vergib diese Aufgabe an den passendsten Agenten. Wenn keiner passt, sage 'NEED_AGENT: <vorgeschlagene Beschreibung>'.")
    asked = dispatch(prompt, target=general["name"])
    return {"status": "job_created", "job_id": job["id"], "general": general["name"], "task": task, "asked": asked}
@router.get("/api/ideas")
def get_ideas(): return get_db("ideas")
@router.get("/api/jobs")
def get_jobs(): return sorted(get_db("jobs"), key=lambda j: j.get("ts",""), reverse=True)[:20]
@router.put("/api/agents/{agent_id}/group")
def set_group(agent_id: str, group: str = ""):
    agents = get_db("agents"); a = next((x for x in agents if x["id"] == agent_id), None)
    if not a: return {"error": "Agent nicht gefunden"}
    a["group"] = group; save_db("agents", agents); return {"agent": a["name"], "group": group}
