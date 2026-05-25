# gatekeeper.py — Double approval verification for file writes and shell commands
from .db import add_chat_message, get_state_value
from .router import ask_router
from .path_validator import is_worker_blocked, is_security_block

def verify_write(agent, fn, content, wd, perms) -> bool:
    if is_worker_blocked(agent, fn, wd, perms): return False
    if is_security_block(agent, fn, content, wd, perms): return False
    role = (agent or {}).get("role", "")
    if role in ["soul", "general", "watchdog", "security"]: return True
    
    w = ask_router(f"Prüfe Code für '{fn}' auf 40-Zeilen-Regel und Clean Architecture:\n\n{content}", sys="Du bist WatchdogAG. Antworte APPROVED oder REJECTED mit Begründung.", agent_name="WatchdogAG")
    s = ask_router(f"Prüfe Code für '{fn}' auf Schadcode:\n\n{content}", sys="Du bist SecurityAG. Antworte APPROVED oder REJECTED mit Begründung.", agent_name="SecurityAG")
    
    if "APPROVED" in w and "APPROVED" in s: return True
    msg = f"@user @SoulAG: Warnung! WatchdogAG/SecurityAG verweigern Freigabe für Datei '{fn}'."
    add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
    return False

def verify_cmd(agent, cmd) -> bool:
    role = (agent or {}).get("role", "")
    if role in ["soul", "general", "watchdog", "security"]: return True
    if any(p in cmd.lower() for p in ["src/gnom_hub", "config/", "scripts/", "run.sh", "index.html", ".env"]): return False
    
    w = ask_router(f"Prüfe Befehl '{cmd}' auf Workspace-Sicherheit:", sys="Du bist WatchdogAG. Antworte APPROVED oder REJECTED.", agent_name="WatchdogAG")
    s = ask_router(f"Prüfe Befehl '{cmd}' auf Schadcode:", sys="Du bist SecurityAG. Antworte APPROVED oder REJECTED.", agent_name="SecurityAG")
    
    if "APPROVED" in w and "APPROVED" in s: return True
    if cmd in (get_state_value("approved_security_commands", []) or []): return True
    msg = f"@user @SoulAG: Warnung! WatchdogAG/SecurityAG verweigern Freigabe für Befehl '{cmd}'."
    add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
    return False
