"""MIDI I/O layer.

Wraps :mod:`mido` for send-only access to MIDI output ports. In mock
mode every outgoing message is appended to an in-memory log instead of
being sent to a hardware port. Provides the low-level DT1/RQ1 framing
for Roland SysEx communication.
"""

from .midi import MIDIIO
from .sysex import SysExController

__all__ = ["MIDIIO", "SysExController"]