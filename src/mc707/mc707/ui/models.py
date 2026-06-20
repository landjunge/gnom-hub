"""Pydantic models for the WebUI request/response payloads.

These models give the OpenAPI schema type-safety for every endpoint and
let the frontend generate TypeScript types directly from
``/openapi.json``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.sound import Sound


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------


class OkResponse(BaseModel):
    """Standard success response — just an ``ok`` flag and optional data."""

    ok: bool = True
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    ok: bool = False
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class PlayResponse(BaseModel):
    ok: bool
    playing: bool


class TempoRequest(BaseModel):
    """Set the sequencer tempo (BPM)."""

    bpm: float = Field(..., ge=20, le=300, description="Beats per minute")


class TempoResponse(BaseModel):
    bpm: float


# ---------------------------------------------------------------------------
# Scenes / Clips
# ---------------------------------------------------------------------------


class SceneSelectRequest(BaseModel):
    index: int = Field(..., ge=0, le=127)


class ClipTriggerRequest(BaseModel):
    track: int = Field(..., ge=1, le=8)
    clip: int = Field(..., ge=1, le=16)


class TrackMixerRequest(BaseModel):
    """Per-track mute / solo / volume / pan request."""

    track: int = Field(..., ge=1, le=8)
    value: Optional[int] = None
    """For volume / pan: 0..127. For mute/solo: ignored (toggle)."""


# ---------------------------------------------------------------------------
# Sounds (CRUD)
# ---------------------------------------------------------------------------


class SoundCreateRequest(BaseModel):
    """Create or replace a Sound by name."""

    sound: Sound


class SoundUpdateRequest(BaseModel):
    """Update an existing Sound (partial)."""

    updates: Dict[str, Any]


class SoundListResponse(BaseModel):
    names: List[str]


# ---------------------------------------------------------------------------
# Sound parameters (live editing via SoundEditor)
# ---------------------------------------------------------------------------


class ParamSetRequest(BaseModel):
    """Set a single Tone parameter via SysEx DT1.

    Note: the parameter name is taken from the URL path
    (``/api/sounds/{name}/params/{param_name}``), NOT from the body. The
    body only carries the new value. ``name`` is kept as an optional
    field for backward compatibility with old clients that sent it.
    """

    name: Optional[str] = None
    value: int = Field(..., ge=0, le=127)


class ParamGetResponse(BaseModel):
    name: str
    value: Optional[int]
    cached: bool = True


class ParamsListResponse(BaseModel):
    params: Dict[str, int]


class ApplyRequest(BaseModel):
    """Apply a list of parameter names from a Sound.

    Note: the source Sound is taken from the registry under the URL-path
    ``name`` segment, NOT from the body. The body only carries the
    optional ``params`` allow-list. ``sound`` is kept as an optional
    field for backward compatibility with old clients that sent it.
    """

    sound: Optional[Sound] = None
    params: Optional[List[str]] = None
    """If None, apply every parameter. If a list, apply only those."""


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


class EffectValueRequest(BaseModel):
    value: int = Field(..., ge=0, le=127)
    track: Optional[int] = Field(None, ge=1, le=8)


class FxParamRequest(BaseModel):
    track: int = Field(..., ge=1, le=8)
    slot: int = Field(..., ge=0, le=3)
    param: int = Field(..., ge=0, le=127)
    value: int = Field(..., ge=0, le=127)


# ---------------------------------------------------------------------------
# Arpeggiator
# ---------------------------------------------------------------------------


class ArpRateRequest(BaseModel):
    rate: int = Field(..., ge=0, le=127)


class ArpGateRequest(BaseModel):
    gate: int = Field(..., ge=0, le=127)


class ArpStyleRequest(BaseModel):
    """Arpeggiator playing style.

    0 = Up, 1 = Down, 2 = UpDown, 3 = Random. These four match the
    :class:`ArpController` validation; the wider ``0..15`` range was a
    placeholder while the MIDI spec was TBD.
    """

    style: int = Field(..., ge=0, le=3)


class ArpOctaveRequest(BaseModel):
    """Number of arpeggiator octaves.

    ``0..3`` matches the :class:`ArpController` validation
    (``_validate_octave``); the wider ``1..4`` was a placeholder.
    """

    octave: int = Field(..., ge=0, le=3)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


class PatternStep(BaseModel):
    """A single sequencer step."""

    note: int = Field(..., ge=0, le=127)
    velocity: int = Field(100, ge=1, le=127)
    gate: int = Field(64, ge=1, le=127)


class PatternRequest(BaseModel):
    """Program a pattern on a track."""

    track: int = Field(..., ge=1, le=8)
    steps: List[Any]  # List[int] or List[PatternStep]
    """Each step is either an int (note, velocity=100, gate=64) or a
    PatternStep dict."""


# ---------------------------------------------------------------------------
# SysEx
# ---------------------------------------------------------------------------


class Dt1Request(BaseModel):
    address: List[int] = Field(..., min_length=1, max_length=4)
    payload: List[int] = Field(..., min_length=1, max_length=4)


class Rq1Request(BaseModel):
    address: List[int] = Field(..., min_length=1, max_length=4)
    size: int = Field(..., ge=1, le=16384)


# ---------------------------------------------------------------------------
# Status / State dump
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    scene: Optional[int]
    tempo: Optional[float]
    tones: Dict[int, int] = Field(default_factory=dict)


class StateResponse(BaseModel):
    """Full backend state snapshot — used by the UI on connect."""

    is_mock: bool
    sound_dir: str
    registry_size: int
    registry_names: List[str]
    known_params: List[str]
    cached_params: Dict[str, int]
    disk_sounds: List[str]


# ---------------------------------------------------------------------------
# WebSocket protocol
# ---------------------------------------------------------------------------


class WsEvent(BaseModel):
    """Server-pushed WebSocket event."""

    model_config = ConfigDict(extra="allow")

    type: str
    """Event type — see ``EventBus.publish`` for the catalogue."""
    data: Dict[str, Any] = Field(default_factory=dict)


class WsClientMessage(BaseModel):
    """Client → server message (subscribe / unsubscribe / ping)."""

    action: str = Field(..., pattern="^(subscribe|unsubscribe|ping)$")
    events: Optional[List[str]] = None


__all__ = [
    "ApplyRequest",
    "ArpGateRequest",
    "ArpOctaveRequest",
    "ArpRateRequest",
    "ArpStyleRequest",
    "ClipTriggerRequest",
    "Dt1Request",
    "EffectValueRequest",
    "ErrorResponse",
    "FxParamRequest",
    "OkResponse",
    "ParamGetResponse",
    "ParamSetRequest",
    "ParamsListResponse",
    "PatternRequest",
    "PatternStep",
    "PlayResponse",
    "Rq1Request",
    "SceneSelectRequest",
    "SoundCreateRequest",
    "SoundListResponse",
    "SoundUpdateRequest",
    "StateResponse",
    "StatusResponse",
    "TempoRequest",
    "TempoResponse",
    "TrackMixerRequest",
    "WsClientMessage",
    "WsEvent",
]