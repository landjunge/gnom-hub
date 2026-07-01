"""Backwards-compatible shim for gnom-hub code paths.

The MC-707 library has moved to a standalone-installable package at
``mc707`` (see ``src/mc707/``). This module re-exports the public API
so existing gnom-hub code that imports from
``gnom_hub.infrastructure.audio.mc707`` continues to work without
changes.

Both import paths resolve to the same objects::

    from gnom_hub.infrastructure.audio.mc707 import MC707  # via this shim
    from mc707 import MC707                                # direct

New code should prefer ``from mc707 import ...``.
"""

from __future__ import annotations

from mc707 import (
    MC707,
    MIDIIO,
    PARAM_ADDRESSES,
    AmpEnvelope,
    ArpeggiatorController,
    ClipController,
    EffectsController,
    FilterEnvelope,
    FilterParams,
    FilterType,
    LFOParams,
    LfoTarget,
    OscillatorParams,
    PatternController,
    SceneController,
    Sound,
    SoundCategory,
    SoundController,
    SoundEditor,
    SoundRegistry,
    SoundStore,
    StatusController,
    SysExController,
    TransportController,
    Waveform,
)

__version__ = "0.3.0"
__all__ = [
    "MIDIIO",
    "PARAM_ADDRESSES",
    "AmpEnvelope",
    "ArpeggiatorController",
    "ClipController",
    "EffectsController",
    "FilterEnvelope",
    "FilterParams",
    "FilterType",
    "LFOParams",
    "LfoTarget",
    "MC707",
    "OscillatorParams",
    "PatternController",
    "SceneController",
    "Sound",
    "SoundCategory",
    "SoundController",
    "SoundEditor",
    "SoundRegistry",
    "SoundStore",
    "StatusController",
    "SysExController",
    "TransportController",
    "Waveform",
]