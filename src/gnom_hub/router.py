from .router_config import AGENT_MODELS, DEFAULT_MODELS; from .db import get_db
from .router_call import _try, _try_keys, _call, get_keys
LOCAL_MODELS = ["llama3", "llama3:latest", "qwen2:7b", "phi3", "phi3:latest", "llama3.2", "gemma2", "gemma2:2b", "mistral"]
def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    n, msgs = (agent_name or "").lower(), [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    kdb, adb = get_db("llm_keys") or {}, get_db("llm_agents") or {}; cfg = adb.get(n)
    if cfg and cfg.get("provider") and cfg.get("model"):
        pvd, mdl = cfg["provider"], cfg["model"]
        ans = _try("lokal", mdl, "", msgs, agent_name) if pvd == "lokal" else _try_keys(pvd, mdl, kdb, msgs, agent_name)
        if ans: return ans
    ans = _try_keys("deepseek", "deepseek-chat", kdb, msgs, agent_name)
    if ans: return ans
    for m in AGENT_MODELS.get(n, DEFAULT_MODELS):
        ans = _try_keys("openrouter", m, kdb, msgs, agent_name)
        if ans: return ans
    for lm in LOCAL_MODELS:
        ans = _try("lokal", lm, "", msgs, agent_name)
        if ans: return ans
    return "[ROUTER-FEHLER] Alle Gleise offline."
