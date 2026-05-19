from fastapi import APIRouter, Request; import requests, os; from .db import get_db, save_db
router = APIRouter()
@router.get("/api/llm/keys")
def get_keys(): d = get_db("llm_keys"); return d if isinstance(d, dict) else {}
@router.post("/api/llm/keys")
async def save_keys(req: Request): j = await req.json(); save_db("llm_keys", j); return {"status": "ok"}
@router.post("/api/llm/test")
async def test_key(req: Request):
    j = await req.json(); k, p = j.get("key"), j.get("provider")
    if p == "deepseek":
        r = requests.get("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {k}"})
        return {"valid": r.status_code == 200, "info": r.text if r.status_code != 200 else "OK"}
    if p == "openrouter":
        r = requests.get("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {k}"})
        return {"valid": r.status_code == 200, "info": r.text if r.status_code != 200 else "OK"}
    return {"valid": True, "info": "Local"}
@router.get("/api/llm/agents")
def get_agent_llm(): d = get_db("llm_agents"); return d if isinstance(d, dict) else {}
@router.post("/api/llm/agents")
async def save_agent_llm(req: Request): j = await req.json(); save_db("llm_agents", j); return {"status": "ok"}
@router.post("/api/llm/test_agent")
async def test_agent(req: Request):
    j = await req.json(); p, m = j.get("provider"), j.get("model"); kdb = get_db("llm_keys") or {}
    k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p and x.get("valid")), None)
    if not k and p != "lokal": return {"valid": False, "info": f"Kein gültiger Key für {p}"}
    try:
        from .router import _call; ans = _call(p, m, k or "", [{"role":"user", "content":"Ping. Reply OK."}], "Test")
        return {"valid": bool(ans), "info": "OK" if ans else "Keine Antwort"}
    except Exception as e: return {"valid": False, "info": str(e)}
@router.post("/api/restart")
def restart_server(): import sys, subprocess; subprocess.Popen([sys.executable] + sys.argv); os._exit(0)
