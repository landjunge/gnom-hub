from fastapi import APIRouter; from pydantic import BaseModel; from gnom_hub.soul.zwc_soul import add_agent_metadata
from gnom_hub.db.legacy_db import get_all_agents, get_active_project, add_chat_message, get_chat_history
from gnom_hub.chat.brainstorm.brainstorm import dispatch; from gnom_hub.soul import soul_instance
from gnom_hub.core.security.showbox_validator import sanitize_showboxes; from .chat_helpers import _parse, _handle_sys
from gnom_hub.chat.chat_commands import handle_clear, handle_status, handle_job, handle_free, handle_git, handle_resume, handle_approve_decision, handle_reject_decision, handle_bake, handle_emergency, handle_diagnose, handle_confirmations, handle_spass
router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def handle_bs(q): return {"status": "dispatched", "asked": dispatch(q, target=None), "mode": "brainstorm"}
def handle_worker(q):
    import re
    q_clean = re.sub(r'^[\s→>\-:]+', '', q).strip()
    return {"status": "dispatched", "asked": dispatch(q_clean, target="worker"), "mode": "worker"}
CMDS = {"clear": handle_clear, "status": lambda q: handle_status(), "job": handle_job, "free": handle_free, "git": handle_git, "project": lambda q: _handle_sys(q, "proj"), "bs": handle_bs, "resume": handle_resume, "approve_decision": handle_approve_decision, "reject_decision": handle_reject_decision, "bake": handle_bake, "emergency": handle_emergency, "notfall": handle_emergency, "diagnose": handle_diagnose, "confirmations": handle_confirmations, "spass": handle_spass, "worker": handle_worker, "workers": handle_worker}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    if msg.sender == "user" and "@merken" in msg.content.lower():
        import re, uuid
        from gnom_hub.db.legacy_db import save_soul_fact
        
        add_chat_message(get_active_project(), "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
        
        cleaned_content = re.sub(r'(?i)\s*@merken\s*', ' ', msg.content).strip()
        if cleaned_content:
            fact_key = f"user_fact_{uuid.uuid4().hex[:8]}"
            save_soul_fact(fact_key, cleaned_content, agent="System", priority="high")
            add_chat_message(get_active_project(), "System", "soulag", "chat", f"💾 **Fakt gemerkt (hohe Priorität):** \"{cleaned_content}\"", {"type": "chat", "sender": "System"})
            return {"status": "saved", "message": cleaned_content}
        else:
            add_chat_message(get_active_project(), "System", "soulag", "chat", "⚠️ **@merken:** Bitte gib einen Text ein, den ich mir merken soll.", {"type": "chat", "sender": "System"})
            return {"status": "error", "message": "Empty content"}

    soul_instance.on_message(msg.content, msg.sender)
    
    # Intercept simple approvals/rejections of pending decisions
    if msg.sender == "user":
        content_clean = msg.content.strip().lower().strip("!.?,")
        if content_clean in ("ja", "nein", "yes", "no", "allow", "block", "erlauben", "ablehnen"):
            from gnom_hub.db.legacy_db import get_state_value
            pending = get_state_value("pending_decisions", {})
            pending_items = [
                (dec_id, d) for dec_id, d in pending.items() 
                if d.get("status") == "pending"
            ]
            if pending_items:
                pending_items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
                decision_id, dec_info = pending_items[0]
                is_approve = content_clean in ("ja", "yes", "allow", "erlauben")
                if is_approve:
                    r = handle_approve_decision(decision_id)
                else:
                    r = handle_reject_decision(decision_id)
                add_chat_message(get_active_project(), "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
                return r

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
