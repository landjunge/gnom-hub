import time, sqlite3; from .db import get_state_value, set_state_value, get_db_conn
from gnom_hub.infrastructure.router.router_call import _call, _try_keys; from gnom_hub.structured_log import AgentLogger; from gnom_hub.monitoring import record_agent_request
def _try(pvd, mdl, key, msgs, n):
    try: return _call(pvd, mdl, key, msgs, n)
    except Exception: return None
def ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
    n, t0 = (agent_name or "").lower(), time.time()
    active_preset = (get_state_value("active_preset") or "Web Development").strip('"\'')
    if n in ["coderag", "researcherag", "writerag", "editorag"]:
        from .preset_service import get_preset_prompt
        if prs := get_preset_prompt(active_preset, n): sys = prs + "\n\n" + sys
    if agent_name:
        try:
            from gnom_hub.evolution_v2 import get_active_version
            active_version = get_active_version(agent_name)
            if active_version:
                r = active_version.modifications
            else:
                with get_db_conn() as conn:
                    r = [row["value"] for row in conn.execute("SELECT value FROM soul_memory WHERE key LIKE ?", (f"evolution_{agent_name}_%",)).fetchall()]
            if r: sys += "\n\n=== SELBSTVERBESSERTE REGELN ===\n" + "\n".join(f"- {x}" for x in r)
        except Exception: pass
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
    kdb, adb = get_state_value("llm_keys") or {}, get_state_value("llm_agents") or {}
    cfg = adb.get(n) or {"provider": "auto", "model": "stage_3"}
    pvd, mdl = cfg.get("provider", "auto"), cfg.get("model", "stage_3")
    if pvd == "auto":
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        cands = SmartRouter.resolve_stage_candidates(mdl, kdb, n)
    else: cands = [("lokal", mdl)] if pvd == "lokal" else [(pvd, mdl), ("lokal", "llama3")]
    logger = AgentLogger(agent_name or "Unknown")
    for cp, cm in cands:
        ans = _try("lokal", cm, "", msgs, agent_name) if cp == "lokal" else _try_keys(cp, cm, kdb, msgs, agent_name)
        if ans:
            lat = (time.time() - t0) * 1000; record_agent_request(n or "unknown", lat, True); logger.log_event("llm_call", provider=cp, model=cm, latency_ms=lat, status="success")
            if cfg.get("provider") != cp or cfg.get("model") != cm:
                if cfg.get("provider") != "auto": adb[n] = {"provider": cp, "model": cm}; set_state_value("llm_agents", adb)
            if n:
                from .swarm_comms import process_swarm_mentions; process_swarm_mentions(agent_name or n, ans)
            return ans
    lat = (time.time() - t0) * 1000; record_agent_request(n or "unknown", lat, False); logger.log_event("llm_call", latency_ms=lat, status="failed")
    return "[ROUTER-FEHLER] Alle Gleise offline."
