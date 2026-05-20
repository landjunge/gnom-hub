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
    if not k:
        from .router import DS_KEY, OR_KEY
        if p == "deepseek" and DS_KEY: k = DS_KEY
        elif p == "openrouter" and OR_KEY: k = OR_KEY
    if not k and p != "lokal": return {"valid": False, "info": f"Kein gültiger Key für {p}"}
    try:
        from .router import _call; ans = _call(p, m, k or "", [{"role":"user", "content":"Ping. Reply OK."}], "Test")
        return {"valid": bool(ans), "info": "OK" if ans else "Keine Antwort"}
    except Exception as e: return {"valid": False, "info": str(e)}
@router.get("/api/llm/available_models")
def get_available_models():
    ds_models = ["deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v4-pro"]
    or_models = []
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
        if r.status_code == 200:
            for m in r.json().get("data", []):
                mid = m.get("id")
                if mid and mid.endswith(":free"):
                    or_models.append(mid)
    except Exception:
        pass
    if not or_models:
        or_models = [
            'deepseek/deepseek-v4-flash:free', 'openai/gpt-oss-120b:free', 'minimax/minimax-m2.5:free',
            'nvidia/nemotron-nano-9b-v2:free', 'qwen/qwen3-coder:free', 'arcee-ai/trinity-large-thinking:free',
            'qwen/qwen3-next-80b:free', 'meta-llama/llama-3.3-70b-instruct:free', 'meta-llama/llama-3.2-3b-instruct:free',
            'nousresearch/hermes-3-llama-3.1-405b:free'
        ]
    local_models = []
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200:
            for m in r.json().get("models", []):
                name = m.get("name")
                if name:
                    local_models.append(name)
    except Exception:
        pass
    if not local_models:
        local_models = ['llama3', 'mistral', 'qwen2', 'phi3', 'llama3.2', 'gemma2']
    return {
        "deepseek": ds_models,
        "openrouter": or_models,
        "lokal": local_models
    }
@router.get("/api/system/info")
def get_system_info():
    import subprocess
    try:
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except:
        cpu = "Intel/Apple Silicon (unknown)"
    try:
        mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        ram = f"{round(mem_bytes / (1024**3))} GB"
    except:
        ram = "32 GB"
    is_intel = "intel" in cpu.lower()
    return {"cpu": cpu, "ram": ram, "is_intel": is_intel}

@router.post("/api/restart")
def restart_server(request: Request):
    from .securityAG import _get_or_create_secret
    if request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex(): return {"error": "Unauthorized"}
    import sys, subprocess; subprocess.Popen([sys.executable] + sys.argv); os._exit(0)
