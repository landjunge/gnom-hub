import time, threading, requests
from datetime import datetime, timedelta
from .db import get_db, save_db

TIMEOUT = 120

def _alive(port):
    try: requests.get(f"http://127.0.0.1:{port}/", timeout=1); return True
    except: return False

def pulse_janitor():
    """Prüft Agenten-Status. Port lebt → auto-online. Kein Agent wird offline gesetzt."""
    agents, now, changed = get_db("agents"), datetime.utcnow(), False
    for a in agents:
        port = a.get("port", 0)
        if not port: continue
        if _alive(port):
            if a.get("status") != "online": a["status"] = "online"; changed = True
            a["last_seen"] = now.isoformat() + "Z"; changed = True
    if changed: save_db("agents", agents)

def start_pulse(interval=30):
    def loop():
        while True:
            try: pulse_janitor()
            except: pass
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start(); return t
