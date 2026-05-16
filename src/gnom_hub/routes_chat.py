from fastapi import APIRouter; from datetime import datetime; import uuid, re; from .db import get_db, save_db; from .brainstorm import dispatch; from .chat_commands import handle_idea, handle_clear, handle_status, handle_job, handle_summary; from pydantic import BaseModel
router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def _parse(t):
    m = re.match(r"@(\w+)\s*(.*)", t, re.DOTALL); r = m.group(2).strip() if m else None
    if not m: return t, None, None
    tag = m.group(1).lower()
    if tag in ("bs","idea","clear","status","research","job","summary"): return r or t, None, tag
    if tag in ("summarizer","general","normal"):
        m2 = re.match(r"@?(\w+)", r); return (t, m2.group(1), tag) if m2 else (t, None, None)
    return r or t, tag, None
def _role(name, role):
    agents = get_db("agents"); a = next((x for x in agents if x["name"].lower() == name.lower()), None)
    if not a: return None
    for x in agents:
        if x.get("role") == role and role != "normal": x["role"] = "normal"
    a["role"] = role; save_db("agents", agents); return a["name"]
CMDS = {"idea": handle_idea, "clear": lambda q: handle_clear(), "status": lambda q: handle_status(), "job": handle_job, "summary": handle_summary}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    q, tgt, cmd = _parse(msg.content)
    s_name = msg.sender if msg.sender != "user" else tgt
    a = next((x for x in get_db("agents") if x.get("name","").lower() == (s_name or "").lower()), None)
    if a and a.get("description"):
        job = f" [MISSION: {a['active_job']}]" if a.get("active_job") else ""
        msg.content += f' <span style="display:none" data-soul="{a["name"]}">[SOUL: {a["description"]}]{job}</span>'
    save_db("memory", get_db("memory") + [{"id": str(uuid.uuid4()), "agent_id": "war-room", "content": msg.content, "metadata": {"type": cmd or "chat", "sender": msg.sender}, "timestamp": datetime.utcnow().isoformat()+"Z"}])
    if msg.sender != "user": return {"status": "saved"}
    if cmd in CMDS: return CMDS[cmd](q)
    if cmd == "research":
        tgts = [a["name"] for a in get_db("agents") if a.get("status")=="online" and a.get("role") not in ("general","summarizer")]
        return {"status": "dispatched", "asked": [n for n in tgts if dispatch(q, target=n)], "target": None, "mode": "research"}
    if cmd in ("general","summarizer","normal") and tgt: n = _role(tgt, cmd); return {"status": "role_set", "agent": n, "role": cmd} if n else {"status": "error"}
    return {"status": "dispatched", "asked": dispatch(q, target=tgt), "target": tgt, "mode": "brainstorm" if cmd=="bs" else "chat"}
@router.get("/api/chat")
def get_chat(limit: int = 50): return sorted([m for m in get_db("memory") if m.get("agent_id")=="war-room"], key=lambda x: x.get("timestamp",""), reverse=True)[:limit]