import os; from gnom_hub.core.config import WORKSPACE_DIR

def _safe(wd, f, perms):
    if "godmode" in perms: perms = [p for p in perms if p != "godmode"] + ["run"]
    if os.path.isabs(f) and "run" in perms:
        p = os.path.realpath(f)
        return p if p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else None
    p = os.path.realpath(os.path.join(wd, f))
    return p if p.startswith(os.path.realpath(wd)) else None

def is_worker_blocked(agent, f, wd, perms):
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if name.lower() == "generalag" or role == "general": return True
    if role in ["soul", "watchdog", "security"]: return False
    p = _safe(wd, f, perms)
    if p:
        real_wd = os.path.realpath(wd)
        real_p = os.path.realpath(p)
        if real_p == real_wd or real_p.startswith(real_wd + os.sep):
            return False
    check = p or os.path.join(wd, f)
    path_str = os.path.realpath(check).replace("\\", "/").lower()
    if any(part in path_str for part in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]):
        from gnom_hub.database.legacy_db import add_chat_message
        msg = f"@user @SoulAG: Warnung! Worker {agent.get('name')} versucht auf Systemdatei '{f}' zuzugreifen. Zugriff blockiert."
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", msg)
        return True
    return False

def is_security_block(agent, f, content, wd, perms):
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if name.lower() == "generalag" or role == "general": return True
    if role in ["soul", "watchdog", "security"]: return False
    if any(p in content for p in ["rm -rf", "eval(", "os.system(", "subprocess.", "exec(", "pickle.load", "chmod 777", "shutil.rmtree"]):
        from gnom_hub.database.legacy_db import get_state_value, add_chat_message
        approved = [os.path.realpath(os.path.join(wd, a)) for a in (get_state_value("approved_security_writes", []) or [])]
        p = _safe(wd, f, perms)
        if p and os.path.realpath(p) in approved: return False
        msg = f"@user @SoulAG: Warnung! SecurityAG hat die geplante Dateiänderung an '{f}' durch {agent.get('name')} als unsicher eingestuft. Freigabe erforderlich."
        add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
        return True
    return False
