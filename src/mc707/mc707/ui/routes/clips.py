"""Clip routes — trigger / stop / track mixer."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import ClipTriggerRequest, OkResponse, TrackMixerRequest
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.post("/trigger", response_model=OkResponse)
def trigger(
    req: ClipTriggerRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Trigger a clip on a track."""
    state.mc707.clips.trigger(req.track, req.clip)
    state.bus.publish(
        "clip_triggered", track=req.track, clip=req.clip
    )
    return OkResponse(ok=True)


@router.post("/{track}/stop", response_model=OkResponse)
def stop(
    track: int,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Stop all clips on a track."""
    state.mc707.clips.stop(track)
    return OkResponse(ok=True)


@router.post("/stop-all", response_model=OkResponse)
def stop_all(state: BackendState = Depends(get_state)) -> OkResponse:
    """Stop all clips on every track."""
    state.mc707.clips.stop_all()
    return OkResponse(ok=True)


@router.post("/{track}/mute", response_model=OkResponse)
def mute(
    track: int,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Toggle mute on a track."""
    state.mc707.clips.track_mute(track)
    return OkResponse(ok=True)


@router.post("/{track}/solo", response_model=OkResponse)
def solo(
    track: int,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Toggle solo on a track."""
    state.mc707.clips.track_solo(track)
    return OkResponse(ok=True)


@router.post("/{track}/volume", response_model=OkResponse)
def volume(
    track: int,
    req: TrackMixerRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set the track volume (0..127)."""
    if req.value is None:
        return OkResponse(ok=False, data={"error": "value is required"})
    state.mc707.clips.track_volume(track, req.value)
    return OkResponse(ok=True)


@router.post("/{track}/pan", response_model=OkResponse)
def pan(
    track: int,
    req: TrackMixerRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set the track pan (0..127)."""
    if req.value is None:
        return OkResponse(ok=False, data={"error": "value is required"})
    state.mc707.clips.track_pan(track, req.value)
    return OkResponse(ok=True)