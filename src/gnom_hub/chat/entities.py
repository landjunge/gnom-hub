from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4


@dataclass
class ChatMessage:
    agent_id: UUID
    role: str                     # "user", "assistant", "system"
    content: str
    id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.now)
    model: Optional[str] = None
    token_count: Optional[int] = None


@dataclass
class FlexSoul:
    """Zentrale Gedächtnis-Struktur eines Agenten (FlexSoul)."""
    agent_id: UUID
    short_term: List[ChatMessage] = field(default_factory=list)

    long_term_summary: str = ""
    last_updated: datetime = field(default_factory=datetime.now)

    def add_message(self, message: ChatMessage):
        self.short_term.append(message)
        self.last_updated = datetime.now()
