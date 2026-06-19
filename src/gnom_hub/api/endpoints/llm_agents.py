import asyncio
from fastapi import APIRouter, Request
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.router.router_config import DS_KEY, OR_KEY
from gnom_hub.infrastructure.router.router_call import _call

router = APIRouter()

SYSTEM_AGENTS = ["SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG"]
WORKER_AGENTS = ["WriterAG", "CoderAG", "ResearcherAG", "EditorAG"]
ALL_AGENTS = SYSTEM_AGENTS + WORKER_AGENTS


@router.get("/api/llm/agents")
def get_agent_llm():
    d = SQLiteStateRepository().get_value("llm_agents", {})
    return d if isinstance(d, dict) else {}


# Mode → Model-Präferenz (Reihenfolge = Priorität)
# Free-Tier Models pro Provider (für "Only Free Models" und "Local First")
FREE_MODELS = {
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "minimax/minimax-m2.5:free",
        "google/gemma-2-9b-it:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "nvidia/llama-3.1-nemotron-70b-instruct:free",
    ],
    "deepseek":  ["deepseek-chat", "deepseek-reasoner"],
    "gemini":    ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"],
    "groq":      ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "mistral":   ["mistral-small-latest", "open-mistral-7b", "open-mixtral-8x7b"],
    "kimi":      ["moonshot-v1-8k", "moonshot-v1-32k"],
    "github":    ["gpt-4o-mini"],  # GitHub Models hat ein Free-Tier
    "lokal":     ["llama3.2:3b", "llama3.2:1b", "mistral:latest", "gemma2:2b"],
}

# Paid Models pro Provider
PAID_MODELS = {
    "openai":    ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o1-mini", "o1-preview"],
    "anthropic": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    "minimax":   ["MiniMax-M3"],  # multimodal: text + vision + image + tools
}

# Combined für Auto-Routing
PROVIDER_MODELS = {**FREE_MODELS, **PAID_MODELS}


def _pick_provider_and_model(mode: str, available_providers: list) -> tuple:
    """Return (provider, model) for given mode from available providers."""
    # Mode-spezifische Filter — Provider in Reihenfolge der Präferenz pro Mode
    # Hinweis: minimax steht ganz oben in den meisten Modi weil du es aktiv nutzt.
    # OpenRouter bietet `minimax/minimax-m2.5:free` (offiziell Free), und der
    # direkte minimax-Provider ist nutzbar wenn du einen Key hast.
    mode_prefs = {
        "Only Free Models": ["minimax", "openrouter", "opencode-zen", "deepseek", "gemini", "groq", "mistral", "kimi", "github", "lokal"],
        "Local First":      ["lokal", "minimax", "openrouter", "deepseek"],
        "Cost Optimized":   ["minimax", "deepseek", "groq", "openrouter", "opencode-zen", "gemini", "mistral", "openai", "anthropic"],
        "Balanced":         ["minimax", "openrouter", "deepseek", "openai", "anthropic", "gemini", "opencode-zen"],
        "Performance":      ["minimax", "anthropic", "openai", "openrouter", "gemini", "deepseek"],
    }
    prefs = mode_prefs.get(mode, mode_prefs["Balanced"])
    for pvd in prefs:
        if pvd in available_providers:
            models = PROVIDER_MODELS.get(pvd, [])
            if models:
                return pvd, models[0]
    # Fallback: first available
    for pvd in available_providers:
        if PROVIDER_MODELS.get(pvd):
            return pvd, PROVIDER_MODELS[pvd][0]
    return None, None


@router.post("/api/llm/agents")
async def save_agent_llm(req: Request):
    """Save explicit {name: {provider, model}} assignments OR auto-route via {mode, group}."""
    db = SQLiteStateRepository()
    data = await req.json()

    # Auto-Routing path
    if "mode" in data and "group" in data:
        mode = data["mode"]
        group = data["group"]
        agents = SYSTEM_AGENTS if group == "system" else (WORKER_AGENTS if group == "worker" else ALL_AGENTS)
        # Available providers = alle valid-Keys in DB
        kdb = db.get_value("llm_keys", {}) or {}
        available = list({k.get("provider") for k in kdb.values()
                          if isinstance(k, dict) and k.get("valid") and k.get("provider")})
        # Ollama/lokal ist immer verfügbar wenn der Server läuft
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if r.status_code == 200:
                available.append("lokal")
        except Exception:
            pass

        provider, model = _pick_provider_and_model(mode, available)
        if not provider:
            return {"status": "error", "info": f"No working providers for mode '{mode}'", "agents": []}

        new_assignments = {a.lower(): {"provider": provider, "model": model} for a in agents}
        # Merge with existing
        existing = db.get_value("llm_agents", {}) or {}
        if not isinstance(existing, dict):
            existing = {}
        for k, v in new_assignments.items():
            existing[k] = v
        db.set_value("llm_agents", existing)
        # Save to preset too
        preset = db.get_value("active_preset", "Web Development")
        if isinstance(preset, str):
            preset = preset.strip('"\'')
        db.set_value(f"llm_preset_{preset}", existing)

        # Return full list of assignments for the group
        agents_list = [{"name": a, "provider": new_assignments[a.lower()]["provider"],
                        "model": new_assignments[a.lower()]["model"]} for a in agents]
        return {"status": "ok", "mode": mode, "group": group, "agents": agents_list}

    # Explicit assignment path
    db.set_value("llm_agents", data)
    preset = db.get_value("active_preset", "Web Development")
    if isinstance(preset, str):
        preset = preset.strip('"\'')
    db.set_value(f"llm_preset_{preset}", data)
    return {"status": "ok"}

@router.post("/api/llm/test_agent")
async def test_agent(req: Request):
    j = await req.json()
    p, m = j.get("provider"), j.get("model")
    kdb = SQLiteStateRepository().get_value("llm_keys", {})
    if p == "auto":
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        p, m = SmartRouter.resolve_stage(m, kdb, j.get("agent", "Test"))
    
    if p == "openrouter":
        try:
            working = SQLiteStateRepository().get_value("openrouter_working_models") or []
        except Exception:
            working = []
        if working and m not in working:
            from gnom_hub.infrastructure.router.router_stage import SmartRouter
            ordered = SmartRouter._order_working_models(working)
            if ordered:
                m = ordered[0]

    k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p and x.get("valid")), None)
    if not k:
        k = next((x.get("key") for x in (kdb.values() if isinstance(kdb, dict) else kdb) if x.get("provider") == p), None)
    if not k:
        if p == "deepseek" and DS_KEY: k = DS_KEY
        elif p == "openrouter" and OR_KEY: k = OR_KEY
    if not k and p != "lokal": return {"valid": False, "info": f"Kein gültiger Key für {p}", "resolved_provider": p, "resolved_model": m, "caps": []}
    # Caps vom Key oder Provider bestimmen
    key_caps = []
    if p == "lokal":
        key_caps = ["text", "vision", "tools"]
    else:
        for x in (kdb.values() if isinstance(kdb, dict) else kdb):
            if x.get("provider") == p and x.get("valid") and x.get("caps"):
                key_caps = x["caps"]
                break
    if not key_caps:
        key_caps = ["text", "tools"]
    try:
        loop = asyncio.get_running_loop()
        ans = await loop.run_in_executor(None, _call, p, m, k or "", [{"role":"user", "content":"Ping. Reply OK."}], "Test")
        return {"valid": bool(ans), "info": "OK" if ans else "Keine Antwort", "resolved_provider": p, "resolved_model": m, "caps": key_caps if ans else []}
    except Exception as e: return {"valid": False, "info": str(e), "resolved_provider": p, "resolved_model": m, "caps": []}

@router.get("/api/llm/routing_insights")
async def get_routing_insights():
    db = SQLiteStateRepository()
    kdb = db.get_value("llm_keys", {})
    adb = db.get_value("llm_agents", {})
    from gnom_hub.infrastructure.router.router_stage import SmartRouter
    return SmartRouter.get_routing_insights(kdb, adb)
