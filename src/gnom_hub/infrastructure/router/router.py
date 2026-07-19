import logging
import time

from gnom_hub.agents.explainability.eo_wrap import wrap_error, wrap_response
from gnom_hub.core.config import Config  # noqa: F401 — re-export for tests patching router.Config
from gnom_hub.core.structured_log import AgentLogger
from gnom_hub.core.utils.routing_override import load_routing_from_txt
from gnom_hub.db import get_all_agents, get_state_value, set_agent_status, set_state_value
from gnom_hub.db.state_repo import SQLiteStateRepository  # noqa: F401 — tests patch this path
from gnom_hub.infrastructure.monitoring import record_agent_request
from gnom_hub.infrastructure.router.router_call import _call, _try_keys
from gnom_hub.infrastructure.router.router_stage import SmartRouter


def _try(pvd, mdl, key, msgs, n):
    try:
        if not key:
            return _try_keys(pvd, mdl, None, msgs, n)
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

def _has_provider_key(kdb: dict, provider: str) -> bool:
    """True if any usable key exists for provider (Wave A: prefer paid)."""
    if not isinstance(kdb, dict):
        return False
    p = provider.lower()
    for k, v in kdb.items():
        kl = str(k).lower()
        if isinstance(v, dict):
            key = v.get("key") or v.get("api_key") or ""
            if not key or len(str(key)) < 8:
                continue
            if str(v.get("provider", "")).lower() == p:
                return True
            if p in kl:  # e.g. key id minimax_…
                return True
        elif isinstance(v, str) and len(v) > 8 and p in kl:
            return True
    return False


def _resolve(pvd, mdl, kdb, n):
    """Build provider/model fallback chain.

    Wave A: prefer stable/paid (MiniMax, then paid providers) before OpenRouter free.
    Free rotation remains a fallback, not the default primary when a paid key exists.
    """
    import os

    from gnom_hub.infrastructure.router.openrouter_free import openrouter_provider_candidates

    prefer_paid = os.environ.get("GNOM_PREFER_PAID", "1").lower() not in ("0", "false", "no")

    if pvd == "auto":
        cands = list(SmartRouter.resolve_stage_candidates(mdl, kdb, n))
        if prefer_paid and _has_provider_key(kdb, "minimax"):
            cands = [("minimax", "MiniMax-M3")] + cands
        return _dedupe_cands(cands)
    if pvd == "lokal":
        return [("lokal", mdl)]

    try:
        repo = SQLiteStateRepository()
    except Exception:
        repo = None

    candidates: list[tuple[str, str]] = []
    # Paid-first injection when routing still points at openrouter/free
    paid_first = prefer_paid and (
        pvd == "openrouter"
        or (isinstance(mdl, str) and ("free" in mdl.lower() or mdl == "openrouter/free"))
    )
    if paid_first and _has_provider_key(kdb, "minimax"):
        candidates.append(("minimax", "MiniMax-M3"))

    if pvd == "openrouter":
        candidates.extend(openrouter_provider_candidates(preferred=mdl, repo=repo))
    elif pvd == "minimax":
        candidates.append(("minimax", mdl or "MiniMax-M3"))
        candidates.extend(openrouter_provider_candidates(preferred=None, repo=repo))
        candidates.append(("lokal", "llama3"))
    elif pvd in ("deepseek", "openai", "anthropic", "gemini", "mistral"):
        candidates.append((pvd, mdl))
        candidates.extend(openrouter_provider_candidates(preferred=None, repo=repo))
    else:
        candidates.append((pvd, mdl))

    if ("lokal", "llama3") not in candidates:
        candidates.append(("lokal", "llama3"))
    return _dedupe_cands(candidates)


def _dedupe_cands(candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

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
        
        from gnom_hub.infrastructure.router.openrouter_free import (
            mark_model_failed,
            mark_model_success,
        )

        for idx, (cp, cm) in enumerate(cands):
            ans = _try("lokal", cm, "", msgs, agent_name) if cp == "lokal" else _try_keys(cp, cm, kdb, msgs, agent_name)
            if ans:
                lat = (time.time() - t0) * 1000
                record_agent_request(n or "unknown", lat, True)
                logger.log_event("llm_call", provider=cp, model=cm, latency_ms=lat, status="success")
                if cp == "openrouter":
                    try:
                        mark_model_success(cm)
                    except Exception:
                        pass
                # CRITICAL FIX: persistiere NICHT den Fallback-Provider. Wenn z.B.
                # minimax fehlschlägt und der Fallback `lokal:llama3` antwortet,
                # würde db["soulag"] dauerhaft auf lokal gesetzt — der nächste
                # Call würde dann nie mehr minimax versuchen. Statt dessen: behalte
                # die ursprüngliche explizite Zuweisung. Drift-Schutz.
                if idx > 0 and cfg.get("_source") != "routing.txt" and cfg.get("_source") != "default":
                    # Fallback-Candidate hat geantwortet — nicht persistieren.
                    logger.log_event("fallback_used", primary=cfg.get("provider"),
                                     primary_model=cfg.get("model"),
                                     fallback_provider=cp, fallback_model=cm)
                # Wenn explizit als auto geroutet (kein _source) UND der Primary hat
                # geantwortet: dann darfst du persistieren, das ist die Auto-Learn-Logik.
                elif idx == 0 and cfg.get("provider") != cp:
                    adb[n] = {"provider": cp, "model": cm}
                    set_state_value("llm_agents", adb)
                if n and ans and len(ans) <= 6000:
                    # Wave A: only GeneralAG (conductor) may auto-dispatch @mentions
                    # from LLM output — workers re-mentioning each other = queue storm.
                    role = _get_agent_role(n)
                    allow_mentions = n in ("generalag",) or role in ("general", "conductor")
                    if allow_mentions:
                        from gnom_hub.agents.swarm.swarm_comms import process_swarm_mentions
                        process_swarm_mentions(
                            agent_name or n, ans, depth=depth, parent_msg_id=parent_msg_id
                        )
                return wrap_response(ans, agent_name or n, p, lat, cp, cm, idx > 0)

            # Free-Model gescheitert (429/404/leer) → cooldown + nächstes Free-Modell
            if cp == "openrouter":
                try:
                    mark_model_failed(cm)
                    logger.log_event(
                        "openrouter_free_rotate",
                        failed_model=cm,
                        next_index=idx + 1,
                        remaining=max(0, len(cands) - idx - 1),
                    )
                except Exception:
                    pass

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
