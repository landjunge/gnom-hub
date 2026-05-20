from fastapi import APIRouter; from datetime import datetime; import uuid, re; from .db import get_db, save_db, get_active_project; from .brainstorm import dispatch; from .chat_commands import handle_idea, handle_clear, handle_status, handle_job, handle_summary, handle_sandbox, handle_skill, handle_free, handle_checkpoint, handle_git, handle_publish; from pydantic import BaseModel
router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def _parse(t):
    m = re.match(r"@{1,2}(\w+)\s*(.*)", t, re.DOTALL); r, tag = m.group(2).strip() if m else None, m.group(1).lower() if m else None
    if not m: return t, None, None
    if tag in ("bs","idea","clear","status","research","job","summary","sandbox","skill","free","provider","checkpoint","git","rollback","desktop","vision","evolve","project","projekt","publish","browser"): return r or t, None, tag
    if tag in ("summarizer","general","normal"): m2 = re.match(r"@?(\w+)", r); return (t, m2.group(1), tag) if m2 else (t, None, None)
    return r or t, tag, None
def _role(n, r):
    ags = get_db("agents"); a = next((x for x in ags if x["name"].lower() == n.lower()), None)
    if not a: return None
    [x.update({"role": "normal"}) for x in ags if x.get("role") == r and r != "normal"]; a["role"] = r; save_db("agents", ags); return a["name"]
def _handle_sys(q, m):
    from .chat_commands import _post_chat
    if m=="prov": from .provider_switchAG import set_provider; p=q.split(); _post_chat("System", set_provider(p[0], p[1] if len(p)>1 else None)) if p else None
    elif m=="vis": from .visionAG import vision_loop; _post_chat("System", vision_loop(q))
    elif m=="evol": from .evolutionAG import evolve_agent; _post_chat("System", evolve_agent(q))
    elif m=="proj": from .db import set_active_project; set_active_project(q or "default"); _post_chat("System", f"Project: {q or 'default'}")
    elif m=="brow": from .browserAG import browser_cmd; _post_chat("System", browser_cmd(q))
    else: from .desktopAG import desktop_action; _post_chat("System", desktop_action(q))
    return {"status": "ok"}
CMDS = {"idea": handle_idea, "clear": handle_clear, "status": lambda q: handle_status(), "job": handle_job, "summary": handle_summary, "sandbox": handle_sandbox, "skill": handle_skill, "free": handle_free, "provider": lambda q: _handle_sys(q,"prov"), "checkpoint": handle_checkpoint, "git": handle_git, "rollback": lambda q: handle_git(q, rb=True), "desktop": lambda q: _handle_sys(q,"desk"), "vision": lambda q: _handle_sys(q,"vis"), "evolve": lambda q: _handle_sys(q,"evol"), "projekt": lambda q: _handle_sys(q,"proj"), "project": lambda q: _handle_sys(q,"proj"), "publish": lambda q: handle_publish(q), "browser": lambda q: _handle_sys(q,"brow")}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    q, tgt, cmd = _parse(msg.content); s_name = msg.sender if msg.sender != "user" else tgt; from .securityAG import seal_content
    a = next((x for x in get_db("agents") if x.get("name","").lower() == (s_name or "").lower()), None)
    if a: msg.content = seal_content(a["name"], msg.content)
    save_db("memory", get_db("memory") + [{"id": str(uuid.uuid4()), "agent_id": "war-room", "project": get_active_project(), "content": msg.content, "metadata": {"type": cmd or "chat", "sender": msg.sender}, "timestamp": datetime.utcnow().isoformat()+"Z"}])
    if msg.sender != "user": return {"status": "saved"}
    if cmd in CMDS: return CMDS[cmd](q)
    if cmd == "research": return {"status": "dispatched", "asked": [n for n in [a["name"] for a in get_db("agents") if a.get("status")=="online" and a.get("role") not in ("general","summarizer")] if dispatch(q, target=n)], "target": None, "mode": "research"}
    if cmd in ("general","summarizer","normal") and tgt: n = _role(tgt, cmd); return {"status": "role_set", "agent": n, "role": cmd} if n else {"status": "error"}
    if not cmd and not tgt: from .gatekeeperAG import intercept; return intercept(msg.content)
    return {"status": "dispatched", "asked": dispatch(q, target=tgt), "target": tgt, "mode": "brainstorm" if cmd=="bs" else "chat"}
@router.get("/api/chat")
def get_chat(limit: int = 50): 
    from .showbox_validator import sanitize_showboxes; rm = sorted([m for m in get_db("memory") if m.get("agent_id")=="war-room" and m.get("project", "default") == get_active_project()], key=lambda x: x.get("timestamp",""), reverse=True)[:limit]
    for m in rm:
        if "content" in m: m["content"] = sanitize_showboxes(m["content"])
    return rm