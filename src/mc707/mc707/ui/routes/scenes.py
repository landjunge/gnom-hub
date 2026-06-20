"""Scene routes — select / next / previous / current."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import OkResponse, SceneSelectRequest
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/scenes", tags=["scenes"])


@router.post("/select", response_model=OkResponse)
def select(
    req: SceneSelectRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Select a scene by index."""
    state.mc707.scenes.select(req.index)
    state.bus.publish("scene_changed", index=req.index)
    return OkResponse(ok=True)


@router.post("/next", response_model=OkResponse)
def next_scene(state: BackendState = Depends(get_state)) -> OkResponse:
    """Advance to the next scene."""
    state.mc707.scenes.next()
    new_index = state.mc707.scenes.current()
    state.bus.publish("scene_changed", index=new_index)
    return OkResponse(ok=True, data={"index": new_index})


@router.post("/previous", response_model=OkResponse)
def previous_scene(state: BackendState = Depends(get_state)) -> OkResponse:
    """Go back to the previous scene."""
    state.mc707.scenes.previous()
    new_index = state.mc707.scenes.current()
    state.bus.publish("scene_changed", index=new_index)
    return OkResponse(ok=True, data={"index": new_index})


@router.get("/current", response_model=OkResponse)
def current(state: BackendState = Depends(get_state)) -> OkResponse:
    """Return the currently selected scene index."""
    return OkResponse(ok=True, data={"index": state.mc707.scenes.current()})