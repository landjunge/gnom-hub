import time, threading, requests; from .db import get_all_agents, pulse_agent_alive
def _alive(port):
    try: requests.get(f"http://127.0.0.1:{port}/", timeout=1); return True
    except Exception: return False
def pulse_janitor():
    """Prüft Agenten-Status. Port lebt → auto-online. Kein Agent wird offline gesetzt."""
    for a in get_all_agents():
        p = a.get("port", 0)
        if p and _alive(p): pulse_agent_alive(a["name"])
def start_pulse(interval=30):
    def loop():
        while True:
            try: pulse_janitor()
            except Exception as e: print(f"[PULSE] Fehler: {e}")
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start(); return t
