import httpx
from typing import Optional
from gnom_hub.core.config import Config
from gnom_hub.core.exceptions import LLMProviderError


class OllamaClient:
    """Client für lokalen Ollama-Server."""

    def __init__(self):
        self.base_url = Config.OLLAMA_BASE_URL.rstrip("/")
        self.timeout = 600.0  # Ollama kann bei großen Modellen langsam sein

    async def ask(self, prompt: str, model: Optional[str] = None) -> str:
        """Sendet eine einfache Prompt-Anfrage an Ollama."""
        model = model or "llama3"  # Standard-Modell, falls keines angegeben

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
            except Exception as e:
                raise LLMProviderError(f"Ollama-Anfrage fehlgeschlagen: {e}") from e
