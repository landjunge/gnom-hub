import os, uuid; from datetime import datetime, timezone; from gnom_hub.db import add_chat_message, get_chat_history, get_active_project; from gnom_hub.infrastructure.router.router import ask_router; from gnom_hub.core.config import WORKSPACE_DIR
def get_workspace_dir():
    d = os.path.join(str(WORKSPACE_DIR), get_active_project()); os.makedirs(d, exist_ok=True); return d
def post(sender, content, depth=0):
    add_chat_message(get_active_project(), sender, "war-room", "brainstorm", content, {"type": "brainstorm", "status": "open", "sender": sender, "mention_depth": depth})
def get_ctx():
    from gnom_hub.soul.zwc_soul import strip_zwc; c = list(reversed(get_chat_history(get_active_project(), limit=8)))
    return "\n".join(f"[{m.get('sender','?')}] {strip_zwc(m['content'])[:1000]}" for m in c)
def ask_llm(ag, q, ctx, bs_mode=False, depth=0):
    from gnom_hub.agents.tool_registry import format_tools_prompt; from gnom_hub.soul import get_soul; from gnom_hub.agents.actions.action_handlers import process_actions; from gnom_hub.db import set_agent_status, update_agent_active_job
    soul = get_soul(ag["name"]) or {"role": ag.get('description', ''), "permissions": ["read"]}
    sys = format_tools_prompt(soul, ag["name"])
    from gnom_hub.soul import soul_instance
    sys = soul_instance.inject_context(sys, q, agent_name=ag["name"])
    wd = get_workspace_dir(); fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
    sys += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"
    if bs_mode: sys += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt.]"
    u_msg = (
        f"Aufgabe/Frage: {q}\n\n"
        f"Verlauf der bisherigen Diskussion (nur zur Information):\n"
        f"===\n{ctx}\n===\n\n"
        f"WICHTIG: Antworte jetzt ausschließlich als {ag['name']} auf die Aufgabe/Frage unter Berücksichtigung des Verlaufs. Spiele keine anderen Rollen."
    ) if ctx else q
    set_agent_status(ag["name"], "busy")
    try:
        eo = ask_router(u_msg, sys, agent_name=ag.get("name", ""), depth=depth)
        if not eo.content: return post(ag["name"], f"[Fehler: Keine Antwort vom LLM]", depth=depth)
        processed = process_actions(eo.content, ag, soul.get("permissions", []), bs_mode, wd)
        
        has_failure = any(term in processed for term in ["[Gatekeeper:", "Fehler:", "blockiert", "BLOCKIERT", "not found", "command not found", "permission denied"]) or ("keine" in processed and "Berechtigung" in processed)
        has_showbox = any(tag in processed for tag in ["<SHOWBOX", "<showbox", "[SHOWBOX", "[showbox"])
        
        if has_failure and not has_showbox and not bs_mode:
            retry_prompt = (
                f"Beobachtung (Systemfehler / Aktion fehlgeschlagen):\n"
                f"{processed}\n\n"
                f"WICHTIG: Melde dieses Fehlen SOFORT dem Benutzer über die Showbox! "
                f"Schreibe dazu ein EXTREM kurzes, scrollfreies Showbox-Update (maximal 1-2 Zeilen), das perfekt ohne Scrollen in die Box passt! "
                f"Verwende genau den Titel '<h3>🛑 CRITICAL: System-Blockade</h3>' und nenne kurz den Grund (z. B. fehlendes Tool, fehlendes WRITE oder fehlendes SHELL). "
                f"Format: <SHOWBOX:2>[\"<h3>🛑 CRITICAL: System-Blockade</h3><p>Fehlende Berechtigung: WRITE.</p>\"]</SHOWBOX>"
            )
            eo2 = ask_router(retry_prompt, sys + f"\n\nBisherige Gedanken/Antwort:\n{eo.content}", agent_name=ag.get("name", ""), depth=depth)
            if eo2.content:
                processed = process_actions(eo2.content, ag, soul.get("permissions", []), bs_mode, wd)
                
        post(ag["name"], processed, depth=depth)
    except Exception as e: post(ag["name"], f"[Fehler: {str(e)[:80]}]", depth=depth)
    finally:
        set_agent_status(ag["name"], "online"); update_agent_active_job(ag["name"], None)
