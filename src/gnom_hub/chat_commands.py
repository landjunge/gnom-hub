import subprocess
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from .chat_commands_handlers import handle_clear, handle_status, handle_job, _post_chat

router = APIRouter()

@router.get("/help")
def get_help():
    return FileResponse(str(Path(__file__).parent.parent.parent / "frontend" / "help.html"))

@router.get("/api/ideas")
def get_ideas(): return SQLiteStateRepository().get_value("ideas", [])

@router.get("/api/jobs")
def get_jobs():
    return sorted(SQLiteStateRepository().get_value("jobs", []), key=lambda j: j.get("ts",""), reverse=True)[:20]

def handle_free(q):
    t = q.replace("@","").strip().lower()
    SQLiteAgentRepository().clear_jobs(t or None)
    _post_chat("System", f"Jobs cleared: {t or 'ALL'}")
    return {"status": "ok"}

def handle_git(q, rb=False):
    from gnom_hub.presentation.api.v1.workspace import get_workspace_dir
    wd = get_workspace_dir()
    p = q.split(" ", 1)
    cmd = f"reset --hard {p[1]}" if rb else (p[1] if len(p) > 1 else "status")
    from pathlib import Path
    if not (Path(wd) / ".git").exists(): 
        subprocess.run(["git", "init"], cwd=wd, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Gnom-Hub Agents"], cwd=wd, capture_output=True)
        subprocess.run(["git", "config", "user.email", "agents@gnom-hub.local"], cwd=wd, capture_output=True)
    try: 
        r = subprocess.run(["git"] + cmd.split(), cwd=wd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e: 
        r = f"Error: {e}"
    _post_chat("System", f"Git: {r[:300]}"); return {"status": "ok"}

def handle_resume(q):
    agent_name = q.strip().replace("@", "")
    if not agent_name:
        _post_chat("System", "Fehler: Bitte gib einen Agenten-Namen an (z.B. @@resume CoderAG)")
        return {"status": "error", "message": "Missing agent name"}
    
    from .db import set_agent_status, get_all_agents
    agents = get_all_agents()
    agent = next((a for a in agents if a["name"].lower() == agent_name.lower()), None)
    if not agent:
        _post_chat("System", f"Fehler: Agent '{agent_name}' nicht gefunden.")
        return {"status": "error", "message": "Agent not found"}
        
    set_agent_status(agent["name"], "busy")
    _post_chat("System", f"Agent **{agent['name']}** wurde fortgesetzt.")
    return {"status": "ok"}

def handle_approve_decision(q):
    decision_id = q.strip()
    from .db import get_state_value, set_state_value, set_agent_status
    pending = get_state_value("pending_decisions", {})
    if decision_id in pending:
        d = pending[decision_id]
        d["status"] = "approved"
        set_state_value("pending_decisions", pending)
        if d["action_type"] == "WRITE":
            writes = get_state_value("approved_security_writes", [])
            writes.append(d["detail"])
            set_state_value("approved_security_writes", writes)
        elif d["action_type"] == "SHELL":
            cmds = get_state_value("approved_security_commands", [])
            cmds.append(d["detail"])
            set_state_value("approved_security_commands", cmds)
        set_agent_status(d["agent_name"], "busy")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **erlaubt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}

def handle_reject_decision(q):
    decision_id = q.strip()
    from .db import get_state_value, set_state_value, set_agent_status
    pending = get_state_value("pending_decisions", {})
    if decision_id in pending:
        d = pending[decision_id]
        d["status"] = "rejected"
        set_state_value("pending_decisions", pending)
        set_agent_status(d["agent_name"], "busy")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **abgelehnt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}
