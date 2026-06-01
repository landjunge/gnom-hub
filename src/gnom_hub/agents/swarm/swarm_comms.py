# swarm_comms.py — Detects agent-to-agent mentions and dispatches tasks
import logging
import re, time, threading
from gnom_hub.db.legacy_db import get_all_agents, get_state_value, set_state_value

def process_swarm_mentions(sender: str, text: str, depth: int = 0):
    new_depth = depth + 1
    if new_depth > 6:
        try:
            from gnom_hub.db.legacy_db import add_chat_message, get_active_project
            add_chat_message(get_active_project(), "System", "war-room", "chat", f"⚠️ [System] Swarm-Mention-Limit überschritten ({new_depth} > 6). GeneralAG greift automatisch ein, um das Ergebnis fertigzustellen.")
            from gnom_hub.chat.brainstorm.brainstorm import dispatch
            prompt = "[AUTOMATISCHE SYNTHESE] Mention-Limit überschritten. Bitte analysiere den Chatverlauf und erstelle das abschließende Ergebnis."
            threading.Thread(target=dispatch, args=(prompt, "GeneralAG", 0), daemon=True).start()
        except Exception as e: logging.getLogger(__name__).error('Fehler in Swarm-Mention-Limit-Behandlung: %s', e)
        return
    ags = {a["name"].lower(): a["name"] for a in get_all_agents() if a.get("status") == "online"}
    mentions = re.findall(r'@(\w+)', text)
    comms = get_state_value("active_swarm_comms", []) or []
    comms = [c for c in comms if time.time() - c.get("ts", 0) < 15]
    updated = False
    for m in mentions:
        tgt_low = m.lower()
        if tgt_low in ags and tgt_low != sender.lower():
            if sender.lower() == "generalag" and tgt_low in {"soulag", "generalag", "securityag", "watchdogag"}:
                continue
            tgt_name = ags[tgt_low]
            if len(comms) < 6 and not any(c.get("from") == sender and c.get("to") == tgt_name for c in comms):
                comms.append({"from": sender, "to": tgt_name, "ts": time.time()})
                updated = True
                try:
                    from gnom_hub.chat.brainstorm.brainstorm import dispatch
                    threading.Thread(target=dispatch, args=(text, tgt_name, new_depth), daemon=True).start()
                except Exception as e: logging.getLogger(__name__).error('Fehler in Dispatch an Ziel-Agenten: %s', e)
    if updated: set_state_value("active_swarm_comms", comms)
