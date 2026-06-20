"""Pattern routes — step sequencer programming."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import OkResponse, PatternRequest
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.post("/program", response_model=OkResponse)
def program(
    req: PatternRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Program a pattern on a track.

    ``req.steps`` accepts a mix of:

    * ``int`` — a note (velocity=100, gate=64, duration=full)
    * ``{"note": int, "velocity"?: int, "gate"?: int}`` — explicit step

    The underlying controller normalises both shapes.
    """
    ok = state.mc707.patterns.program(req.track, req.steps)
    return OkResponse(ok=ok)