import asyncio
from fastapi import APIRouter
import httpx
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository

router = APIRouter()

async def check_and_update_models():
    """Fetches, tests all openrouter free models, and caches the working ones in DB."""
    import asyncio
    import httpx
    from gnom_hub.core.config import Config
    from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
    from gnom_hub.infrastructure.llm.openrouter import OpenRouterClient
    
    repo = SQLiteStateRepository()
    or_models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://openrouter.ai/api/v1/models")
            if r.status_code == 200:
                or_models = [m["id"] for m in r.json().get("data", []) if m.get("id", "").endswith(":free")]
    except Exception:
        pass
        
    if not or_models:
        or_models = list(Config.OPENROUTER_FREE_MODELS)
        
    # Load OpenRouter API key
    for k in repo.get_value("llm_keys", {}).values():
        if k.get("provider") == "openrouter" and k.get("valid"):
            Config.OPENROUTER_API_KEY = k.get("key")
            
    if Config.OPENROUTER_API_KEY:
        try:
            client = OpenRouterClient()
            tasks = [client._test_model(m, "Ping", timeout=5.0) for m in or_models]
            results = await asyncio.gather(*tasks)
            working = [m for m, res in zip(or_models, results) if res is not None]
            repo.set_value("openrouter_working_models", working)
            return working
        except Exception as e:
            print(f"Error checking models: {e}")
    return repo.get_value("openrouter_working_models") or []


@router.get("/api/llm/available_models")
async def get_available_models():
    repo = SQLiteStateRepository()
    
    or_models = repo.get_value("openrouter_working_models")
    if not or_models:
        from gnom_hub.core.config import Config
        or_models = list(Config.OPENROUTER_FREE_MODELS)
 
    local_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://127.0.0.1:11434/api/tags")
            if r.status_code == 200:
                local_models = [m["name"] for m in r.json().get("models", []) if m.get("name")]
    except Exception: pass
    if not local_models: local_models = ['llama3', 'mistral', 'qwen2', 'phi3', 'gemma2']
    
    return {
        "deepseek": ["deepseek-chat", "deepseek-reasoner"], 
        "openrouter": or_models, 
        "lokal": local_models,
        "openai": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
        "mistral": ["mistral-large-latest", "pixtral-large-latest", "codestral-latest"]
    }

@router.post("/api/llm/check_free_models")
async def check_free_models_endpoint():
    """Testet alle OpenRouter Free-Modelle und gibt die funktionierenden zurück."""
    working = await check_and_update_models()
    return working
