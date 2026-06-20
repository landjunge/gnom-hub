"""High-level MC-707 controllers.

Each controller wraps a slice of the MC-707's MIDI surface — transport
(play/stop/clock), scenes, clips, sounds (legacy loader), tone editing
(via SysEx DT1), patterns, effects, arpeggiator, and status queries.
"""

from .arpeggiator import ArpeggiatorController
from .clips import ClipController
from .effects import EffectsController
from .patterns import PatternController
from .scenes import SceneController
from .sound_editor import PARAM_ADDRESSES, SoundEditor
from .sounds import SoundController
from .status import StatusController
from .transport import TransportController

__all__ = [
    "ArpeggiatorController",
    "ClipController",
    "EffectsController",
    "PARAM_ADDRESSES",
    "PatternController",
    "SceneController",
    "SoundController",
    "SoundEditor",
    "StatusController",
    "TransportController",
]