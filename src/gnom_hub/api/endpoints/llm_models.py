import sys
import time
import asyncio
import logging
from fastapi import APIRouter
import httpx
from gnom_hub.core.config import Config
from gnom_hub.db.state_repo import SQLiteStateRepository

router = APIRouter()

async def check_and_update_models():
    """Fetches, tests all openrouter free models, and caches the working ones in DB."""
    repo = SQLiteStateRepository()
    
    # 1. Fetch free models list from OpenRouter API
    or_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://openrouter.ai/api/v1/models")
            if r.status_code == 200:
                or_models = [m["id"] for m in r.json().get("data", []) if m.get("id", "").endswith(":free")]
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Abruf der OpenRouter-Modelle: %s', e)

    if not or_models:
        or_models = list(Config.OPENROUTER_FREE_MODELS)

    # 2. Get OpenRouter API key
    keys = repo.get_value("llm_keys", {}).values()
    api_key = next((k["key"] for k in keys if k.get("provider") == "openrouter" and k.get("valid")), Config.OPENROUTER_API_KEY)
    if api_key:
        Config.OPENROUTER_API_KEY = api_key

    # 3. Verify each model individually with sequential completions ping
    working_models = []
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "http://localhost:8000", "X-Title": "Gnom-Hub"}
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for model in or_models:
                try:
                    r = await client.post(url, json={"model": model, "messages": [{"role": "user", "content": "Ping"}]}, headers=headers)
                    if r.status_code == 200:
                        working_models.append(model)
                except Exception:
                    pass
                if "pytest" not in sys.modules:
                    await asyncio.sleep(1.0)

        try:
            repo.set_value("openrouter_working_models", working_models)
            return working_models
        except Exception as e:
            logging.getLogger(__name__).error("Error saving models: %s", e)

    return repo.get_value("openrouter_working_models") or []


_cached_available_models = None
_cached_time = 0

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
