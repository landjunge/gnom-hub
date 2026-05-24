import uuid, re, subprocess; from datetime import datetime; from fastapi import APIRouter; from .db import get_db, save_db
router = APIRouter()
def _post_chat(s, c): save_db("memory", get_db("memory") + [{"id":str(uuid.uuid4()),"agent_id":"war-room","content":c,"metadata":{"type":"role_response","sender":s},"timestamp":datetime.utcnow().isoformat()+"Z"}])

def handle_clear(q=""): from .chat_clear import handle_clear as _hc; return _hc(q)
def handle_status(): return {"agents": [{"name":a["name"],"role":a.get("role","—"),"st":a.get("skill",a.get("status"))} for a in get_db("agents")]}
def handle_free(q): ags=get_db("agents"); t=q.replace("@","").strip().lower(); [a.update({"active_job":""}) for a in ags if not t or a["name"].lower()==t]; save_db("agents", ags); _post_chat("System", f"Jobs cleared: {t or 'ALL'}"); return {"status": "ok"}
def handle_job(task):
    from .role_tools import distribute_job; from .brainstorm import dispatch; ags = get_db("agents"); gen = next((a for a in ags if a.get("role") == "general" or a.get("name","").lower() == "generalag"), None)
    if not gen: return {"error": "Kein General"}
    save_db("jobs", get_db("jobs") + [{"id": str(uuid.uuid4()), "task": task, "general": gen["name"], "status": "open", "ts": datetime.utcnow().isoformat()+"Z"}])
    res = distribute_job(task); _post_chat(gen["name"], res)
    for a in ags:
        a["active_job"] = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s→>:\-]+(.+)', res) if m.group(1).lower()==a["name"].lower()), "")
        if a["active_job"]: dispatch(a["active_job"], target=a["name"])
    save_db("agents", ags); return {"status": "job_created"}
def handle_git(q, rb=False):
    p = q.split(" ", 1); cmd = f"reset --hard {p[1]}" if rb else (p[1] if len(p)>1 else ""); from pathlib import Path
    if not (Path(".") / ".git").exists(): subprocess.run(["git", "init"], capture_output=True)
    try: r = subprocess.run(["git"] + cmd.split(), capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e: r = f"Error: {e}"
    _post_chat("System", f"Git: {r[:300]}"); return {"status": "ok"}
def handle_publish(q=""):
    from .ftp_sync import sync_index; from .db import get_active_project; from .config import DATA_DIR
    sync_index(DATA_DIR / get_active_project())
    _post_chat("System", "🚀 Manuelles Deployment zu netzwerkpunkt.de abgeschlossen!")
    return {"status": "ok"}
@router.get("/api/ideas")
def get_ideas(): return get_db("ideas")
@router.get("/api/jobs")
def get_jobs(): return sorted(get_db("jobs"), key=lambda j: j.get("ts",""), reverse=True)[:20]
@router.put("/api/agents/{agent_id}/group")
def set_group(aid: str, grp: str = ""): ags=get_db("agents"); a=next((x for x in ags if x["id"]==aid), None); a and (a.update({"group": grp}), save_db("agents", ags)); return {"agent": a["name"]} if a else {"error": "Not found"}
