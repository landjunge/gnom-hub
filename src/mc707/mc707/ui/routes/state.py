"""State route — full backend snapshot, used by the UI on connect."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import StateResponse
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("", response_model=StateResponse)
def get_state_snapshot(
    state: BackendState = Depends(get_state),
) -> StateResponse:
    """Return the full backend state — registry, cached params, disk listing.

    The UI calls this once on connect to populate its initial view
    without having to make dozens of follow-up requests.
    """
    return StateResponse(
        is_mock=state.is_mock,
        sound_dir=str(state.sound_store.base_dir),
        registry_size=len(state.sound_registry),
        registry_names=state.sound_registry.list(),
        known_params=sorted(state.sound_editor.known_params()),
        cached_params=state.sound_editor.cached_params(),
        disk_sounds=state.sound_store.list(),
    )