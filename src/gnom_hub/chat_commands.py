import uuid, re, subprocess; from datetime import datetime; from fastapi import APIRouter
router = APIRouter()
def _post_chat(s, c):
    from .db import add_chat_message, get_active_project
    add_chat_message(get_active_project(), s, "war-room", "role_response", c, {"type": "role_response", "sender": s})
def handle_clear(q=""): from .chat_clear import handle_clear as _hc; return _hc(q)
def handle_status():
    from .db import get_all_agents
    return {"agents": [{"name":a["name"],"role":a.get("role","—"),"st":a.get("skill",a.get("status"))} for a in get_all_agents()]}
def handle_free(q):
    from .db import clear_agent_jobs; t=q.replace("@","").strip().lower(); clear_agent_jobs(t or None)
    _post_chat("System", f"Jobs cleared: {t or 'ALL'}"); return {"status": "ok"}
def handle_job(task):
    from .role_tools import distribute_job; from .brainstorm import dispatch; from .db import get_all_agents, get_state_value, set_state_value, update_agent_active_job
    ags = get_all_agents(); gen = next((a for a in ags if a.get("role") == "general" or a.get("name","").lower() == "generalag"), None)
    if not gen: return {"error": "Kein General"}
    jobs = get_state_value("jobs", []) + [{"id": str(uuid.uuid4()), "task": task, "general": gen["name"], "status": "open", "ts": datetime.utcnow().isoformat()+"Z"}]
    set_state_value("jobs", jobs)
    res = distribute_job(task); _post_chat(gen["name"], res)
    for a in ags:
        aj = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s→>:\-]+(.+)', res) if m.group(1).lower()==a["name"].lower()), "")
        update_agent_active_job(a["name"], aj)
        if aj: dispatch(aj, target=a["name"])
    return {"status": "job_created"}
def handle_git(q, rb=False):
    p = q.split(" ", 1); cmd = f"reset --hard {p[1]}" if rb else (p[1] if len(p)>1 else ""); from pathlib import Path
    if not (Path(".") / ".git").exists(): subprocess.run(["git", "init"], capture_output=True)
    try: r = subprocess.run(["git"] + cmd.split(), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e: r = f"Error: {e}"
    _post_chat("System", f"Git: {r[:300]}"); return {"status": "ok"}
@router.get("/api/ideas")
def get_ideas(): from .db import get_state_value; return get_state_value("ideas", [])
@router.get("/api/jobs")
def get_jobs(): from .db import get_state_value; return sorted(get_state_value("jobs", []), key=lambda j: j.get("ts",""), reverse=True)[:20]
