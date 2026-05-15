"""Chat-Spezial-Befehle + Ideas-API + Job-System."""
import uuid
from datetime import datetime
from fastapi import APIRouter
from .db import get_db, save_db
router = APIRouter()
def _uid(): return str(uuid.uuid4())
def _ts(): return datetime.utcnow().isoformat()+"Z"
def _post_chat(sender, content):
    save_db("memory", get_db("memory") + [{"id": _uid(), "agent_id": "war-room",
        "content": content, "metadata": {"type": "role_response", "sender": sender}, "timestamp": _ts()}])
def handle_idea(text):
    save_db("ideas", get_db("ideas") + [{"id": _uid(), "content": text, "ts": _ts()}])
    return {"status": "idea_saved", "content": text}
def handle_clear():
    save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != "war-room"])
    return {"status": "cleared"}
def handle_status():
    return {"agents": [{"name":a["name"],"role":a.get("role","—"),"st":a["status"]} for a in get_db("agents")]}
def handle_job(task):
    from .role_tools import distribute_job
    general = next((a for a in get_db("agents") if a.get("role") == "general"), None)
    if not general: return {"error": "Kein General — erst @general @Name zuweisen"}
    save_db("jobs", get_db("jobs") + [{"id": _uid(), "task": task, "general": general["name"], "status": "open", "ts": _ts()}])
    result = distribute_job(task); _post_chat(general["name"], result)
    return {"status": "job_created", "general": general["name"], "result": result}
def handle_summary(q=""):
    from .role_tools import summarize_chat
    result = summarize_chat(); _post_chat("Summarizer", result)
    return {"status": "summarized", "result": result}
@router.get("/api/ideas")
def get_ideas(): return get_db("ideas")
@router.get("/api/jobs")
def get_jobs(): return sorted(get_db("jobs"), key=lambda j: j.get("ts",""), reverse=True)[:20]
@router.put("/api/agents/{agent_id}/group")
def set_group(agent_id: str, group: str = ""):
    agents = get_db("agents"); a = next((x for x in agents if x["id"] == agent_id), None)
    if not a: return {"error": "Agent nicht gefunden"}
    a["group"] = group; save_db("agents", agents); return {"agent": a["name"], "group": group}
