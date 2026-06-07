# gatekeeper_browser.py — Browser script safety verification
import re
import hashlib
from gnom_hub.db import add_chat_message, get_state_value
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.agents.capability_manager import check_capability, request_capability

def verify_browser(agent, code, wd, perms) -> bool:
    name = (agent or {}).get("name", "Unknown")
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
    
    # Auto-approve if confirmations are disabled (default is False)
    from gnom_hub.db import get_state_value, get_active_project
    if not get_state_value("enable_confirmations", False):
        proj = get_active_project()
        add_chat_message(
            proj,
            "WatchdogAG",
            "watchdogag",
            "chat",
            f"⚡ [AUTO-APPROVED] Browser-Aktion von **{name}** (Code Hash: {code_hash}) automatisch freigegeben."
        )
        request_capability(name, "BROWSER", code_hash, "AutoApprovedBrowser")
        return True

    if not isinstance(perms, list) or "godmode" not in perms: return False
    if check_capability(name, "BROWSER", code_hash): return True
    urls = re.findall(r'https?://[^\s\'"]+', code)
    approved = get_state_value("approved_external_urls", []) or []
    for u in urls:
        if not any(lh in u for lh in ["localhost", "127.0.0.1"]) and u not in approved:
            add_chat_message("default", "SecurityAG", "securityag", "chat", f"@user @SoulAG: Warnung! Browser-Aktion versucht externe URL '{u}' aufzurufen. Freigabe erforderlich.")
            return False
    w = ask_router(f"Prüfe Browser-Code:\n{code}", sys="Du bist WatchdogAG. Antworte APPROVED oder REJECTED.", agent_name="WatchdogAG").content
    s = ask_router(f"Prüfe Browser-Code:\n{code}", sys="Du bist SecurityAG. Antworte APPROVED oder REJECTED.", agent_name="SecurityAG").content
    if "APPROVED" in w and "APPROVED" in s:
        request_capability(name, "BROWSER", code_hash, "WatchdogAG+SecurityAG")
        return True
    lbl = "Unsicherheit bei Freigabe" if ("APPROVED" not in w and "REJECTED" not in w) or ("APPROVED" not in s and "REJECTED" not in s) else "Warnung! Keine Freigabe"
    add_chat_message("default", "SecurityAG", "securityag", "chat", f"@user @SoulAG: {lbl} für Browser-Code. W: {w[:40]}... S: {s[:40]}...")
    return False
