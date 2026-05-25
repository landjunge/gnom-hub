from typing import Dict, Tuple
from ...core.config import Config


class SmartRouter:
    """Intelligentes 4-Stufen-Auto-Routing mit Rollen- und Qualitätsbewertung."""

    STAGES: Dict[str, Tuple[int, str, str]] = {
        "stage_1": (1, "free", "fast"),
        "stage_2": (2, "free", "medium"),
        "stage_3": (3, "cheap", "balanced"),
        "stage_4": (4, "premium", "high"),
    }

    ROLE_PREFERENCE = {
        "coder": "stage_4",
        "security": "stage_4",
        "normal": "stage_3",
        "brainstorm": "stage_2",
        "default": "stage_3",
    }

    @staticmethod
    def get_stage_for_role(role: str) -> str:
        return SmartRouter.ROLE_PREFERENCE.get(role.lower(), "stage_3")

    @staticmethod
    def get_best_model(stage: str, available_models: list) -> str:
        preferred = {
            "stage_4": ["claude-3.5-sonnet", "gpt-4o", "deepseek-reasoner"],
            "stage_3": ["gpt-4o-mini", "mistral-large", "llama3.1"],
            "stage_2": ["llama3.2", "gemma2"],
            "stage_1": ["llama3.2", "phi3"],
        }.get(stage, ["llama3.2"])

        for model in preferred:
            if any(model.lower() in m.lower() for m in available_models):
                return model
        return available_models[0] if available_models else "llama3.2"
