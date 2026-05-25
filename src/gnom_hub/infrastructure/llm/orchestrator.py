from typing import List, Optional
from ...core.config import Config
from .openrouter import OpenRouterClient
from .ollama import OllamaClient
from ..llm.key_assigner import KeyAssigner
from ...infrastructure.database.agent_repo import SQLiteAgentRepository

class LLMOrchestrator:
    def __init__(self):
        self.default_provider = Config.DEFAULT_LLM_PROVIDER

    async def _get_client(self, provider: str):
        return OpenRouterClient() if provider == "openrouter" else OllamaClient()

    async def ask(self, agent_role: str, prompt: str, model: Optional[str] = None) -> str:
        role = agent_role
        try:
            a = await SQLiteAgentRepository().get_by_id(agent_role)
            if a: role = a.role
        except Exception:
            try:
                a = await SQLiteAgentRepository().get_by_name(str(agent_role))
                if a: role = a.role
            except Exception: pass
        assignment = await KeyAssigner.assign_for_agent(str(role or "normal"), ["ollama", "openrouter"])
        provider = assignment["provider"]
        final_model = model or assignment["model"]
        client = await self._get_client(provider)
        try:
            return await client.ask(prompt, final_model)
        except Exception:
            fb = "ollama" if provider == "openrouter" else "openrouter"
            return await (await self._get_client(fb)).ask(prompt, final_model)

    async def generate_response(self, agent_id: str, messages: List) -> str:
        return await self.ask(agent_id, messages[-1].content if messages else "")
