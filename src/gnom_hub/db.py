import json, threading, uuid
from datetime import datetime
from .config import DATA_DIR
_lock = threading.Lock()

def get_db(name: str):
    path = DATA_DIR / f"{name}.json"
    with _lock:
        if path.exists():
            try:
                with open(path, "r") as f: return json.load(f)
            except: return []
            
        # --- AUTO INSTALLATION SEED ---
        if name == "agents":
            seed = [
                {"id": str(uuid.uuid4()), "name": "Kira", "port": 0, "description": "Lead Developer & Architektur", "status": "online", "role": "normal", "created_at": datetime.utcnow().isoformat() + "Z"},
                {"id": str(uuid.uuid4()), "name": "Lian", "port": 0, "description": "Marketing, SEO & Growth", "status": "online", "role": "normal", "created_at": datetime.utcnow().isoformat() + "Z"},
                {"id": str(uuid.uuid4()), "name": "Elara", "port": 0, "description": "UX/UI Design & Konzept", "status": "online", "role": "normal", "created_at": datetime.utcnow().isoformat() + "Z"}
            ]
            with open(path, "w") as f: json.dump(seed, f, indent=2)
            return seed
            
        if name == "memory":
            # Optional: Start with empty memory, the fallback prompt handles the basic roles based on descriptions.
            with open(path, "w") as f: json.dump([], f, indent=2)
            return []
            
    return []

def save_db(name: str, data: list):
    path = DATA_DIR / f"{name}.json"
    with _lock:
        with open(path, "w") as f: json.dump(data, f, indent=2)
