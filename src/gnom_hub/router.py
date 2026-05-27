import time; from gnom_hub.database.legacy_db import get_state_value, set_state_value, get_db_conn
from gnom_hub.infrastructure.router.router_call import _call, _try_keys
from gnom_hub.structured_log import AgentLogger; from gnom_hub.monitoring import record_agent_request
from gnom_hub.explainability.eo_wrap import wrap_response, wrap_error

def _try(pvd, mdl, key, msgs, n):
    try: return _call(pvd, mdl, key, msgs, n)
    except Exception: return None

def _build_sys(n, sys, agent_name):
    """Inject preset + evolution rules into system prompt."""
    active_preset = (get_state_value("active_preset") or "Web Development").strip('"\'')
    if n in ["coderag", "researcherag", "writerag", "editorag"]:
        from .preset_service import get_preset_prompt
        if prs := get_preset_prompt(active_preset, n): sys = prs + "\n\n" + sys
    if not agent_name: return sys
    try:
        from gnom_hub.evolution_v2 import get_active_version
        av = get_active_version(agent_name)
        r = av.modifications if av else [row["value"] for row in get_db_conn().execute("SELECT value FROM soul_memory WHERE key LIKE ?", (f"evolution_{agent_name}_%",)).fetchall()]
        if r: sys += "\n\n=== SELBSTVERBESSERTE REGELN ===\n" + "\n".join(f"- {x}" for x in r)
    except Exception: pass
    return sys

def _resolve(pvd, mdl, kdb, n):
    if pvd == "auto":
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        return SmartRouter.resolve_stage_candidates(mdl, kdb, n)
    return [("lokal", mdl)] if pvd == "lokal" else [(pvd, mdl), ("lokal", "llama3")]

def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    """Einzige Routing-Funktion. Gibt immer ExplainableOutput zurück."""
    n, t0 = (agent_name or "").lower(), time.time()
    sys = _build_sys(n, sys, agent_name)
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    kdb, adb = get_state_value("llm_keys") or {}, get_state_value("llm_agents") or {}
    cfg = adb.get(n) or {"provider": "auto", "model": "stage_3"}
    pvd, mdl = cfg.get("provider", "auto"), cfg.get("model", "stage_3")
    cands = _resolve(pvd, mdl, kdb, n)
    logger = AgentLogger(agent_name or "Unknown")
    for idx, (cp, cm) in enumerate(cands):
        ans = _try("lokal", cm, "", msgs, agent_name) if cp == "lokal" else _try_keys(cp, cm, kdb, msgs, agent_name)
        if ans:
            lat = (time.time() - t0) * 1000
            record_agent_request(n or "unknown", lat, True)
            logger.log_event("llm_call", provider=cp, model=cm, latency_ms=lat, status="success")
            if cfg.get("provider") != cp or cfg.get("model") != cm:
                if cfg.get("provider") != "auto": adb[n] = {"provider": cp, "model": cm}; set_state_value("llm_agents", adb)
            if n:
                from .swarm_comms import process_swarm_mentions; process_swarm_mentions(agent_name or n, ans)
            return wrap_response(ans, agent_name or n, p, lat, cp, cm, idx > 0)
    lat = (time.time() - t0) * 1000; record_agent_request(n or "unknown", lat, False)
    logger.log_event("llm_call", latency_ms=lat, status="failed")
    return wrap_error("[ROUTER-FEHLER] Alle Gleise offline.", agent_name or "system", p)
