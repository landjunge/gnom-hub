import json, threading
from .config import DATA_DIR
_lock = threading.Lock()
def get_db(name: str):
    path = DATA_DIR / f"{name}.json"
    with _lock:
        if path.exists():
            try:
                with open(path, "r") as f: return json.load(f)
            except: return []
    return []
def save_db(name: str, data: list):
    path = DATA_DIR / f"{name}.json"
    with _lock:
        with open(path, "w") as f: json.dump(data, f, indent=2)
