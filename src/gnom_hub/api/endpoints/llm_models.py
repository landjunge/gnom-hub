import sys
import time
import asyncio
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
import httpx
from gnom_hub.core.config import Config
from gnom_hub.db.state_repo import SQLiteStateRepository

router = APIRouter()

async def check_opencode_zen_models():
    """Fetches available OpenCode-Zen models, tests each, caches working ones in DB."""
    repo = SQLiteStateRepository()
    keys = repo.get_value("llm_keys", {}).values()
    api_key = next((k["key"] for k in keys if k.get("provider") == "opencode-zen" and k.get("valid")), None)
    if not api_key:
        return repo.get_value("opencode-zen_working_models") or []

    # Fetch model list
    zen_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://opencode.ai/zen/v1/models",
                                  headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code == 200:
                zen_models = [m["id"] for m in r.json().get("data", []) if m.get("id")]
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Abruf der OpenCode-Zen-Modelle: %s', e)

    if not zen_models:
        return repo.get_value("opencode-zen_working_models") or []

    # Test each with a chat completion ping
    working = []
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = "https://opencode.ai/zen/v1/chat/completions"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for model in zen_models:
            try:
                r = await client.post(url, json={"model": model, "messages": [{"role": "user", "content": "Ping"}]}, headers=headers)
                if r.status_code == 200:
                    working.append(model)
            except Exception:
                pass
            if "pytest" not in sys.modules:
                await asyncio.sleep(0.5)

    try:
        repo.set_value("opencode-zen_working_models", working)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler beim Speichern der OpenCode-Zen-Modelle: %s', e)
    return working


async def check_and_update_models():
    """Fetches, tests all free models (OpenRouter + OpenCode-Zen), caches working ones.

    User-Mandat 2026-06-28 06:34: OpenRouter-Pfad DEAKTIVIERT.
    Wir nutzen NUR MiniMax. Nur OpenCode-Zen wird noch gepingt (falls vorhanden).
    """
    repo = SQLiteStateRepository()

    # ── 1. OpenRouter free models — DEAKTIVIERT (User-Mandat 2026-06-28 06:34) ──
    or_models = []   # leer — keine OpenRouter-Calls mehr
    or_working = []
    or_key = None

    # ── 2. OpenCode-Zen models ──
    zen_working = await check_opencode_zen_models()

    # Return combined (legacy: list)
    return or_working + zen_working


_cached_available_models = None
_cached_time = 0

@router.get("/api/llm/providers")
async def get_provider_registry():
    """Returns the full provider registry (from infrastructure/llm/providers.py).

    Shape (frontend-friendly, secrets/headers stripped):
        {
          "providers": [
            {"id": "openai", "display_name": "OpenAI", "caps": [...],
             "category": "llm",       # llm | web_search | tts | other
             "key_prefixes": [...],   # auto-detect patterns
             "label_patterns": [...], # label-substring matches
             "default_model": "..."}, # sensible default
            ...
          ],
          "categories": ["llm", "web_search", "tts", "other"],
          "defaults": {                 # sensible placeholder models per category
              "web_search": {provider_id: model, ...},
              "tts": {provider_id: model, ...},
          }
        }
    """
    try:
        from gnom_hub.infrastructure.llm.providers import PROVIDERS
    except Exception as e:
        logging.getLogger(__name__).error("provider registry import failed: %s", e)
        return {"providers": [], "categories": [], "defaults": {}}

    # Sensible default model names per provider. Kept small + safe; the
    # backend never has to actually call these — they're just placeholders
    # so the input field is never blank.
    DEFAULT_MODEL = {
        "openai":       "gpt-4o-mini",
        "openrouter":   "meta-llama/llama-3.3-70b-instruct:free",
        "anthropic":    "claude-3-5-sonnet-latest",
        "gemini":       "gemini-1.5-flash",
        "deepseek":     "deepseek-chat",
        "mistral":      "mistral-large-latest",
        "minimax":      "MiniMax-M3",
        "opencode-zen": "big-pickle",
        "groq":         "llama-3.1-70b-versatile",
        "cohere":       "command-r-plus",
        "perplexity":   "sonar-pro",
        "together":     "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "fireworks":    "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "replicate":    "meta/meta-llama-3-70b-instruct",
        "huggingface":  "meta-llama/Llama-3.1-8B-Instruct",
        "kimi":         "moonshot-v1-32k",
        "elevenlabs":   "eleven_turbo_v2_5",
        "brave":        "brave-search",
        "tavily":       "tavily-search",
        "serper":       "serper-search",
        "google-cse":   "google-cse",
        "bing-search":  "bing-web-search",
        "duckduckgo":   "duckduckgo-search",
        "you-com":      "you-search",
        "kagi":         "kagi-search",
        "exa":          "exa-search",
        "perplexity-search": "sonar-pro",
        "openai-tts":   "tts-1",
        "edge-tts":     "en-US-AriaNeural",
        "google-tts":   "en-US-Standard-A",
        "azure-tts":    "en-US-JennyNeural",
        "playht":       "playht-2.0",
        "lmnt":         "lmnt-default",
        "coqui":        "coqui-default",
        "cartesia":     "cartesia-sonic",
    }

    # Map caps → category for cleaner UI grouping.
    # Use explicit allow-lists instead of caps-based detection so a provider
    # like 'openai' (which has audio in caps) isn't mistakenly shown under TTS.
    WEB_SEARCH_IDS = {
        "brave", "tavily", "serper", "serpapi", "bing", "bing-search",
        "google_search", "google-cse", "duckduckgo", "you-com", "kagi",
        "exa", "perplexity-search",
    }
    TTS_IDS = {
        "elevenlabs", "openai-tts", "edge-tts", "google-tts", "azure-tts",
        "playht", "lmnt", "coqui", "cartesia", "openai_audio",
    }

    def _category(pid: str, caps: list) -> str:
        if pid in WEB_SEARCH_IDS:
            return "web_search"
        if pid in TTS_IDS:
            return "tts"
        if pid in {"minimax", "openai", "gemini"} and "audio" in caps:
            # Generalist providers that also expose audio; surface under LLM
            # for the main grid — TTS-only section handles dedicated engines.
            return "llm"
        if "web" in caps:
            return "web_search"
        return "llm"

    out_providers = []
    for pid, p in PROVIDERS.items():
        caps = p.get("caps", []) or []
        out_providers.append({
            "id": pid,
            "display_name": p.get("display_name", pid),
            "caps": caps,
            "category": _category(pid, caps),
            "key_prefixes": p.get("key_prefixes", []) or [],
            "label_patterns": p.get("label_patterns", []) or [],
            "default_model": DEFAULT_MODEL.get(pid, ""),
        })

    # Build category-defaults maps for Web Search + TTS.
    # Generalisten (MiniMax/OpenAI/Gemini) tragen ihre audio/web caps ohne in
    # der jeweiligen primary-category zu landen — wir nehmen sie zusätzlich
    # mit auf, damit der Default-Eintrag im Dropdown sinnvoll bleibt.
    web_defaults = {p["id"]: p["default_model"] for p in out_providers
                    if (p["category"] == "web_search" or "web" in p["caps"]) and p["default_model"]}
    tts_defaults  = {p["id"]: p["default_model"] for p in out_providers
                     if (p["category"] == "tts" or "audio" in p["caps"]) and p["default_model"]}

    return {
        "providers": out_providers,
        "categories": ["llm", "web_search", "tts", "other"],
        "defaults": {"web_search": web_defaults, "tts": tts_defaults},
    }


@router.get("/api/llm/service")
async def get_service_config():
    """Returns persisted Web Search + TTS config (provider, model, key id).

    The key_id references an existing entry in `llm_keys`. If no key is bound,
    the user must paste one in the LLM-Keys input above.
    """
    repo = SQLiteStateRepository()
    return {
        "web_search": repo.get_value("llm_service_web_search", {}) or {},
        "tts":        repo.get_value("llm_service_tts", {}) or {},
    }


@router.post("/api/llm/service")
async def save_service_config(req: Request):
    """Persist Web Search + TTS service configuration.

    Body: {"web_search": {provider, model, key_id?}, "tts": {...}}
    Only the keys present in the body are updated (partial update friendly).
    """
    j = await req.json()
    if not isinstance(j, dict):
        return {"status": "error", "info": "invalid body"}

    repo = SQLiteStateRepository()
    if "web_search" in j and isinstance(j["web_search"], dict):
        cur = repo.get_value("llm_service_web_search", {}) or {}
        cur.update({k: v for k, v in j["web_search"].items() if v is not None})
        repo.set_value("llm_service_web_search", cur)
    if "tts" in j and isinstance(j["tts"], dict):
        cur = repo.get_value("llm_service_tts", {}) or {}
        cur.update({k: v for k, v in j["tts"].items() if v is not None})
        repo.set_value("llm_service_tts", cur)
    return {"status": "ok"}


@router.get("/api/llm/available_models")
async def get_available_models():
    global _cached_available_models, _cached_time
    now = time.time()
    if _cached_available_models and (now - _cached_time < 30):
        return _cached_available_models
        
    repo = SQLiteStateRepository()
    or_models = repo.get_value("openrouter_working_models") or list(Config.OPENROUTER_FREE_MODELS)
 
    local_models = []
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            r = await client.get("http://127.0.0.1:11434/api/tags")
            if r.status_code == 200:
                local_models = [m["name"] for m in r.json().get("models", []) if m.get("name")]
    except Exception as e: 
        logging.getLogger(__name__).error('Fehler in Abruf lokaler Ollama-Modelle: %s', e)
        
    if not local_models: 
        local_models = ['llama3', 'mistral', 'qwen2', 'phi3', 'gemma2']
    
    _cached_available_models = {
        "deepseek": ["deepseek-chat", "deepseek-reasoner"], 
        "openrouter": or_models, 
        "lokal": local_models,
        "openai": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
        "mistral": ["mistral-large-latest", "pixtral-large-latest", "codestral-latest"]
    }
    _cached_time = now
    return _cached_available_models

@router.post("/api/llm/check_free_models")
async def check_free_models_endpoint():
    """Testet alle OpenRouter Free-Modelle und gibt die funktionierenden zurück."""
    working = await check_and_update_models()
    return working
