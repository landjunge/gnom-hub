import requests
import json
from os import getenv

OLLAMA_HOST = "http://localhost:11434"
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = getenv("OPENROUTER_API_KEY")  # aus .env oder env

current_provider = "openrouter"  # Default
current_model = "deepseek/deepseek-chat"

def set_provider(provider: str, model: str = None):
    """Globaler Switch – wird von MCP und allen Agents genutzt."""
    global current_provider, current_model
    if provider == "ollama":
        try:
            requests.get(OLLAMA_HOST + "/api/tags", timeout=2)
            current_provider = "ollama"
            if model:
                current_model = model
            return f"✅ Switched to Ollama ({current_model})"
        except:
            return "❌ Ollama nicht erreichbar – starte `ollama serve`"
    else:
        current_provider = "openrouter"
        if model:
            current_model = model
        return f"✅ Switched to OpenRouter ({current_model})"

def llm_call(prompt: str, system: str = "", tokens: int = 500) -> str:
    """Einheitlicher Call – je nach Provider."""
    global current_provider, current_model
    if current_provider == "ollama":
        payload = {
            "model": current_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False
        }
        r = requests.post(OLLAMA_HOST + "/api/chat", json=payload, timeout=60)
        return r.json()["message"]["content"]
    else:
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "HTTP-Referer": "gnom-hub"}
        payload = {
            "model": current_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": tokens
        }
        r = requests.post(OPENROUTER_API, json=payload, headers=headers)
        return r.json()["choices"][0]["message"]["content"]
