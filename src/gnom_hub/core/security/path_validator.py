import os; from gnom_hub.core.config import WORKSPACE_DIR
import re as _re

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
    Immer aktiv. System-Agenten (soul, watchdog, security) sind ausgenommen.
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
        msg = f"[WatchdogAG] {name} auf Systemdatei '{f}' BLOCKIERT."
        add_chat_message("default", "WatchdogAG", "watchdogag", "chat", msg)
        return True
    return False

# Gefährliche Code-Patterns — regex-basiert mit verschleierten Varianten
_DANGEROUS_RE = _re.compile(
    r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|[a-zA-Z]*-r[a-zA-Z]*-f[a-zA-Z]*)"
    r"|subprocess\.(call|run|Popen|check_output)"
    r"|os\.system\s*\(|os\.popen\s*\(|os\.exec[lvpe]*\s*\(|os\.spawn[lvpe]*\s*\("
    r"|eval\s*\(|exec\s*\(|__import__\s*\(|compile\s*\(.*?(?:eval|exec)"
    r"|shutil\.rmtree\s*\(|shutil\.move\s*\([^,]*,[^,]*/(?:etc|usr|bin|sbin|var|root|tmp)"
    r"|pickle\.(?:load|dumps)\s*\(|marshal\.(?:load|dumps)\s*\(|bytes\.decode\s*\(.*?\)\s*"
    r"|chmod\s+[0-7]*7[0-7]*7\s"
    r"|>\s*/(?:etc|usr|bin|sbin|var|dev)/|>>\s*/(?:etc|usr|bin|sbin|var|dev)/"
    r"|curl.*\|\s*(?:ba)?sh|wget.*\|\s*(?:ba)?sh"
    r"|dd\s+if=|mkfs\.|:\(\)\s*\{\s*:\|:&\s*\};:"
    r"|input\s*\(.*?exec|__builtins__|__globals__|__getattribute__|base64\..*decode",
    _re.IGNORECASE | _re.DOTALL
)

def is_security_block(agent, f, content, wd, perms):
    """
    Regex-basierte Prüfung auf gefährliche Code-Patterns.
    Immer aktiv. System-Agenten sind ausgenommen.
    """
    role = (agent or {}).get("role", "")
    if role in ["soul", "watchdog", "security"]:
        return False

    if not content or not content.strip():
        return False

    if _DANGEROUS_RE.search(content):
        from gnom_hub.db import add_chat_message
        name = (agent or {}).get("name", "Unknown")
        msg = f"[SecurityAG] {name} verwendet gefaehrliches Code-Pattern. BLOCKIERT."
        add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
        return True

    return False
