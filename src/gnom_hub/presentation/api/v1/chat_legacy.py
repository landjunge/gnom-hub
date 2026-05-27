from fastapi import APIRouter; from pydantic import BaseModel; from gnom_hub.soul.zwc_soul import add_agent_metadata
from gnom_hub.database.legacy_db import get_all_agents, get_active_project, add_chat_message, get_chat_history
from gnom_hub.chat.brainstorm.brainstorm import dispatch; from gnom_hub.soul import soul_instance
from gnom_hub.security.showbox_validator import sanitize_showboxes; from .chat_helpers import _parse, _handle_sys
from gnom_hub.chat.chat_commands import handle_clear, handle_status, handle_job, handle_free, handle_git, handle_resume, handle_approve_decision, handle_reject_decision
router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def handle_bs(q): return {"status": "dispatched", "asked": dispatch(q, target=None), "mode": "brainstorm"}
CMDS = {"clear": handle_clear, "status": lambda q: handle_status(), "job": handle_job, "free": handle_free, "git": handle_git, "project": lambda q: _handle_sys(q, "proj"), "bs": handle_bs, "resume": handle_resume, "approve_decision": handle_approve_decision, "reject_decision": handle_reject_decision}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    soul_instance.on_message(msg.content, msg.sender)
    q, tgt, cmd = _parse(msg.content); s_name = msg.sender if msg.sender != "user" else tgt; ags = get_all_agents()
    a = next((x for x in ags if x.get("name", "").lower() == (s_name or "").lower()), None)
    if a: msg.content = add_agent_metadata(a["name"], msg.content)
    add_chat_message(get_active_project(), msg.sender, "war-room", cmd or "chat", msg.content, {"type": cmd or "chat", "sender": msg.sender})
    if msg.sender != "user": return {"status": "saved"}
    if cmd in CMDS: return CMDS[cmd](q)
    _SYS = ("soulag", "generalag", "watchdogag")
    if cmd == "research":
        asked = [n for n in [x["name"] for x in ags if x.get("status") == "online" and x["name"].lower() not in _SYS] if dispatch(q, target=n)]
        return {"status": "dispatched", "asked": asked, "target": None, "mode": "research"}
    if not cmd and not tgt:
        dispatch(msg.content, target="GeneralAG")
        return {"status": "dispatched", "asked": ["GeneralAG"], "target": "GeneralAG", "mode": "chat"}
    return {"status": "dispatched", "asked": dispatch(q, target=tgt), "target": tgt, "mode": "brainstorm" if cmd == "bs" else "chat"}
@router.get("/api/chat")
def get_chat(limit: int = 50):
    rm = get_chat_history(get_active_project(), limit)
    for m in rm:
        if "content" in m: m["content"] = sanitize_showboxes(m["content"])
    return rm
