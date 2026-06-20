"""Status routes — read-back of current device state.

Status is **cache-only** for now (the underlying
:class:`StatusController` returns mock defaults). A real RQ1 response
parser is on the roadmap (TODO).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import OkResponse, StatusResponse
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("", response_model=StatusResponse)
def get_status(state: BackendState = Depends(get_state)) -> StatusResponse:
    """Return the current scene / tempo / per-track tone cache."""
    scene = state.mc707.status.current_scene()
    tempo = state.mc707.status.current_tempo()
    tones = {
        track: state.mc707.status.current_tone(track)
        for track in range(1, 9)
    }
    return StatusResponse(scene=scene, tempo=tempo, tones=tones)


@router.get("/scene", response_model=OkResponse)
def current_scene(state: BackendState = Depends(get_state)) -> OkResponse:
    return OkResponse(ok=True, data={"scene": state.mc707.status.current_scene()})


@router.get("/tempo", response_model=OkResponse)
def current_tempo(state: BackendState = Depends(get_state)) -> OkResponse:
    return OkResponse(ok=True, data={"tempo": state.mc707.status.current_tempo()})


@router.get("/tone/{track}", response_model=OkResponse)
def current_tone(
    track: int,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    return OkResponse(
        ok=True, data={"track": track, "tone": state.mc707.status.current_tone(track)}
    )