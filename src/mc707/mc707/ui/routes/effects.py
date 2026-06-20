"""Effects routes — filter / envelope / master sends / MFX slot parameters."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import EffectValueRequest, FxParamRequest, OkResponse
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/effects", tags=["effects"])


@router.post("/cutoff", response_model=OkResponse)
def cutoff(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set the master cutoff (filter)."""
    state.mc707.effects.cutoff(req.value)
    return OkResponse(ok=True, data={"value": req.value})


@router.post("/resonance", response_model=OkResponse)
def resonance(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set the master resonance."""
    state.mc707.effects.resonance(req.value)
    return OkResponse(ok=True, data={"value": req.value})


@router.post("/attack", response_model=OkResponse)
def attack(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set the amp envelope attack."""
    state.mc707.effects.attack(req.value)
    return OkResponse(ok=True)


@router.post("/decay", response_model=OkResponse)
def decay(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.decay(req.value)
    return OkResponse(ok=True)


@router.post("/sustain", response_model=OkResponse)
def sustain(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.sustain(req.value)
    return OkResponse(ok=True)


@router.post("/release", response_model=OkResponse)
def release(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.release(req.value)
    return OkResponse(ok=True)


@router.post("/reverb", response_model=OkResponse)
def reverb(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.reverb(req.value)
    return OkResponse(ok=True)


@router.post("/chorus", response_model=OkResponse)
def chorus(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.chorus(req.value)
    return OkResponse(ok=True)


@router.post("/delay", response_model=OkResponse)
def delay(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.delay(req.value)
    return OkResponse(ok=True)


@router.post("/distortion", response_model=OkResponse)
def distortion(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.distortion(req.value)
    return OkResponse(ok=True)


@router.post("/filter-type", response_model=OkResponse)
def filter_type(
    req: EffectValueRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.effects.filter_type(req.value)
    return OkResponse(ok=True)


@router.post("/fx-param", response_model=OkResponse)
def set_fx_param(
    req: FxParamRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Set a single MFX slot parameter (track, slot, param, value)."""
    state.mc707.effects.set_fx(req.track, req.slot, req.param, req.value)
    return OkResponse(ok=True)