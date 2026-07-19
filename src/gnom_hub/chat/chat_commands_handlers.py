# chat_commands_handlers.py — Handlers for clear, status, and job command
import re
import uuid
from datetime import datetime, timezone

from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.state_repo import SQLiteStateRepository


def _post_chat(s, c):
    from gnom_hub.db import add_chat_message, get_active_project
    add_chat_message(get_active_project(), s, "war-room", "role_response", c)

def handle_clear(q=""):
    from gnom_hub.chat.chat_clear import handle_clear as _hc
    return _hc(q)

def handle_status():
    agents = [
        {"name": a.name, "role": a.role, "st": a.status}
        for a in SQLiteAgentRepository().get_all()
    ]
    # status field so frontend toast branch matches (was dead code without it)
    return {"status": "agents", "agents": agents}

def handle_job(task):
    from gnom_hub.agents.role_tools import distribute_job
    from gnom_hub.chat.brainstorm.brainstorm import dispatch
    agent_repo, state_repo = SQLiteAgentRepository(), SQLiteStateRepository()
    ags = agent_repo.get_all()
    gen = next((a for a in ags if a.role == "general" or a.name.lower() == "generalag"), None)
    if not gen:
        return {"status": "error", "error": "Kein General", "message": "Kein General"}
    job_id = str(uuid.uuid4())
    jobs = state_repo.get_value("jobs", []) + [{"id": job_id, "task": task, "general": gen.name, "status": "open", "ts": datetime.now(timezone.utc).isoformat()+"Z"}]
    state_repo.set_value("jobs", jobs); res = distribute_job(task); _post_chat(gen.name, res)
    workers = []
    for a in ags:
        if a.name.lower() in {"soulag", "generalag", "securityag", "watchdogag"}:
            continue
        aj = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s→>:\-]+(.+)', res) if m.group(1).lower() == a.name.lower()), "")
        agent_repo.update_active_job(a.name, aj)
        if aj:
            import time; time.sleep(1.5); workers.append(a.name); dispatch(aj, target=a.name, context_id=job_id)
    from gnom_hub.agents.swarm.swarm_coordinator import start_coordinator
    start_coordinator(task, workers, job_id=job_id)
    return {
        "status": "job_created",
        "general": gen.name,
        "task": (task or "")[:120],
        "job_id": job_id,
        "workers": workers,
    }
