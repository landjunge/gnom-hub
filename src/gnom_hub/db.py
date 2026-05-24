import json, threading, os, tempfile, fcntl; from .config import DATA_DIR
_lock = threading.Lock()
def _aw(p, d):
    fd, tp = tempfile.mkstemp(dir=str(DATA_DIR), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tp, str(p))
    except Exception as e:
        print(f"[DB] Schreibfehler {p.name}: {e}")
        try: os.unlink(tp)
        except OSError: pass
def _read_locked(p):
    with open(p, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try: return json.load(f)
        finally: fcntl.flock(f.fileno(), fcntl.LOCK_UN)
def get_db(n: str):
    p = DATA_DIR / f"{n}.json"
    with _lock:
        if p.exists():
            try: return _read_locked(p)
            except Exception as e: print(f"[DB] Lesefehler {n}: {e}"); return []
        if n == "agents":
            from .seed import create_seed
            s = create_seed(); _aw(p, s); return s
    return []
def save_db(n: str, d):
    with _lock: _aw(DATA_DIR / f"{n}.json", d)
def _get_state() -> dict:
    p = DATA_DIR / "state.json"
    try: return _read_locked(p) if p.exists() else {}
    except Exception as e: print(f"[DB] state.json Fehler: {e}"); return {}
def _set_state(key: str, value):
    s = _get_state(); s[key] = value
    with _lock: _aw(DATA_DIR / "state.json", s)
def get_active_project() -> str: return _get_state().get("active_project", "default")
def set_active_project(name: str): _set_state("active_project", name.strip())
def get_language() -> str: return _get_state().get("language", "en")
def set_language(lang: str): _set_state("language", lang.strip().lower())
