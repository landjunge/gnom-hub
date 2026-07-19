"""Hub job claim API — agents pull work without multi-process BEGIN IMMEDIATE."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from gnom_hub.queue import queue_mode
from gnom_hub.queue.claim_service import ack, claim_next, nack

router = APIRouter(prefix="/api/queue", tags=["queue"])


class ClaimRequest(BaseModel):
    agent: str
    timeout: float = Field(default=0.5, ge=0.05, le=5.0)


class AckRequest(BaseModel):
    msg_id: int
    agent: str = ""


class NackRequest(BaseModel):
    msg_id: int
    agent: str = ""
    reason: str = ""


@router.get("/backend")
def queue_backend():
    return {"mode": queue_mode(), "claim": "hub" if queue_mode() == "hub" else "sqlite"}


@router.post("/claim")
def claim_job(body: ClaimRequest):
    msg = claim_next(body.agent, timeout=body.timeout)
    if not msg:
        return {"status": "empty", "message": None}
    return {"status": "ok", "message": msg}


@router.post("/ack")
def ack_job(body: AckRequest):
    ack(body.msg_id)
    return {"status": "acked", "msg_id": body.msg_id}


@router.post("/nack")
def nack_job(body: NackRequest):
    nack(body.msg_id, body.reason)
    return {"status": "nacked", "msg_id": body.msg_id}
