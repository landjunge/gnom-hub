import time
import logging
from gnom_hub.db import get_state_value, set_state_value, get_all_agents, set_agent_status
from gnom_hub.db.connection import get_db_conn
from gnom_hub.infrastructure.router.router_call import _call, _try_keys
from gnom_hub.core.structured_log import AgentLogger
from gnom_hub.infrastructure.monitoring import record_agent_request
from gnom_hub.agents.explainability.eo_wrap import wrap_response, wrap_error
from gnom_hub.core.utils.evolution_v2 import get_active_version
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.router.router_stage import SmartRouter
from gnom_hub.core.utils.routing_override import load_routing_from_txt
from gnom_hub.core.config import Config

def _try(pvd, mdl, key, msgs, n):
    try:
        return _call(pvd, mdl, key, msgs, n)
    except Exception:
        return None

def _get_agent_role(agent_name_lower: str) -> str:
    try:
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        return AGENT_DEFINITIONS.get(agent_name_lower, {}).get("role", "")
    except Exception:
        return ""

def _build_sys(n, sys, agent_name):
    """Phase-2 SSOT-Delegation. Liest runtime-settings aus state und ruft
    den neuen core.prompt.builder. KEIN override-Pfad mehr.
    
    Verarbeitung passiert vollständig im Builder (Post-Processing: Obedience,
    Behavioral, Custom, Preset, Evolution-Rules).
    """
    from gnom_hub.core.prompt.builder import build_system_prompt as new_build

    # Runtime-Settings aus state-table lesen
    settings = get_state_value("agent_settings", {}).get(n.lower(), {}) if n else {}
    active_preset = (get_state_value("active_preset") or "Web Development").strip('"\'')
    runtime_settings = {**settings, "active_preset": active_preset}

    return new_build(
        agent_name=agent_name or "Agent",
        message_text=sys or "",
        runtime_settings=runtime_settings,
    )

def _resolve(pvd, mdl, kdb, n):
    if pvd == "auto":
        return SmartRouter.resolve_stage_candidates(mdl, kdb, n)
    if pvd == "lokal":
        return [("lokal", mdl)]
    
    candidates = []
    if pvd == "openrouter":
        try:
            working = SQLiteStateRepository().get_value("openrouter_working_models") or []
        except Exception:
            working = []
        if not working:
            working = list(Config.OPENROUTER_FREE_MODELS)

        ordered_working = SmartRouter._order_working_models(working)
        if mdl in working:
            candidates.append((pvd, mdl))
            for wm in ordered_working:
                if wm != mdl:
                    candidates.append(("openrouter", wm))
        else:
            if ordered_working:
                best_fallback = ordered_working[0]
                candidates.append(("openrouter", best_fallback))
                for wm in ordered_working:
                    if wm != best_fallback:
                        candidates.append(("openrouter", wm))
            else:
                candidates.append((pvd, mdl))
    elif pvd == "minimax":
        # Reihenfolge: MiniMax M3 → OpenRouter Free Models → Ollama (lokal)
        candidates.append(("minimax", mdl))
        # OpenRouter Fallback mit Free Models
        try:
            working = SQLiteStateRepository().get_value("openrouter_working_models") or []
        except Exception:
            working = []
        if not working:
            working = list(Config.OPENROUTER_FREE_MODELS)
        ordered_working = SmartRouter._order_working_models(working)
        for wm in ordered_working:
            candidates.append(("openrouter", wm))
        # Ollama als letzter Notnagel
        candidates.append(("lokal", "llama3"))
    elif pvd in ("deepseek", "openai", "anthropic", "gemini", "mistral"):
        candidates.append((pvd, mdl))
        try:
            working = SQLiteStateRepository().get_value("openrouter_working_models") or []
        except Exception:
            working = []
        if not working:
            working = list(Config.OPENROUTER_FREE_MODELS)
        ordered_working = SmartRouter._order_working_models(working)
        for wm in ordered_working:
            candidates.append(("openrouter", wm))
    else:
        candidates.append((pvd, mdl))

    candidates.append(("lokal", "llama3"))
    return candidates

def ask_router(p, sys="Du bist ein Assistent.", agent_name=None, depth=0, parent_msg_id=None):
    """Einzige Routing-Funktion. Gibt immer ExplainableOutput zurück."""
    old_status = "online"
    if agent_name:
        try:
            for a in get_all_agents():
                if a["name"].lower() == agent_name.lower():
                    old_status = a.get("status", "online")
                    break
            set_agent_status(agent_name, "busy")
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in Agenten-Status-Aktualisierung: %s', e)
            
    try:
        n, t0 = (agent_name or "").lower(), time.time()
        sys = _build_sys(n, sys, agent_name)
        msgs = [{"role": "system", "content": sys}, {"role": "user", "content": p}]
        kdb, adb = get_state_value("llm_keys") or {}, get_state_value("llm_agents") or {}
        if isinstance(adb, dict) and "llm_agents" in adb and isinstance(adb["llm_agents"], dict):
            adb = adb["llm_agents"]
        
        cfg = adb.get(n)
        if not cfg:
            txt_routing = load_routing_from_txt()
            if txt_routing and n in txt_routing:
                cfg = dict(txt_routing[n])
                cfg["_source"] = "routing.txt"
            else:
                cfg = {"provider": "auto", "model": "stage_3"}
                cfg["_source"] = "default"
            
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
                    adb[n] = {"provider": cp, "model": cm}
                    set_state_value("llm_agents", adb)
                if n:
                    # Swarm mention detection has a circular import loop:
                    # router -> swarm_comms -> brainstorm -> brainstorm_helpers -> router
                    # Therefore we keep this specific import local to break the loop.
                    from gnom_hub.agents.swarm.swarm_comms import process_swarm_mentions
                    process_swarm_mentions(agent_name or n, ans, depth=depth, parent_msg_id=parent_msg_id)
                return wrap_response(ans, agent_name or n, p, lat, cp, cm, idx > 0)
                
        lat = (time.time() - t0) * 1000
        record_agent_request(n or "unknown", lat, False)
        logger.log_event("llm_call", latency_ms=lat, status="failed")
        return wrap_error("[ROUTER-FEHLER] Alle Gleise offline.", agent_name or "system", p)
    finally:
        if agent_name:
            try:
                set_agent_status(agent_name, old_status)
            except Exception as e:
                logging.getLogger(__name__).error('Fehler in Agenten-Status-Wiederherstellung: %s', e)
