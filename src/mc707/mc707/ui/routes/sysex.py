"""SysEx routes — low-level DT1 / RQ1 dispatch + high-level helpers."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models import Dt1Request, OkResponse, Rq1Request
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/sysex", tags=["sysex"])


@router.post("/dt1", response_model=OkResponse)
def send_dt1(
    req: Dt1Request,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Send a raw DT1 (parameter write) SysEx message."""
    ok = state.mc707.sysex.send_dt1(tuple(req.address), req.payload)
    return OkResponse(ok=ok)


@router.post("/rq1", response_model=OkResponse)
def send_rq1(
    req: Rq1Request,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Send a raw RQ1 (parameter request / dump) SysEx message."""
    ok = state.mc707.sysex.send_rq1(tuple(req.address), req.size)
    return OkResponse(ok=ok)