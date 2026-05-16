import requests
import json
from os import getenv
from .db import get_db, save_db

OLLAMA_HOST = "http://localhost:11434"
DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
DEEPSEEK_KEY = getenv("DEEPSEEK_API_KEY")  # aus .env oder env

current_provider = "deepseek"  # Default
current_model = "deepseek-chat"

def add_tokens_to_db(amount: int):
    if amount <= 0: return
    data = get_db("tokens")
    if not data: data = [{"total": 0}]
    data[0]["total"] = data[0].get("total", 0) + amount
    save_db("tokens", data)

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
        current_provider = "deepseek"
        if model:
            current_model = model
        return f"✅ Switched to DeepSeek ({current_model})"

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
        data = r.json()
        if "prompt_eval_count" in data and "eval_count" in data:
            add_tokens_to_db(data["prompt_eval_count"] + data["eval_count"])
        return data["message"]["content"]
    else:
        # Lade den Key dynamisch, falls dotenv erst nach dem Import geladen wurde
        key = getenv("DEEPSEEK_API_KEY")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": current_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "max_tokens": tokens
        }
        r = requests.post(DEEPSEEK_API, json=payload, headers=headers)
        if r.status_code != 200:
            print(f"API ERROR {r.status_code}: {r.text}")
            return f"Fehler vom LLM Provider: {r.text}"
        
        data = r.json()
        if "usage" in data and "total_tokens" in data["usage"]:
            add_tokens_to_db(data["usage"]["total_tokens"])
            
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return f"Unerwartete API Antwort: {data}"
