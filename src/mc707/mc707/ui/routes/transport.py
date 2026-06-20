"""Transport routes — play / stop / tempo / pause."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..models import OkResponse, TempoRequest, TempoResponse
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/transport", tags=["transport"])


@router.post("/play", response_model=OkResponse)
def play(state: BackendState = Depends(get_state)) -> OkResponse:
    """Start the sequencer."""
    ok = state.mc707.transport.play()
    if ok:
        state.bus.publish("transport_changed", playing=True)
    return OkResponse(ok=ok)


@router.post("/stop", response_model=OkResponse)
def stop(state: BackendState = Depends(get_state)) -> OkResponse:
    """Stop the sequencer."""
    ok = state.mc707.transport.stop()
    if ok:
        state.bus.publish("transport_changed", playing=False)
    return OkResponse(ok=ok)


@router.post("/pause", response_model=OkResponse)
def pause(state: BackendState = Depends(get_state)) -> OkResponse:
    """Pause the sequencer."""
    ok = state.mc707.transport.pause()
    return OkResponse(ok=ok)


@router.post("/tempo", response_model=TempoResponse)
def set_tempo(
    req: TempoRequest,
    state: BackendState = Depends(get_state),
) -> TempoResponse:
    """Set the sequencer tempo (BPM)."""
    state.mc707.transport.tempo(req.bpm)
    state.bus.publish("transport_changed", tempo=req.bpm)
    return TempoResponse(bpm=req.bpm)