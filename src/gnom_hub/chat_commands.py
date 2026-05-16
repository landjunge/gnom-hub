"""Chat-Spezial-Befehle + Ideas-API + Job-System."""
import uuid, re, subprocess; from datetime import datetime; from fastapi import APIRouter; from .db import get_db, save_db
router = APIRouter()
def _uid(): return str(uuid.uuid4())
def _ts(): return datetime.utcnow().isoformat()+"Z"
def _post_chat(s, c): save_db("memory", get_db("memory") + [{"id":_uid(),"agent_id":"war-room","content":c,"metadata":{"type":"role_response","sender":s},"timestamp":_ts()}])
def handle_idea(t): save_db("ideas", get_db("ideas") + [{"id":_uid(),"content":t,"ts":_ts()}]); return {"status": "idea_saved"}
def handle_clear(): save_db("memory", [m for m in get_db("memory") if m.get("agent_id") != "war-room"]); return {"status": "cleared"}
def handle_status(): return {"agents": [{"name":a["name"],"role":a.get("role","—"),"st":a.get("skill",a.get("status"))} for a in get_db("agents")]}
def handle_skill(q):
    from .role_tools import _llm; ags = get_db("agents"); a = next((x for x in ags if x["name"].lower() == q.replace("@","").strip().lower()), None)
    if not a: return {"error": "Agent fehlt"}
    a["skill"] = _llm("SYSTEM: Fasse diese Agent-Beschreibung in max 3 Wörtern zusammen. NUR die Wörter.", a.get("description",""), 50).strip()
    save_db("agents", ags); _post_chat("Skill-Master", f"@{a['name']} Skill: {a['skill']}"); return {"status": "ok"}
def handle_job(task):
    from .role_tools import distribute_job; ags = get_db("agents"); gen = next((a for a in ags if a.get("role") == "general"), None)
    if not gen: return {"error": "Kein General — erst @general @Name zuweisen"}
    save_db("jobs", get_db("jobs") + [{"id": _uid(), "task": task, "general": gen["name"], "status": "open", "ts": _ts()}])
    res = distribute_job(task); _post_chat(gen["name"], res)
    for a in ags: a["active_job"] = ""
    for m in re.finditer(r'@(\w+)[\s-→>:]+(.+)', res):
        for a in ags:
            if a["name"].lower() == m.group(1).lower(): a["active_job"] = m.group(2).strip()
    save_db("agents", ags); return {"status": "job_created", "result": res}
def handle_sandbox(code):
    with open("sandbox.py", "w") as f: f.write(code.replace("```python", "").replace("```", "").strip())
    try: r = subprocess.run(["python3", "sandbox.py"], capture_output=True, text=True, timeout=5); out = r.stdout or r.stderr
    except Exception as e: out = str(e)
    _post_chat("Sandbox", f"Output:\n```\n{out[:500]}\n```"); return {"status": "executed"}
def handle_summary(q=""):
    from .role_tools import summarize_chat; res = summarize_chat(); _post_chat("Summarizer", res); return {"status": "summarized", "result": res}
@router.get("/api/ideas")
def get_ideas(): return get_db("ideas")
@router.get("/api/jobs")
def get_jobs(): return sorted(get_db("jobs"), key=lambda j: j.get("ts",""), reverse=True)[:20]
@router.put("/api/agents/{agent_id}/group")
def set_group(aid: str, grp: str = ""):
    ags = get_db("agents"); a = next((x for x in ags if x["id"] == aid), None)
    if not a: return {"error": "Agent nicht gefunden"}
    a["group"] = grp; save_db("agents", ags); return {"agent": a["name"]}
