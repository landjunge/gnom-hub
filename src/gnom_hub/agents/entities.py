from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Agent:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    status: str = "stopped"
    pid: int | None = None
    last_seen: datetime | None = None
    model: str | None = None
    port: int = 0
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    role: str = "normal"
    active_job: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.id, str): self.id = UUID(self.id)

    def is_running(self) -> bool:
        return self.status == "running" and self.pid is not None

    def mark_as_running(self, pid: int) -> None:
        self.pid = pid
        self.status = "running"
        self.last_seen = datetime.now()
        self.updated_at = datetime.now()

    def mark_as_stopped(self) -> None:
        self.pid = None
        self.status = "stopped"
        self.updated_at = datetime.now()
