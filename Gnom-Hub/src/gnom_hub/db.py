import json
from .config import DATA_DIR

def get_db(name: str):
    path = DATA_DIR / f"{name}.json"
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_db(name: str, data: list):
    path = DATA_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
