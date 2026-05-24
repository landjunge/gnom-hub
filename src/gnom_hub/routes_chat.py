from fastapi import APIRouter; from datetime import datetime, timezone; import uuid, re; from .db import get_all_agents, get_active_project, add_chat_message; from .brainstorm import dispatch; from .chat_commands import handle_clear, handle_status, handle_job, handle_free, handle_git; from pydantic import BaseModel
router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def _parse(t):
    m = re.match(r"@{1,2}(\w+)\s*(.*)", t, re.DOTALL); r, tag = m.group(2).strip() if m else None, m.group(1).lower() if m else None
    if not m: return t, None, None
    if tag in ("bs","clear","status","research","job","free","git","project"): return r or t, None, tag
    return r or t, tag, None
def _handle_sys(q, m):
    from .chat_commands import _post_chat
    if m=="proj": from .db import set_active_project; set_active_project(q or "default"); _post_chat("System", f"Project: {q or 'default'}")
    return {"status": "ok"}
def handle_bs(q): return {"status": "dispatched", "asked": dispatch(q, target=None), "mode": "brainstorm"}
CMDS = {"clear": handle_clear, "status": lambda q: handle_status(), "job": handle_job, "free": handle_free, "git": handle_git, "project": lambda q: _handle_sys(q,"proj"), "bs": handle_bs}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    q, tgt, cmd = _parse(msg.content); s_name = msg.sender if msg.sender != "user" else tgt; from .zwc_soul import add_agent_metadata; ags = get_all_agents()
    a = next((x for x in ags if x.get("name","").lower() == (s_name or "").lower()), None)
    if a: msg.content = add_agent_metadata(a["name"], msg.content)
    add_chat_message(get_active_project(), msg.sender, "war-room", cmd or "chat", msg.content, {"type": cmd or "chat", "sender": msg.sender})
    if msg.sender != "user": return {"status": "saved"}
    if cmd in CMDS: return CMDS[cmd](q)
    _SYS = ("soulag", "generalag", "watchdogag")
    if cmd == "research": return {"status": "dispatched", "asked": [n for n in [x["name"] for x in ags if x.get("status")=="online" and x["name"].lower() not in _SYS] if dispatch(q, target=n)], "target": None, "mode": "research"}
    if not cmd and not tgt: dispatch(msg.content, target="GeneralAG"); return {"status": "dispatched", "asked": ["GeneralAG"], "target": "GeneralAG", "mode": "chat"}
    return {"status": "dispatched", "asked": dispatch(q, target=tgt), "target": tgt, "mode": "brainstorm" if cmd=="bs" else "chat"}
@router.get("/api/chat")
def get_chat(limit: int = 50): 
    from .showbox_validator import sanitize_showboxes; from .db import get_chat_history; rm = get_chat_history(get_active_project(), limit)
    for m in rm:
        if "content" in m: m["content"] = sanitize_showboxes(m["content"])
    return rm