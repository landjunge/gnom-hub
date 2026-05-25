# gatekeeper_browser.py — Browser script safety verification
import re
from .db import add_chat_message, get_state_value
from .router import ask_router

def verify_browser(agent, code, wd, perms) -> bool:
    if "godmode" not in perms: return False
    urls = re.findall(r'https?://[^\s\'"]+', code)
    approved = get_state_value("approved_external_urls", []) or []
    for u in urls:
        if not any(lh in u for lh in ["localhost", "127.0.0.1"]) and u not in approved:
            msg = f"@user @SoulAG: Warnung! Browser-Aktion versucht externe URL '{u}' aufzurufen. Freigabe erforderlich."
            add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
            return False
    w = ask_router(f"Prüfe Browser-Code:\n{code}", sys="Du bist WatchdogAG. Antworte APPROVED oder REJECTED.", agent_name="WatchdogAG")
    s = ask_router(f"Prüfe Browser-Code:\n{code}", sys="Du bist SecurityAG. Antworte APPROVED oder REJECTED.", agent_name="SecurityAG")
    if "APPROVED" in w and "APPROVED" in s: return True
    is_unsure = ("APPROVED" not in w and "REJECTED" not in w) or ("APPROVED" not in s and "REJECTED" not in s)
    lbl = "Unsicherheit bei Freigabe" if is_unsure else "Warnung! Keine Freigabe"
    msg = f"@user @SoulAG: {lbl} für Browser-Code. W: {w[:40]}... S: {s[:40]}..."
    add_chat_message("default", "SecurityAG", "securityag", "chat", msg)
    return False
