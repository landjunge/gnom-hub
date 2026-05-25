from fastapi import APIRouter
import requests

router = APIRouter()

@router.get("/api/llm/available_models")
def get_available_models():
    ds_models = ["deepseek-chat", "deepseek-reasoner"]
    or_models = []
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=5)
        if r.status_code == 200:
            or_models = [m["id"] for m in r.json().get("data", []) if m.get("id", "").endswith(":free")]
    except Exception: pass
    if not or_models:
        or_models = ['deepseek/deepseek-v4-flash:free', 'openai/gpt-oss-120b:free', 'qwen/qwen3-coder:free', 'meta-llama/llama-3.3-70b-instruct:free']
    local_models = []
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if r.status_code == 200: local_models = [m["name"] for m in r.json().get("models", []) if m.get("name")]
    except Exception: pass
    if not local_models: local_models = ['llama3', 'mistral', 'qwen2', 'phi3', 'llama3.2', 'gemma2']
    return {
        "auto": ["stage_1", "stage_2", "stage_3", "stage_4"],
        "deepseek": ds_models, "openrouter": or_models, "lokal": local_models,
        "openai": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
        "mistral": ["mistral-large-latest", "pixtral-large-latest", "codestral-latest"]
    }
