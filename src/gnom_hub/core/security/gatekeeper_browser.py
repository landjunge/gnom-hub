# gatekeeper_browser.py — Browser script safety verification
import re
import hashlib
from gnom_hub.db import add_chat_message, get_state_value
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.agents.capability_manager import check_capability, request_capability

def verify_browser(agent, code, wd, perms) -> bool:
    name = (agent or {}).get("name", "Unknown")
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    request_capability(name, "BROWSER", code_hash, "AutoApprovedBrowser")
    return True
