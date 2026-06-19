from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class AgentIdReq(BaseModel):
    agent_id: str

class SearchReq(BaseModel):
    query: str

@router.get("/api/memory/search")
def search_memory(q: str):
    from gnom_hub.memory.semantic_search import semantic_search_memories
    return semantic_search_memories(q)

@router.post("/api/tools/get_memory")
def proxy_get_memory(r: AgentIdReq):
    from gnom_hub.api.endpoints.memory_crud import get_agent_memory
    return get_agent_memory(r.agent_id)

@router.post("/api/tools/search_memory")
def proxy_search_memory(r: SearchReq):
    return search_memory(r.query)
