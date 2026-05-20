import json, threading, os, tempfile; from .config import DATA_DIR
_lock = threading.Lock()
def _aw(p, d):
    fd, tp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f: json.dump(d, f, indent=2)
        os.replace(tp, str(p))
    except Exception as e:
        print(f"[DB] Schreibfehler {p.name}: {e}")
        try: os.unlink(tp)
        except: pass
def get_db(n: str):
    p = DATA_DIR / f"{n}.json"
    with _lock:
        if p.exists():
            try: return json.load(open(p, "r"))
            except Exception as e: print(f"[DB] Lesefehler {n}: {e}"); return []
        if n == "agents":
            from .seed import create_seed
            s = create_seed(); _aw(p, s); return s
    return []
def save_db(n: str, d: list):
    with _lock: _aw(DATA_DIR / f"{n}.json", d)
def get_active_project() -> str:
    p = DATA_DIR / "state.json"
    try: return json.load(open(p, "r")).get("active_project", "default") if p.exists() else "default"
    except Exception as e: print(f"[DB] state.json Fehler: {e}"); return "default"
def set_active_project(name: str):
    p, s = DATA_DIR / "state.json", {}
    if p.exists():
        try: s = json.load(open(p, "r"))
        except Exception as e: print(f"[DB] state.json Lesefehler: {e}")
    s["active_project"] = name.strip()
    with _lock: _aw(p, s)
def get_language() -> str:
    p = DATA_DIR / "state.json"
    try: return json.load(open(p, "r")).get("language", "en") if p.exists() else "en"
    except Exception as e: print(f"[DB] state.json language Fehler: {e}"); return "en"
def set_language(lang: str):
    p, s = DATA_DIR / "state.json", {}
    if p.exists():
        try: s = json.load(open(p, "r"))
        except Exception as e: print(f"[DB] state.json Lesefehler: {e}")
    s["language"] = lang.strip().lower()
    with _lock: _aw(p, s)
