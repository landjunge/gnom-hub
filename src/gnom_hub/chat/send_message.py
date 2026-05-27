from uuid import UUID
from gnom_hub.chat.entities import ChatMessage
from gnom_hub.db.chat_repo import ChatRepository
from gnom_hub.db.agent_repo import AgentRepository
from gnom_hub.infrastructure.llm.orchestrator import LLMOrchestrator
from gnom_hub.core.exceptions import ValidationError

class SendMessageUseCase:
    """Use Case: Nachricht an einen Agenten senden mit intelligentem Auto-Routing."""
    def __init__(self, chat_repo: ChatRepository, agent_repo: AgentRepository, llm_orchestrator: LLMOrchestrator):
        self.chat_repo = chat_repo
        self.agent_repo = agent_repo
        self.llm_orchestrator = llm_orchestrator

    async def execute(self, agent_id: UUID, content: str, role: str = "user") -> ChatMessage:
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent: raise ValidationError(f"Agent mit ID {agent_id} nicht gefunden")
        await self.chat_repo.save_message(ChatMessage(agent_id=agent_id, role=role, content=content))
        response_content = await self.llm_orchestrator.ask(
            agent_role=agent.role or "normal",
            prompt=content,
            model=agent.model
        )
        assistant_message = ChatMessage(agent_id=agent_id, role="assistant", content=response_content, model=agent.model)
        await self.chat_repo.save_message(assistant_message)
        return assistant_message
