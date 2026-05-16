"""Chat-Spezial-Befehle + Ideas-API + Job-System."""
import uuid, re, subprocess; from datetime import datetime; from fastapi import APIRouter; from .db import get_db, save_db
router = APIRouter()
def _post_chat(s, c): save_db("memory", get_db("memory") + [{"id":str(uuid.uuid4()),"agent_id":"war-room","content":c,"metadata":{"type":"role_response","sender":s},"timestamp":datetime.utcnow().isoformat()+"Z"}])
def handle_idea(t): save_db("ideas", get_db("ideas") + [{"id":str(uuid.uuid4()),"content":t,"ts":datetime.utcnow().isoformat()+"Z"}]); return {"status": "idea_saved"}
def handle_clear(): save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != "war-room"]); return {"status": "cleared"}
def handle_status(): return {"agents": [{"name":a["name"],"role":a.get("role","—"),"st":a.get("skill",a.get("status"))} for a in get_db("agents")]}
def handle_free(q):
    ags=get_db("agents"); t=q.replace("@","").strip().lower()
    for a in ags:
        if not t or a["name"].lower()==t: a["active_job"]=""
    save_db("agents", ags); _post_chat("System", f"Jobs cleared: {t or 'ALL'}"); return {"status": "ok"}
def handle_skill(q):
    from .role_tools import _llm; ags = get_db("agents"); a = next((x for x in ags if x["name"].lower() == q.replace("@","").strip().lower()), None)
    if a: a["skill"] = _llm("SYSTEM: Fasse in max 3 Wörtern zusammen.", a.get("description",""), 50).strip(); save_db("agents", ags); _post_chat("Skill", f"@{a['name']} Skill: {a['skill']}")
    return {"status": "ok"} if a else {"error": "Fehlt"}
def handle_job(task):
    from .role_tools import distribute_job; ags = get_db("agents"); gen = next((a for a in ags if a.get("role") == "general"), None)
    if not gen: return {"error": "Kein General — erst @general @Name zuweisen"}
    save_db("jobs", get_db("jobs") + [{"id": str(uuid.uuid4()), "task": task, "general": gen["name"], "status": "open", "ts": datetime.utcnow().isoformat()+"Z"}])
    res = distribute_job(task); _post_chat(gen["name"], res)
    for a in ags: a["active_job"] = next((m.group(2).strip() for m in re.finditer(r'@(\w+)[\s-→>:]+(.+)', res) if m.group(1).lower()==a["name"].lower()), "")
    save_db("agents", ags); return {"status": "job_created", "result": res}
def handle_sandbox(code):
    with open("sandbox.py", "w") as f: f.write(code.replace("```python", "").replace("```", "").strip())
    try: out = subprocess.run(["python3", "sandbox.py"], capture_output=True, text=True, timeout=5).stdout
    except Exception as e: out = str(e)
    _post_chat("Sandbox", f"Output:\n```\n{out[:500]}\n```"); return {"status": "executed"}
def handle_summary(q=""):
    from .role_tools import summarize_chat; res = summarize_chat(); _post_chat("Summarizer", res); return {"status": "summarized"}
@router.get("/api/ideas")
def get_ideas(): return get_db("ideas")
@router.get("/api/jobs")
def get_jobs(): return sorted(get_db("jobs"), key=lambda j: j.get("ts",""), reverse=True)[:20]
@router.put("/api/agents/{agent_id}/group")
def set_group(aid: str, grp: str = ""):
    ags = get_db("agents"); a = next((x for x in ags if x["id"] == aid), None)
    if a: a["group"] = grp; save_db("agents", ags)
    return {"agent": a["name"]} if a else {"error": "Not found"}
