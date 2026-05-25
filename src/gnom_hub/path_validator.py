# path_validator.py — Workspace-basierte Pfadvalidierung
import os; from .config import WORKSPACE_DIR

def _safe(wd, f, perms):
    if "godmode" in perms: perms = [p for p in perms if p != "godmode"] + ["run"]
    if os.path.isabs(f) and "run" in perms:
        p = os.path.realpath(f)
        return p if p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else None
    p = os.path.realpath(os.path.join(wd, f))
    return p if p.startswith(os.path.realpath(wd)) else None

def is_worker_blocked(agent, f, wd, perms):
    role = (agent or {}).get("role", "")
    if role in ["soul", "general", "watchdog", "security"]: return False
    p = _safe(wd, f, perms)
    check = p or os.path.join(wd, f)
    path_str = os.path.realpath(check).replace("\\", "/").lower()
    if any(part in path_str for part in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]):
        from .db import get_state_value, add_chat_message
        approved = [os.path.realpath(os.path.join(wd, a)) for a in (get_state_value("approved_system_paths", []) or [])]
        if os.path.realpath(check) in approved: return False
        msg = f"@user @SoulAG: Warnung! Worker {agent.get('name')} versucht auf Systemdatei '{f}' zuzugreifen. Zugriff blockiert."
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", msg)
        return True
    return False
