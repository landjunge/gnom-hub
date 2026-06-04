import logging
import time, threading
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.process.process_manager import AGENTS, _get_proc

def pulse_janitor():
    repo = SQLiteAgentRepository()
    from datetime import datetime, timezone
    import json
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    for agent in repo.list_all():
        if agent.status == "busy" and agent.last_seen:
            last_seen = agent.last_seen
            if last_seen.tzinfo is not None:
                diff = (now_utc - last_seen).total_seconds()
            else:
                diff = (now_local - last_seen).total_seconds()
            if diff > 300:
                agent.status = "online"
                agent.active_job = None
                repo.save(agent)
                try:
                    from gnom_hub.db import add_chat_message, get_active_project
                    add_chat_message(get_active_project(), "System", "war-room", "chat",
                                     f"⚠️ [System] Agent **{agent.name}** wurde nach 5 Minuten Inaktivität automatisch freigegeben (@free).",
                                     {"type": "chat"})
                except Exception as e: logging.getLogger(__name__).error('Fehler in Agenten-Freigabe-Benachrichtigung: %s', e)
    for name in AGENTS:
        proc = _get_proc(name)
        status = "running" if proc else "stopped"
        agent = repo.get_by_name(name)
        if agent:
            if agent.status != status or (proc and agent.pid != proc.pid):
                agent.status = status
                agent.pid = proc.pid if proc else None
                repo.save(agent)

def start_pulse(interval=30):
    def loop():
        while True:
            try: pulse_janitor()
            except Exception as e: print(f"[PULSE] Fehler: {e}")
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
