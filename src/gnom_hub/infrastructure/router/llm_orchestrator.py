from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from .router_call import _try_keys, _call
from gnom_hub.explainability.eo_wrap import wrap_response, wrap_error

def _try(pvd, mdl, key, msgs, n):
    try: return _call(pvd, mdl, key, msgs, n)
    except Exception: return None

def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    """Einzige Routing-Funktion. Gibt immer ExplainableOutput zurück."""
    import time; t0 = time.time()
    n = (agent_name or "").lower()
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    repo = SQLiteStateRepository()
    kdb, adb = repo.get_value("llm_keys") or {}, repo.get_value("llm_agents") or {}
    cfg = adb.get(n) or {"provider": "auto", "model": "stage_3"}
    pvd, mdl = cfg.get("provider", "auto"), cfg.get("model", "stage_3")
    if pvd == "auto":
        from .router_stage import SmartRouter
        cands = SmartRouter.resolve_stage_candidates(mdl, kdb, n)
    else:
        cands = [("lokal", mdl)] if pvd == "lokal" else [(pvd, mdl), ("lokal", "llama3")]
    for idx, (cp, cm) in enumerate(cands):
        ans = _try("lokal", cm, "", msgs, agent_name) if cp == "lokal" else _try_keys(cp, cm, kdb, msgs, agent_name)
        if ans:
            if cfg.get("provider") != cp or cfg.get("model") != cm:
                if cfg.get("provider") != "auto":
                    adb[n] = {"provider": cp, "model": cm}
                    repo.set_value("llm_agents", adb)
            lat = (time.time() - t0) * 1000
            return wrap_response(ans, agent_name or n, p, lat, cp, cm, idx > 0)
    return wrap_error("[ROUTER-FEHLER] Alle Gleise offline.", agent_name or "system", p)
