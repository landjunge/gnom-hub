"""mc707 — Roland MC-707 Groovebox MIDI controller library.

A pure-Python library for controlling the Roland MC-707 Groovebox over
MIDI. Provides high-level controllers for transport, scenes, clips,
sounds, patterns, effects, arpeggiator, and SysEx communication.

The library runs in **mock mode** by default — every outgoing MIDI
message is captured in an in-memory log so the whole API is exercisable
without physical hardware. Pass ``port_name="..."`` and ``mock=False``
to open a real MIDI port.

Quick start::

    from mc707 import MC707, Sound

    m = MC707()                                # mock mode
    m.transport.play()
    m.clips.trigger(1, 1)

    sound = Sound(name="Bass-01", category="bass")
    m.sound_editor.apply(sound)                # write to device
    m.sound_store.save(sound)                  # persist to ~/.mc707/sounds/

Sub-package layout::

    mc707/
    ├── facade.py           # MC707 façade
    ├── io/                 # MIDI + SysEx
    │   ├── midi.py
    │   └── sysex.py
    ├── models/             # Pydantic data models
    │   └── sound.py
    ├── control/            # High-level controllers
    │   ├── transport.py
    │   ├── scenes.py
    │   ├── clips.py
    │   ├── sounds.py       # Bank-select loader (legacy SoundController)
    │   ├── sound_editor.py # SysEx DT1 tone editor (Track 1+)
    │   ├── patterns.py
    │   ├── effects.py
    │   ├── arpeggiator.py
    │   └── status.py
    ├── persistence/        # Disk-backed state
    │   └── sound_store.py
    └── registry/           # In-memory named caches
        └── sound_registry.py

Every MC-707-specific constant that is **not** verified against the
official MIDI Implementation Chart is annotated with
``EDUCATED GUESS`` / ``TEMPLATE - NEEDS VERIFICATION`` in the relevant
module docstring. Treat all bank-layout, SysEx-address, and tone-edit
values as unverified until the spec is filled in.
"""

from __future__ import annotations

from .control.arpeggiator import ArpeggiatorController
from .control.clips import ClipController
from .control.effects import EffectsController
from .control.patterns import PatternController
from .control.scenes import SceneController
from .control.sound_editor import PARAM_ADDRESSES, SoundEditor
from .control.sounds import SoundController
from .control.status import StatusController
from .control.transport import TransportController
from .facade import MC707
from .io.midi import MIDIIO
from .io.sysex import SysExController
from .models.sound import (
    AmpEnvelope,
    FilterEnvelope,
    FilterParams,
    FilterType,
    LFOParams,
    LfoTarget,
    OscillatorParams,
    Sound,
    SoundCategory,
    Waveform,
)
from .persistence.sound_store import SoundStore
from .registry.sound_registry import SoundRegistry

__version__ = "0.3.0"

__all__ = [
    # Façade + IO
    "MC707",
    "MIDIIO",
    "SysExController",
    # Controllers
    "TransportController",
    "SceneController",
    "ClipController",
    "SoundController",
    "SoundEditor",
    "PatternController",
    "EffectsController",
    "ArpeggiatorController",
    "StatusController",
    # Sound models
    "Sound",
    "OscillatorParams",
    "FilterParams",
    "AmpEnvelope",
    "FilterEnvelope",
    "LFOParams",
    "FilterType",
    "LfoTarget",
    "SoundCategory",
    "Waveform",
    # Persistence / registry
    "SoundStore",
    "SoundRegistry",
    # Constants
    "PARAM_ADDRESSES",
]