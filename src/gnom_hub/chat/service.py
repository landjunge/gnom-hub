from uuid import UUID
from typing import List
from gnom_hub.chat.entities import ChatMessage
from .send_message import SendMessageUseCase
from .brainstorm import BrainstormUseCase


class ChatService:
    """Zentraler Service für alle Chat-Operationen (Senden + Brainstorm)."""

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        brainstorm_use_case: BrainstormUseCase,
    ):
        self._send_message_use_case = send_message_use_case
        self._brainstorm_use_case = brainstorm_use_case

    async def send_message(self, agent_id: UUID, content: str) -> ChatMessage:
        """Einfache Nachricht an einen Agenten senden."""
        return await self._send_message_use_case.execute(agent_id, content)

    async def brainstorm(
        self, agent_ids: List[UUID], topic: str, rounds: int = 3
    ) -> List[ChatMessage]:
        """Paralleles Brainstorming mit mehreren Agenten starten."""
        return await self._brainstorm_use_case.execute(agent_ids, topic, rounds)
