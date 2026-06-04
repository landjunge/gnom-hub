import os; from gnom_hub.core.config import WORKSPACE_DIR

def _safe(wd, f, perms):
    """Prüft ob ein Pfad im erlaubten Bereich liegt (Workspace oder Projekt-Root)."""
    if "godmode" in perms: perms = [p for p in perms if p != "godmode"] + ["run"]
    if os.path.isabs(f) and "run" in perms:
        p = os.path.realpath(f)
        return p if p.startswith(os.path.realpath(str(WORKSPACE_DIR))) else None
    p = os.path.realpath(os.path.join(wd, f))
    return p if p.startswith(os.path.realpath(wd)) else None

SYSTEM_PATHS = ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]

def is_system_path(path_str: str) -> bool:
    """Prüft ob ein Pfad auf geschützte Systemdateien zeigt."""
    return any(part in path_str.replace("\\", "/").lower() for part in SYSTEM_PATHS)

def is_worker_blocked(agent, f, wd, perms):
    """
    Prüft ob ein Worker-Zugriff auf eine geschützte Systemdatei erfolgt.
    Immer aktiv - nicht an enable_confirmations gekoppelt.
    System-Agenten (soul, watchdog, security) sind ausgenommen.
    """
    name = (agent or {}).get("name", "Unknown")
    role = (agent or {}).get("role", "")
    if role in ["soul", "watchdog", "security"]:
        return False
    p = _safe(wd, f, perms)
    if p:
        real_wd = os.path.realpath(wd)
        real_p = os.path.realpath(p)
        if real_p == real_wd or real_p.startswith(real_wd + os.sep):
            return False
    check = p or os.path.join(wd, f)
    path_str = os.path.realpath(check).replace("\\", "/").lower()
    if is_system_path(path_str):
        from gnom_hub.db import add_chat_message
        msg = f"⚠️ [WatchdogAG] Worker **{name}** versuchte auf Systemdatei '{f}' zuzugreifen. Zugriff BLOCKIERT."
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", msg)
        return True
    return False

DANGEROUS_PATTERNS = ["rm -rf", "eval(", "os.system(", "subprocess.", "exec(", "pickle.load", "chmod 777", "shutil.rmtree"]

def is_security_block(agent, f, content, wd, perms):
    """
    Prüft auf gefährliche Code-Patterns im Datei-Inhalt.
    Immer aktiv - nicht an enable_confirmations gekoppelt.
    System-Agenten sind ausgenommen.
    """
    role = (agent or {}).get("role", "")
    if role in ["soul", "watchdog", "security"]:
        return False
    if any(p in content for p in DANGEROUS_PATTERNS):
        from gnom_hub.db import add_chat_message
        name = (agent or {}).get("name", "Unknown")
        msg = f"⚠️ [SecurityAG] Worker **{name}** versuchte gefaehrlichen Code in '{f}' zu schreiben. Zugriff BLOCKIERT."
        add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
        return True
    return False
