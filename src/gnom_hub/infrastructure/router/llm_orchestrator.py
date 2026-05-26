from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from .router_call import _try_keys, _call

def _try(pvd, mdl, key, msgs, n):
    try: return _call(pvd, mdl, key, msgs, n)
    except Exception: return None

def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    n = (agent_name or "").lower()
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    repo = SQLiteStateRepository()
    kdb, adb = repo.get_value("llm_keys") or {}, repo.get_value("llm_agents") or {}
    cfg = adb.get(n) or {"provider": "auto", "model": "stage_3"}
    pvd, mdl = cfg.get("provider", "auto"), cfg.get("model", "stage_3")
    if pvd == "auto":
        from .router_stage import SmartRouter
        candidates = SmartRouter.resolve_stage_candidates(mdl, kdb, n)
    else:
        if pvd == "lokal":
            candidates = [("lokal", mdl)]
        else:
            candidates = [(pvd, mdl), ("lokal", "llama3")]
    for p, m in candidates:
        ans = _try("lokal", m, "", msgs, agent_name) if p == "lokal" else _try_keys(p, m, kdb, msgs, agent_name)
        if ans:
            if cfg.get("provider") != p or cfg.get("model") != m:
                if cfg.get("provider") != "auto":
                    adb[n] = {"provider": p, "model": m}
                    repo.set_value("llm_agents", adb)
            return ans
    return "[ROUTER-FEHLER] Alle Gleise offline."
