"""DEAD / NOT MOUNTED — do not use for product chat.

Live chat API is ``chat_legacy``:
  POST /api/chat, GET /api/chat, GET /api/chat/stream
(see ``api/endpoints/router.py`` include list).

This module is an old brainstorm/orchestrator stub (prefix ``/chat``) and is
intentionally not registered. Kept only until S4 cleanup removes callers/tests.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gnom_hub.infrastructure.router.llm_orchestrator import LLMOrchestrator


class BrainstormRequest(BaseModel):
    agent_ids: list[UUID]
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
        raise HTTPException(status_code=400, detail=str(e)) from e

@router.post("/brainstorm")
async def brainstorm(req: BrainstormRequest):
    try:
        orch = LLMOrchestrator()
        messages = orch.process_message("brainstorm", req.topic)
        return {"status": "ok", "messages": [messages]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
