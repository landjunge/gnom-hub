from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from .router_config import AGENT_MODELS, DEFAULT_MODELS
from .router_call import _try, _try_keys
from .router_stage import resolve_stage

LOCAL_MODELS = ["llama3", "llama3:latest", "qwen2:7b", "phi3", "phi3:latest", "llama3.2", "gemma2", "gemma2:2b", "mistral"]

def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    n = (agent_name or "").lower()
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    repo = SQLiteStateRepository()
    kdb, adb = repo.get_value("llm_keys") or {}, repo.get_value("llm_agents") or {}
    cfg = adb.get(n) or {"provider": "auto", "model": "stage_3"}
    pvd, mdl = cfg.get("provider", "auto"), cfg.get("model", "stage_3")
    role = "coder" if "coder" in n else "normal"
    if pvd == "auto":
        candidates = get_stage_options(mdl, role)
    else:
        candidates = [(pvd, mdl)] + get_stage_options("stage_3", role)
    for p, m in candidates:
        ans = _try("lokal", m, "", msgs, agent_name) if p == "lokal" else _try_keys(p, m, kdb, msgs, agent_name)
        if ans:
            if cfg.get("provider") != p or cfg.get("model") != m:
                adb[n] = {"provider": p, "model": m}
                repo.set_value("llm_agents", adb)
            return ans
    return "[ROUTER-FEHLER] Alle Gleise offline."
