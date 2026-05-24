import os, uuid; from datetime import datetime, timezone; from .db import get_db, save_db, get_active_project; from .router import ask_router; from .config import WORKSPACE_DIR
def get_workspace_dir():
    d = os.path.join(str(WORKSPACE_DIR), get_active_project()); os.makedirs(d, exist_ok=True); return d
def post(sender, content):
    save_db("memory", get_db("memory") + [{"id": str(uuid.uuid4()), "agent_id": "war-room", "project": get_active_project(), "content": content, "metadata": {"type": "brainstorm", "status": "open", "sender": sender}, "timestamp": datetime.now(timezone.utc).isoformat() + "Z"}])
def get_ctx():
    from .zwc_soul import strip_zwc; c = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
    return "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])[:1000]}" for m in sorted(c, key=lambda x: x.get("timestamp",""))[-8:])
def ask_llm(ag, q, ctx, bs_mode=False):
    from .tool_registry import format_tools_prompt; from .soul_initializer import get_soul; from .action_handlers import process_actions; from .zwc_soul import decode_soul
    soul = get_soul(ag["name"]) or {"role": ag.get('description', ''), "permissions": ["read"]}
    sys = format_tools_prompt(soul, ag["name"])
    traits = {}
    for m in get_db("memory") or []:
        s = decode_soul(m.get("content", ""))
        if s and s.get("name") == "user_soul": traits.update({k: v for k, v in s.items() if k not in ("agent", "sig", "name")})
    if traits: sys += f"\n\n[User-Profil] {traits}"
    wd = get_workspace_dir(); fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
    sys += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"
    if bs_mode: sys += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt.]"
    u_msg = f"{q}\n\nBisherige Diskussion:\n{ctx}" if ctx else q
    ags = get_db("agents"); [x.update({"status": "busy"}) for x in ags if x["name"] == ag["name"]]; save_db("agents", ags)
    try:
        ans = ask_router(u_msg, sys, agent_name=ag.get("name", ""))
        if not ans or not isinstance(ans, str): return post(ag["name"], f"[Fehler: Keine Antwort vom LLM]")
        post(ag["name"], process_actions(ans, ag, soul.get("permissions", []), bs_mode, wd))
    except Exception as e: post(ag["name"], f"[Fehler: {str(e)[:80]}]")
    finally:
        ags = get_db("agents"); [x.update({"status": "online", "active_job": ""}) for x in ags if x["name"] == ag["name"]]; save_db("agents", ags)
