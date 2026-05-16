import json, threading, uuid
from datetime import datetime; from .config import DATA_DIR
_lock = threading.Lock()
def get_db(n: str):
    p = DATA_DIR / f"{n}.json"
    with _lock:
        if p.exists():
            try:
                with open(p, "r") as f: return json.load(f)
            except: return []
        if n == "agents":
            s = [{"id": str(uuid.uuid4()), "name": a, "port": 0, "description": d, "status": "online", "role": "normal", "created_at": datetime.utcnow().isoformat() + "Z"} for a, d in [("Kira", "Lead Dev"), ("Lian", "Marketing/SEO"), ("Elara", "UX/UI Design")]]
            with open(p, "w") as f: json.dump(s, f, indent=2)
            return s
        if n == "memory":
            with open(p, "w") as f: json.dump([], f, indent=2)
            return []
    return []
def save_db(n: str, d: list):
    with _lock:
        with open(DATA_DIR / f"{n}.json", "w") as f: json.dump(d, f, indent=2)
def get_active_project() -> str:
    p = DATA_DIR / "state.json"
    try:
        with open(p, "r") as f: return json.load(f).get("active_project", "default") if p.exists() else "default"
    except: return "default"
def set_active_project(name: str):
    p, s = DATA_DIR / "state.json", {}
    if p.exists():
        try:
            with open(p, "r") as f: s = json.load(f)
        except: pass
    s["active_project"] = name.strip()
    with _lock:
        with open(p, "w") as f: json.dump(s, f, indent=2)
