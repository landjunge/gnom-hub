"""Sound routes — CRUD + persistence + live param editing.

This is the largest router because Sounds are the most featureful
entity in the system. The router covers:

* Registry CRUD (in-memory)
* Disk persistence (SoundStore)
* Legacy bank-select loader (``sounds``)
* Live parameter editing via :class:`SoundEditor`
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from ...control.sound_editor import PARAM_ADDRESSES
from ...models.sound import Sound
from ..events import (
    EVT_PARAM_CHANGED,
    EVT_SOUND_LOADED,
    EVT_SOUND_REGISTERED,
    EVT_SOUND_REMOVED,
    EVT_SOUND_SAVED,
)
from ..models import (
    ApplyRequest,
    OkResponse,
    ParamGetResponse,
    ParamSetRequest,
    ParamsListResponse,
    SoundCreateRequest,
    SoundListResponse,
)
from ..state import BackendState, get_state

router = APIRouter(prefix="/api/sounds", tags=["sounds"])


# ===========================================================================
# 1. Registry CRUD
# ===========================================================================


@router.get("", response_model=SoundListResponse)
def list_sounds(state: BackendState = Depends(get_state)) -> SoundListResponse:
    """List all sounds in the in-memory registry."""
    return SoundListResponse(names=state.sound_registry.list())


@router.post("", response_model=OkResponse)
def create_sound(
    req: SoundCreateRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Create or replace a Sound in the registry."""
    state.sound_registry.register(req.sound)
    state.bus.publish(
        EVT_SOUND_REGISTERED, name=req.sound.name, category=req.sound.category
    )
    return OkResponse(ok=True, data={"name": req.sound.name})


@router.get("/{name}", response_model=Sound)
def get_sound(
    name: str,
    state: BackendState = Depends(get_state),
) -> Sound:
    """Retrieve a Sound by name."""
    sound = state.sound_registry.get(name)
    if sound is None:
        raise HTTPException(status_code=404, detail=f"Sound {name!r} not found")
    return sound


@router.delete("/{name}", response_model=OkResponse)
def delete_sound(
    name: str,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Remove a Sound from the registry."""
    removed = state.sound_registry.remove(name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Sound {name!r} not found")
    state.bus.publish(EVT_SOUND_REMOVED, name=name)
    return OkResponse(ok=True, data={"name": name})


# ===========================================================================
# 2. Live parameter editing (SoundEditor)
# ===========================================================================


@router.get("/{name}/params", response_model=ParamsListResponse)
def list_params(
    name: str,
    state: BackendState = Depends(get_state),
) -> ParamsListResponse:
    """List all parameters currently cached on the SoundEditor.

    Note: this is the **editor cache**, not the live device state.
    See TODO (Track 4+) — a real RQ1 read-back is still pending.
    """
    return ParamsListResponse(params=state.sound_editor.cached_params())


@router.get("/{name}/params/{param_name}", response_model=ParamGetResponse)
def get_param(
    name: str,
    param_name: str,
    state: BackendState = Depends(get_state),
) -> ParamGetResponse:
    """Read a single parameter from the editor cache.

    Returns ``value=None`` if the parameter has not been written yet
    in this session. The UI must label cached values accordingly.
    """
    if param_name not in PARAM_ADDRESSES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown parameter {param_name!r}",
        )
    return ParamGetResponse(
        name=param_name, value=state.sound_editor.get_param(param_name)
    )


@router.post("/{name}/params/{param_name}", response_model=OkResponse)
def set_param(
    name: str,
    param_name: str,
    req: ParamSetRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Write a single parameter to the device via SysEx DT1."""
    if param_name not in PARAM_ADDRESSES:
        raise HTTPException(
            status_code=404, detail=f"Unknown parameter {param_name!r}"
        )
    ok = state.sound_editor.set_param(param_name, req.value)
    if ok:
        state.bus.publish(
            EVT_PARAM_CHANGED, sound=name, param=param_name, value=req.value
        )
    return OkResponse(ok=ok, data={"name": param_name, "value": req.value})


@router.post("/{name}/apply", response_model=OkResponse)
def apply_sound(
    name: str,
    req: ApplyRequest,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Push parameters from a Sound to the device via DT1.

    If ``req.params`` is ``None``, every parameter from the Sound is
    written; otherwise only the listed names. The Sound must be in the
    registry under *name* — the request body must match.
    """
    registry_sound = state.sound_registry.get(name)
    if registry_sound is None:
        raise HTTPException(
            status_code=404, detail=f"Sound {name!r} not in registry"
        )
    if req.params is None:
        ok = state.sound_editor.apply(registry_sound)
    else:
        ok = state.sound_editor.apply_partial(registry_sound, req.params)
    if ok:
        state.bus.publish(EVT_PARAM_CHANGED, sound=name, applied="all")
    return OkResponse(ok=ok)


# ===========================================================================
# 3. Disk persistence (SoundStore)
# ===========================================================================


@router.get("/_disk/list", response_model=SoundListResponse)
def list_disk_sounds(
    state: BackendState = Depends(get_state),
) -> SoundListResponse:
    """List all sounds persisted on disk."""
    return SoundListResponse(names=state.sound_store.list())


@router.post("/_disk/{name}/save", response_model=OkResponse)
def save_to_disk(
    name: str,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Persist the registry Sound *name* to the SoundStore."""
    sound = state.sound_registry.get(name)
    if sound is None:
        raise HTTPException(
            status_code=404, detail=f"Sound {name!r} not in registry"
        )
    path = state.sound_store.save(sound)
    state.bus.publish(EVT_SOUND_SAVED, name=name, path=str(path))
    return OkResponse(ok=True, data={"path": str(path)})


@router.post("/_disk/{name}/load", response_model=OkResponse)
def load_from_disk(
    name: str,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Load a Sound from the SoundStore into the registry."""
    try:
        sound = state.sound_store.load(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    state.sound_registry.register(sound)
    state.bus.publish(EVT_SOUND_LOADED, name=name)
    return OkResponse(ok=True, data={"name": sound.name})


# ===========================================================================
# 4. Legacy bank-select loader (SoundController)
# ===========================================================================


@router.post("/_loader/tone", response_model=OkResponse)
def load_tone(
    track: int,
    tone_number: int,
    bank_msb: int = 0,
    bank_lsb: int = 0,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Load a Tone onto a track via bank-select + program-change."""
    ok = state.mc707.sounds.load_tone(track, tone_number, bank_msb, bank_lsb)
    return OkResponse(ok=ok)


@router.post("/_loader/drum-kit", response_model=OkResponse)
def load_drum_kit(
    track: int,
    kit_number: int,
    user: bool = False,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Load a Drum Kit onto a track."""
    ok = state.mc707.sounds.load_drum_kit(track, kit_number, user=user)
    return OkResponse(ok=ok)


@router.post("/_loader/instrument", response_model=OkResponse)
def load_instrument(
    track: int,
    tone_number: int,
    user: bool = False,
    state: BackendState = Depends(get_state),
) -> OkResponse:
    """Load an Instrument onto a track."""
    ok = state.mc707.sounds.load_instrument(track, tone_number, user=user)
    return OkResponse(ok=ok)