import logging
import time, threading, os
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.process.process_manager import AGENTS, _get_proc
from gnom_hub.core.config import DB_PATH

BUSY_TIMEOUT = 15 if os.environ.get("TESTING") == "true" else 120  # (war 60)
STUCK_RECOVERY_INTERVAL = 300  # recover_stuck_messages alle 5 Minuten
_last_stuck_recovery = 0


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
            if diff > BUSY_TIMEOUT:
                agent.status = "online"
                agent.active_job = None
                repo.save(agent)
                try:
                    from gnom_hub.db import add_chat_message, get_active_project
                    add_chat_message(get_active_project(), "System", "war-room", "chat",
                                     f"⚠️ [System] Agent **{agent.name}** wurde nach 2 Minuten Inaktivität automatisch freigegeben (@free).",
                                     {"type": "chat"})
                except Exception as e:
                    logging.getLogger(__name__).error('Fehler in Agenten-Freigabe-Benachrichtigung: %s', e)
    for name in AGENTS:
        proc = _get_proc(name)
        agent = repo.get_by_name(name)
        if agent and agent.pid != (proc.pid if proc else None):
            agent.pid = proc.pid if proc else None
            repo.save(agent)

    global _last_stuck_recovery
    now = time.time()
    if now - _last_stuck_recovery > STUCK_RECOVERY_INTERVAL:
        _last_stuck_recovery = now
        try:
            from gnom_hub.agents.swarm.swarm_comms import recover_stuck_messages
            recover_stuck_messages(str(DB_PATH))
        except Exception as e:
            logging.getLogger(__name__).error("Stuck message recovery failed: %s", e)

def start_pulse(interval=30):
    def loop():
        while True:
            try: pulse_janitor()
            except Exception as e: logging.getLogger(__name__).error("Pulse janitor failed: %s", e)
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
