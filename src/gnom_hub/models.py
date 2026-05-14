from pydantic import BaseModel
from typing import Optional

class MemoryEntry(BaseModel):
    agent_id: str
    content: str
    timestamp: Optional[str] = None

class AgentEntry(BaseModel):
    name: str
    description: str = ""
    status: str = "offline"

class AgentIdReq(BaseModel):
    agent_id: str

class SearchReq(BaseModel):
    query: str
