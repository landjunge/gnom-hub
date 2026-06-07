from fastapi import APIRouter, HTTPException
from uuid import UUID
from typing import List
from pydantic import BaseModel
from gnom_hub.infrastructure.router.llm_orchestrator import LLMOrchestrator

class BrainstormRequest(BaseModel):
    agent_ids: List[UUID]
    topic: str
    rounds: int = 3

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/send")
async def send_message(agent_id: UUID, content: str):
    try:
        orch = LLMOrchestrator()
        result = orch.process_message(str(agent_id), content)
        return {"status": "ok", "message": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/brainstorm")
async def brainstorm(req: BrainstormRequest):
    try:
        orch = LLMOrchestrator()
        messages = orch.process_message("brainstorm", req.topic)
        return {"status": "ok", "messages": [messages]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
