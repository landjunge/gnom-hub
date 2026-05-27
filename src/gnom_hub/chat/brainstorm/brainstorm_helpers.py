import os, uuid; from datetime import datetime, timezone; from gnom_hub.database.legacy_db import add_chat_message, get_chat_history, get_active_project; from gnom_hub.router import ask_router; from gnom_hub.core.config import WORKSPACE_DIR
def get_workspace_dir():
    d = os.path.join(str(WORKSPACE_DIR), get_active_project()); os.makedirs(d, exist_ok=True); return d
def post(sender, content):
    add_chat_message(get_active_project(), sender, "war-room", "brainstorm", content, {"type": "brainstorm", "status": "open", "sender": sender})
def get_ctx():
    from gnom_hub.soul.zwc_soul import strip_zwc; c = list(reversed(get_chat_history(get_active_project(), limit=8)))
    return "\n".join(f"[{m.get('sender','?')}] {strip_zwc(m['content'])[:1000]}" for m in c)
def ask_llm(ag, q, ctx, bs_mode=False):
    from gnom_hub.agents.tool_registry import format_tools_prompt; from gnom_hub.soul import get_soul; from gnom_hub.action_handlers import process_actions; from gnom_hub.database.legacy_db import set_agent_status, update_agent_active_job
    soul = get_soul(ag["name"]) or {"role": ag.get('description', ''), "permissions": ["read"]}
    sys = format_tools_prompt(soul, ag["name"])
    from gnom_hub.soul import soul_instance
    sys = soul_instance.inject_context(sys, q, agent_name=ag["name"])
    wd = get_workspace_dir(); fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
    sys += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"
    if bs_mode: sys += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt.]"
    u_msg = f"{q}\n\nBisherige Diskussion:\n{ctx}" if ctx else q
    set_agent_status(ag["name"], "busy")
    try:
        eo = ask_router(u_msg, sys, agent_name=ag.get("name", ""))
        if not eo.content: return post(ag["name"], f"[Fehler: Keine Antwort vom LLM]")
        post(ag["name"], process_actions(eo.content, ag, soul.get("permissions", []), bs_mode, wd))
    except Exception as e: post(ag["name"], f"[Fehler: {str(e)[:80]}]")
    finally:
        set_agent_status(ag["name"], "online"); update_agent_active_job(ag["name"], None)
