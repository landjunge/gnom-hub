"""Brainstorm Helpers — Workspace, Chat-Post, LLM-Calls."""
import os, uuid
from datetime import datetime
from .db import get_db, save_db
from .router import ask_router

BASE_WORKSPACE = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"

def get_workspace_dir():
    from .db import get_active_project
    d = os.path.join(BASE_WORKSPACE, get_active_project())
    os.makedirs(d, exist_ok=True)
    return d

def post(sender, content):
    from .db import get_active_project
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "project": get_active_project(), "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])

def get_ctx():
    """Holt die letzten 8 Chat-Nachrichten als Kontext."""
    from .db import get_active_project
    from .zwc_soul import strip_zwc
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
    return "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])[:1000]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-8:])

def ask_llm(agent, question, context, bs_mode=False):
    desc = agent.get("description", "")
    role_mem = [m for m in get_db("memory") if m.get("agent_id") == agent.get("id") and m.get("type") == "role"]
    sys_prompt = role_mem[-1]["content"].replace("[SYSTEM-ROLLE] ", "") if role_mem else f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub."
    wd = get_workspace_dir()
    files_str = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
    sys_prompt += f"\n\n[WORKSPACE: {wd} | Dateien: {files_str}]"
    from .zwc_soul import decode_soul
    from .tool_registry import format_tools_prompt
    from .soul_initializer import get_soul
    role_text = role_mem[-1]["content"] if role_mem else ""
    soul = get_soul(agent["name"]) or decode_soul(role_text) or {"role": desc, "permissions": ["read"]}
    sys_prompt += f"\n{format_tools_prompt(soul, agent['name'])}"
    if bs_mode:
        sys_prompt += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt.]"
    user_msg = question
    if context: user_msg += f"\n\nBisherige Diskussion:\n{context}"
    try:
        answer = ask_router(user_msg, sys_prompt, agent_name=agent.get("name", ""))
        if not answer or not isinstance(answer, str):
            post(agent["name"], f"[Fehler: Keine Antwort vom LLM für {agent['name']}]"); return
        from .action_handlers import process_actions
        answer = process_actions(answer, agent, soul.get("permissions", []), bs_mode, wd)
        post(agent["name"], answer)
    except Exception as e: post(agent["name"], f"[Fehler: {str(e)[:80]}]")
