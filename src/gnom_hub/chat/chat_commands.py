import subprocess
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.chat.chat_commands_handlers import handle_clear, handle_status, handle_job, _post_chat

router = APIRouter()

@router.get("/help")
def get_help():
    return FileResponse(str(Path(__file__).parent.parent / "frontend" / "help.html"))

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
    from gnom_hub.api.endpoints.workspace import get_workspace_dir
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
    
    from gnom_hub.db.legacy_db import set_agent_status, get_all_agents
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
    from gnom_hub.db.legacy_db import get_state_value, set_state_value, set_agent_status
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
        try:
            from gnom_hub.db.legacy_db import set_active_showbox, delete_showbox_presentation
            set_active_showbox("")
            delete_showbox_presentation(f"Blockade: {d['agent_name']}")
        except Exception as e:
            print(f"Error clearing blockade presentation: {e}")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **erlaubt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}

def handle_reject_decision(q):
    decision_id = q.strip()
    from gnom_hub.db.legacy_db import get_state_value, set_state_value, set_agent_status
    pending = get_state_value("pending_decisions", {})
    if decision_id in pending:
        d = pending[decision_id]
        d["status"] = "rejected"
        set_state_value("pending_decisions", pending)
        set_agent_status(d["agent_name"], "busy")
        try:
            from gnom_hub.db.legacy_db import set_active_showbox, delete_showbox_presentation
            set_active_showbox("")
            delete_showbox_presentation(f"Blockade: {d['agent_name']}")
        except Exception as e:
            print(f"Error clearing blockade presentation: {e}")
        _post_chat("System", f"Entscheidung '{decision_id}': Aktion von **{d['agent_name']}** wurde **abgelehnt**.")
        return {"status": "ok"}
    else:
        _post_chat("System", f"Fehler: Entscheidung '{decision_id}' nicht gefunden.")
        return {"status": "error", "message": "Decision not found"}

def handle_bake(q):
    parts = q.strip().split()
    if not parts or not parts[0].strip():
        _post_chat("System", "Fehler: Bitte gib einen Namen für deinen SuperGNOM an (z.B. `@bake senior_assistant`)")
        return {"status": "error", "message": "Missing name"}
    name = parts[0]
    template = parts[1] if len(parts) > 1 else "chat"
    _post_chat("System", f"🚀 Starte Kompilierung von SuperGNOM **{name}** (Template: *{template}*)...")
    try:
        from gnom_hub.core.utils.compiler import bake_supergnom
        dist_path = bake_supergnom(name, template)
        _post_chat("System", f"✅ SuperGNOM **{name}** erfolgreich kompiliert!\n\nVerzeichnis: `{dist_path}`\n\nStarte ihn im neuen Ordner per: `bash run.sh`")
        return {"status": "ok", "path": dist_path}
    except Exception as e:
        _post_chat("System", f"❌ Fehler bei der Kompilierung: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_emergency(q):
    query = q.strip()
    if not query:
        _post_chat("System", "Fehler: Bitte gib einen Suchbegriff für die Notfall-Abfrage an (z.B. `@emergency Python`).")
        return {"status": "error", "message": "Missing query"}
    _post_chat("System", f"🚨 Starte Notfall-Abfrage in der passiven Archiv-Datenbank für: **{query}**...")
    try:
        from gnom_hub.db.passive_db import emergency_search
        results = emergency_search(query, limit=5)
        if not results:
            _post_chat("System", "⚠️ Keine passenden Einträge im passiven Archiv gefunden.")
            return {"status": "ok", "results": []}
        md = f"📋 **Gefundene Archiv-Einträge ({len(results)}):**\n\n"
        for r in results:
            ts = r.get("timestamp", "").split("T")[0]
            md += f"- **[{ts}] {r.get('sender')} ({r.get('category')}):** {r.get('content')}\n"
        _post_chat("System", md)
        return {"status": "ok", "results": results}
    except Exception as e:
        _post_chat("System", f"❌ Fehler bei der Notfall-Abfrage: {str(e)}")
        return {"status": "error", "message": str(e)}
