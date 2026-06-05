import time
import logging
from gnom_hub.db import get_state_value, set_state_value, get_all_agents, set_agent_status
from gnom_hub.db.connection import get_db_conn
from gnom_hub.infrastructure.router.router_call import _call, _try_keys
from gnom_hub.core.structured_log import AgentLogger
from gnom_hub.infrastructure.monitoring import record_agent_request
from gnom_hub.agents.explainability.eo_wrap import wrap_response, wrap_error
from gnom_hub.core.utils.preset_service import get_preset_prompt
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

def _get_behavioral_instructions(settings: dict) -> str:
    custom_insts = []
    p_val = settings.get("personality", 3)
    p_map = {
        1: "Tone instructions: Maintain an extremely formal, professional, and serious tone. Avoid casual language.",
        2: "Tone instructions: Keep a polite, professional, and business-like tone.",
        4: "Tone instructions: Maintain a friendly, warm, and approachable tone.",
        5: "Tone instructions: Be very casual, relaxed, and conversational."
    }
    if p_map.get(p_val):
        custom_insts.append(p_map[p_val])
        
    r_val = settings.get("response_style", 3)
    r_map = {
        1: "Length instructions: Be extremely concise, direct, and brief. Output only essential information.",
        2: "Length instructions: Keep your responses concise and to the point.",
        4: "Length instructions: Provide detailed, comprehensive explanations and structure your answers thoroughly.",
        5: "Length instructions: Be exceptionally detailed and exhaustive. Elaborate on all details, write step-by-step breakdowns, and provide deep context."
    }
    if r_map.get(r_val):
        custom_insts.append(r_map[r_val])
        
    k_val = settings.get("risk_tolerance", 3)
    k_map = {
        1: "Safety/Risk instructions: Prioritize safety, robustness, and stability. Avoid speculative changes, check every dependency, and do not make risky optimizations.",
        2: "Safety/Risk instructions: Be cautious and prefer conservative, well-tested approaches.",
        4: "Safety/Risk instructions: Be proactive and suggest innovative, creative solutions or optimizations.",
        5: "Safety/Risk instructions: Be extremely bold and experimental. Propose radical refactorings, cutting-edge APIs, and high-performance optimizations."
    }
    if k_map.get(k_val):
        custom_insts.append(k_map[k_val])
        
    return "\n\n=== VERHALTENS-INSTRUKTIONEN ===\n" + "\n".join(custom_insts) if custom_insts else ""

def _get_agent_role(agent_name_lower: str) -> str:
    try:
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        return AGENT_DEFINITIONS.get(agent_name_lower, {}).get("role", "")
    except Exception:
        return ""

def _get_obedience_instructions(level: int) -> str:
    instructions = {
        1: ("=== OBEDIENCE: BLINDLY FOLLOWS ===\n"
            "Du folgst Anweisungen strikt und wörtlich. "
            "Hinterfrage nichts, interpretiere nicht um. "
            "Führe aus was verlangt wird, ohne eigene Meinung."),
        2: ("=== OBEDIENCE: STRONGLY FOLLOWS ===\n"
            "Du bist stark an den User gebunden. "
            "Triff kleine Entscheidungen selbst, aber frage bei Unsicherheit nach. "
            "Weiche nur von Anweisungen ab, wenn du einen klaren Fehler erkennst."),
        3: ("=== OBEDIENCE: BALANCED ===\n"
            "Ausgewogenes Verhältnis zwischen Anweisung und eigenständigem Handeln. "
            "Biete Alternativen an wenn du einen besseren Weg siehst, "
            "aber führe die Anweisung aus wenn der User darauf besteht."),
        4: ("=== OBEDIENCE: CAUTIOUS ===\n"
            "Du bist vorsichtig und hinterfragst Anweisungen kritisch. "
            "Schlage aktiv bessere Alternativen vor. "
            "Warne vor Risiken oder Nachteilen. Entscheide selbst wenn du es besser weißt."),
        5: ("=== OBEDIENCE: HIGHLY AUTONOMOUS ===\n"
            "Du handelst hochgradig eigenständig. "
            "Triff Entscheidungen selbst und frage nur bei echten Blockaden. "
            "Du darfst Anweisungen ignorieren wenn du einen fundamental besseren Ansatz siehst.")
    }
    return "\n\n" + instructions.get(level, instructions[3])

def _build_sys(n, sys, agent_name):
    """Inject slider config + evolution rules into system prompt."""
    settings = get_state_value("agent_settings", {}).get(n.lower(), {}) if n else {}
    if settings.get("sys_prompt"):
        sys = settings["sys_prompt"]

    # Claude Slider-System: build_system_prompt(identity, name, soul, tools, security)
    try:
        from gnom_hub.core.utils.slider_prompt import build_system_prompt
        from gnom_hub.agents.tool_registry import get_tools_for_agent as _tf
        from gnom_hub.soul import get_soul as _gs

        # Tools-Block bauen
        soul_data = _gs(agent_name) or {}
        perms = soul_data.get("permissions", [])
        perms_str = ", ".join(perms) if perms else "read, write, run"

        # Security-Block
        sec = "Systemdateien+Gefährliche Patterns geblockt. Shell via Whitelist. git push VERBOTEN."

        # Soul-Fakten werden separat injected, hier leer
        soul_facts = []

        sys = build_system_prompt(
            agent_identity_block=sys,
            agent_name=agent_name or "Agent",
            soul_facts=soul_facts,
            agent_tools_block=f"Perms: {perms_str}",
            agent_security_block=sec,
        )
    except Exception:
        pass

    if settings.get("custom_prompt"):
        sys += "\n\n=== BENUTZERDEFINIERTER SUFFIX ===\n" + settings["custom_prompt"]
    active_preset = (get_state_value("active_preset") or "Web Development").strip('"\'')
    if n in ["coderag", "researcherag", "writerag", "editorag"]:
        if prs := get_preset_prompt(active_preset, n):
            sys = prs + "\n\n" + sys
    if not agent_name:
        return sys

    try:
        av = get_active_version(agent_name)
        r = av.modifications if av else None
        if not r:
            with get_db_conn() as conn:
                r = [row["value"] for row in conn.execute("SELECT value FROM soul_memory WHERE key LIKE ?", (f"evolution_{agent_name}_%",)).fetchall()]
        if r:
            sys += "\n\n=== SELBSTVERBESSERTE REGELN ===\n" + "\n".join(f"- {x}" for x in r)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Evolutions-Regeln-Laden: %s', e)
    return sys

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
        
        txt_routing = load_routing_from_txt()
        if txt_routing and n in txt_routing:
            cfg = txt_routing[n]
        else:
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
                    if cfg.get("provider") != "auto":
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
