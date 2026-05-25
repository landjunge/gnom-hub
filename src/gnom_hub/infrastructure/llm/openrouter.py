import httpx; from typing import Optional
from ...core.config import Config; from ...common.exceptions import LLMProviderError

class OpenRouterClient:
    """Einfacher und stabiler OpenRouter Client."""
    def __init__(self):
        self.api_key, self.base_url = Config.OPENROUTER_API_KEY, "https://openrouter.ai/api/v1"
        if not self.api_key: raise LLMProviderError("OPENROUTER_API_KEY ist nicht gesetzt")

    async def ask(self, prompt: str, model: Optional[str] = None) -> str:
        """Testet Modelle nacheinander in fester Reihenfolge."""
        models = [m for m in [model, "google/gemma-2-9b-it", "meta-llama/llama-3.1-8b-instruct", "mistralai/mistral-7b-instruct", "qwen/qwen2.5-7b-instruct", "deepseek/deepseek-chat", "llama3.2"] if m is not None]
        for current_model in models:
            print(f"🟡 OpenRouter Versuch → {current_model}")
            headers = {"Authorization": f"Bearer {self.api_key}", "HTTP-Referer": "http://localhost:8000", "X-Title": "Gnom-Hub"}
            payload = {"model": current_model, "messages": [{"role": "user", "content": prompt}]}
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    print(f"✅ Erfolg mit {current_model}"); return content
                except Exception as e:
                    print(f"❌ Fehlgeschlagen mit {current_model}: {e}")
        raise LLMProviderError("OpenRouter: Alle Modelle sind fehlgeschlagen")
