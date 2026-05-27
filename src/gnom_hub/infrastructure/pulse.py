import time, threading
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.process.psutil_mgr import AGENTS, _get_proc

def pulse_janitor():
    repo = SQLiteAgentRepository()
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
