import time, threading
from datetime import datetime, timedelta
from .db import get_db, save_db

TIMEOUT = 120  # Sekunden ohne Heartbeat → offline

def pulse_janitor():
    """Setzt Agenten auf offline wenn Heartbeat > 120s alt."""
    agents = get_db("agents")
    now = datetime.utcnow()
    changed = False
    for a in agents:
        ls = a.get("last_seen")
        if a.get("status") == "online" and ls:
            try:
                dt = datetime.fromisoformat(ls.rstrip("Z"))
                if (now - dt) > timedelta(seconds=TIMEOUT):
                    a["status"] = "offline"; changed = True
            except: pass
    if changed: save_db("agents", agents)

def start_pulse(interval=30):
    """Startet den Janitor als Daemon-Thread."""
    def loop():
        while True:
            try: pulse_janitor()
            except: pass
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start(); return t
