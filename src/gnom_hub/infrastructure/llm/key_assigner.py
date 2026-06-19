from ...core.config import Config
from ..router.router_stage import SmartRouter


class KeyAssigner:
    """Intelligente Zuweisung von Provider + Modell basierend auf Rolle und Verfügbarkeit."""

    @staticmethod
    async def assign_for_agent(agent_role: str, available_providers: list) -> dict:
        """Gibt optimale Provider + Modell-Kombination zurück."""
        stage = SmartRouter.get_stage_for_role(agent_role)

        preferred = Config.DEFAULT_LLM_PROVIDER
        if preferred not in available_providers:
            preferred = "ollama" if "ollama" in available_providers else (available_providers[0] if available_providers else "ollama")

        avail = Config.OPENROUTER_FREE_MODELS if preferred == "openrouter" else (["deepseek-chat", "deepseek-reasoner"] if preferred == "deepseek" else ["llama3.2", "gemma2"])
        model = SmartRouter.get_best_model(stage, avail)

        return {
            "provider": preferred,
            "model": model,
            "stage": stage,
            "reason": f"Rolle '{agent_role}' → Stufe {stage} ({preferred})"
        }
