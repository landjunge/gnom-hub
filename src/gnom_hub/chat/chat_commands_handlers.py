# chat_commands_handlers.py — Handlers for clear, status, and job command
import uuid, re
from datetime import datetime
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository
from gnom_hub.chat.entities import ChatMessage

def _post_chat(s, c):
    from gnom_hub.db.legacy_db import add_chat_message, get_active_project
    add_chat_message(get_active_project(), s, "war-room", "role_response", c)

def handle_clear(q=""):
    from gnom_hub.chat.chat_clear import handle_clear as _hc
    return _hc(q)

def handle_status():
    return {"agents": [{"name": a.name, "role": a.role, "st": a.status} for a in SQLiteAgentRepository().get_all()]}

def handle_job(task):
    from gnom_hub.agents.role_tools import distribute_job; from gnom_hub.chat.brainstorm.brainstorm import dispatch
    agent_repo, state_repo = SQLiteAgentRepository(), SQLiteStateRepository()
    ags = agent_repo.get_all()
    gen = next((a for a in ags if a.role == "general" or a.name.lower() == "generalag"), None)
    if not gen: return {"error": "Kein General"}
    jobs = state_repo.get_value("jobs", []) + [{"id": str(uuid.uuid4()), "task": task, "general": gen.name, "status": "open", "ts": datetime.utcnow().isoformat()+"Z"}]
    state_repo.set_value("jobs", jobs); res = distribute_job(task); _post_chat(gen.name, res)
    workers = []
    for a in ags:
        if a.name.lower() in {"soulag", "generalag", "securityag", "watchdogag"}:
            continue
        aj = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s→>:\-]+(.+)', res) if m.group(1).lower() == a.name.lower()), "")
        agent_repo.update_active_job(a.name, aj)
        if aj:
            import time; time.sleep(1.5); workers.append(a.name); dispatch(aj, target=a.name)
    from gnom_hub.agents.swarm.swarm_coordinator import start_coordinator
    start_coordinator(task, workers)
    return {"status": "job_created"}
