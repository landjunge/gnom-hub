"""Arpeggiator routes — on/off + rate / gate / style / octave."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import (
    ArpGateRequest,
    ArpOctaveRequest,
    ArpRateRequest,
    ArpStyleRequest,
    OkResponse,
)
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/arpeggiator", tags=["arpeggiator"])


@router.post("/on", response_model=OkResponse)
def on(state: BackendState = Depends(get_state)) -> OkResponse:
    """Enable the arpeggiator."""
    state.mc707.arpeggiator.on()
    return OkResponse(ok=True, data={"on": True})


@router.post("/off", response_model=OkResponse)
def off(state: BackendState = Depends(get_state)) -> OkResponse:
    """Disable the arpeggiator."""
    state.mc707.arpeggiator.off()
    return OkResponse(ok=True, data={"on": False})


@router.post("/rate", response_model=OkResponse)
def rate(
    req: ArpRateRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.arpeggiator.rate(req.rate)
    return OkResponse(ok=True)


@router.post("/gate", response_model=OkResponse)
def gate(
    req: ArpGateRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.arpeggiator.gate(req.gate)
    return OkResponse(ok=True)


@router.post("/style", response_model=OkResponse)
def style(
    req: ArpStyleRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.arpeggiator.style(req.style)
    return OkResponse(ok=True)


@router.post("/octave", response_model=OkResponse)
def octave(
    req: ArpOctaveRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    state.mc707.arpeggiator.octave(req.octave)
    return OkResponse(ok=True)