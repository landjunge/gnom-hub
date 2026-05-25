import httpx; import asyncio; from typing import Optional
from ...core.config import Config; from ...common.exceptions import LLMProviderError

class OpenRouterClient:
    """Einfacher und stabiler OpenRouter Client."""
    def __init__(self):
        self.api_key, self.base_url = Config.OPENROUTER_API_KEY, "https://openrouter.ai/api/v1"
        if not self.api_key: raise LLMProviderError("OPENROUTER_API_KEY ist nicht gesetzt")

    async def _test_model(self, model: str, prompt: str, timeout: float = 30.0) -> Optional[str]:
        """Testet ein einzelnes Modell und gibt die Antwort zurück, wenn es funktioniert, andernfalls None."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Gnom-Hub"
        }
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    print(f"✅ Erfolg mit {model}")
                    return content
                else:
                    print(f"❌ Fehlgeschlagen mit {model}: Status {response.status_code}")
            except Exception as e:
                print(f"❌ Fehlgeschlagen mit {model}: {e}")
        return None

    async def ask(self, prompt: str, model: Optional[str] = None) -> str:
        from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
        repo = SQLiteStateRepository()

        # Load remembered working models
        working_models = repo.get_value("openrouter_working_models") or []

        # Re-order the list of default models to prioritize previously remembered ones
        from gnom_hub.core.config import Config
        default_order = list(Config.OPENROUTER_FREE_MODELS)


        # Build testing list: requested model first, then previously working, then defaults
        models_to_try = []
        if model:
            models_to_try.append(model)

        for wm in working_models:
            if wm not in models_to_try:
                models_to_try.append(wm)

        for dm in default_order:
            if dm not in models_to_try:
                models_to_try.append(dm)

        # 1. Test the top-most model first
        top_model = models_to_try[0]
        print(f"🟡 OpenRouter Versuch → {top_model}")
        ans = await self._test_model(top_model, prompt)

        if ans is not None:
            # If it works, remember it!
            if top_model not in working_models:
                working_models.append(top_model)
            # Move the successfully used model to the end of the working models list
            # to distribute future requests among other working models (round-robin)
            if top_model in working_models:
                working_models.remove(top_model)
                working_models.append(top_model)
            repo.set_value("openrouter_working_models", working_models)
            return ans

        # 2. If it did not work, test all remaining models in parallel
        print(f"🟡 Oberstes Modell {top_model} fehlgeschlagen. Teste alle verbleibenden Modelle...")
        remaining_models = models_to_try[1:]

        tasks = [self._test_model(m, prompt) for m in remaining_models]
        results = await asyncio.gather(*tasks)

        # Identify which models worked and remember them
        newly_working = []
        first_successful_ans = None
        succeeded_model = None

        for m, res in zip(remaining_models, results):
            if res is not None:
                newly_working.append(m)
                if first_successful_ans is None:
                    first_successful_ans = res
                    succeeded_model = m

        # Update remembered working models list
        updated_working_models = list(working_models)
        if top_model in updated_working_models:
            updated_working_models.remove(top_model)

        for nw in newly_working:
            if nw not in updated_working_models:
                updated_working_models.append(nw)

        # Move the succeeded model to the end of the list to distribute future requests
        if succeeded_model and succeeded_model in updated_working_models:
            updated_working_models.remove(succeeded_model)
            updated_working_models.append(succeeded_model)

        repo.set_value("openrouter_working_models", updated_working_models)

        if first_successful_ans is not None:
            return first_successful_ans

        raise LLMProviderError("OpenRouter: Alle Modelle sind fehlgeschlagen")
