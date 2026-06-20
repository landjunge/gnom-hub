"""Clip and track-mixer controller for the MC-707.

A *clip* on the MC-707 is a single pattern instance on a track. The
controller exposes:

  * clip trigger / stop
  * per-track mute / solo
  * per-track volume / pan

TEMPLATE - NEEDS VERIFICATION
-----------------------------
The MC-707 maps tracks to MIDI channels 9–16 (track 1 = ch 9, ...
track 8 = ch 16). The task spec originally proposed channels 10–17
(``track + 9``) but that pushes track 8 onto MIDI channel 17 which is
out of range for a 16-channel MIDI bus — kept here as a
TEMPLETE-guess to be re-confirmed against the hardware manual.

Clip triggering is dispatched as a Program Change on the track channel
where PC value ``clip - 1`` selects the clip slot. This matches the
Roland convention used on the MC-101 and a few other grooveboxes, but
the MC-707 manual should be consulted to confirm.

Mixer CCs follow the standard MIDI assignment (7 = volume, 10 = pan) and
use the Roland-specific mute/solo CCs (94 / 95). All values need to be
checked against hardware.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — type hint only
    from ..io.midi import MIDIIO

logger = logging.getLogger(__name__)


class ClipController:
    """High-level clip and track-mix operations for the MC-707.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.

    Notes
    -----
    Track and clip numbers use the **user-facing 1-based** indexing:
    tracks ``1``–``8`` map to MIDI channels ``9``–``16`` (offset
    ``track + 8``), and clip slots ``1``–``16`` map to Program Change
    values ``0``–``15`` (offset ``clip - 1``).
    """

    # ------------------------------------------------------------------
    # Track / channel mapping
    # ------------------------------------------------------------------

    # First track channel on the MC-707. Track N maps to MIDI channel
    # ``TRACK_CHANNEL_OFFSET + N`` (1-based). Offset = 8 keeps all 8
    # tracks inside the valid MIDI 1–16 channel range; the task spec's
    # ``track + 9`` formula was rejected because track 8 would land on
    # the non-existent MIDI channel 17.
    # TEMPLATE - NEEDS VERIFICATION — confirm against hardware.
    TRACK_CHANNEL_OFFSET = 8
    MIN_TRACK = 1
    MAX_TRACK = 8

    # ------------------------------------------------------------------
    # Clip slot mapping
    # ------------------------------------------------------------------

    MIN_CLIP = 1
    MAX_CLIP = 16

    # ------------------------------------------------------------------
    # Mixer CCs (Roland convention)
    # ------------------------------------------------------------------

    CC_MUTE = 94       # TEMPLATE - NEEDS VERIFICATION
    CC_SOLO = 95       # TEMPLATE - NEEDS VERIFICATION
    CC_VOLUME = 7      # standard MIDI channel volume
    CC_PAN = 10        # standard MIDI channel pan
    CC_ALL_NOTES_OFF = 123  # standard MIDI "All Notes Off"

    # MIDI velocity range for clip triggering.
    MIN_VELOCITY = 1
    MAX_VELOCITY = 127

    def __init__(self, midi_io: "MIDIIO") -> None:
        self._midi = midi_io

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_int(name: str, value, low: int, high: int) -> int:
        """Validate that ``value`` is an int in ``[low, high]``.

        Raises :class:`ValueError` with a clear message otherwise.
        """
        # Reject bools explicitly — bool is a subclass of int in Python
        # but treating ``True`` as ``1`` here is almost always a bug.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{name} must be an int in {low}..{high}, "
                f"got {type(value).__name__}"
            )
        if value < low or value > high:
            raise ValueError(
                f"{name} must be between {low} and {high} (inclusive), got {value}"
            )
        return value

    def _track_channel(self, track: int) -> int:
        """Validate ``track`` and return the corresponding MIDI channel."""
        self._validate_int("track", track, self.MIN_TRACK, self.MAX_TRACK)
        return track + self.TRACK_CHANNEL_OFFSET

    # ------------------------------------------------------------------
    # Clip trigger / stop
    # ------------------------------------------------------------------

    def trigger(self, track: int, clip: int, velocity: int = 100) -> bool:
        """Trigger a clip on a given track.

        Parameters
        ----------
        track:
            Track number, ``1``–``8``.
        clip:
            Clip slot, ``1``–``16``.
        velocity:
            Trigger velocity, ``1``–``127``. Default ``100``.

        Returns
        -------
        bool
            ``True`` if the Program Change was dispatched successfully.

        Notes
        -----
        TEMPLATE - NEEDS VERIFICATION
        Sends Program Change on ``track + 8`` with value ``clip - 1``.
        On the MC-707 the actual clip-launch protocol may be a Note-On
        on a per-track base note, or a SysEx DT1 at the clip-launch
        address. The Program Change path matches Roland's MC-series
        groovebox convention and is kept as the primary path because
        it round-trips cleanly through mock mode.
        """
        channel = self._track_channel(track)
        self._validate_int("clip", clip, self.MIN_CLIP, self.MAX_CLIP)
        self._validate_int("velocity", velocity, self.MIN_VELOCITY, self.MAX_VELOCITY)

        program = clip - 1
        ok = self._midi.send_program_change(channel, program)
        if not ok:
            logger.warning(
                "Failed to trigger clip %d on track %d (ch=%d, pc=%d).",
                clip, track, channel, program,
            )
        return ok

    def stop(self, track: int) -> bool:
        """Stop playback of a specific track (All Notes Off).

        Parameters
        ----------
        track:
            Track number, ``1``–``8``.

        Returns
        -------
        bool
            ``True`` if the All-Notes-Off CC was dispatched successfully.
        """
        channel = self._track_channel(track)
        ok = self._midi.send_cc(channel, self.CC_ALL_NOTES_OFF, 0)
        if not ok:
            logger.warning(
                "Failed to stop track %d (ch=%d, All Notes Off).",
                track, channel,
            )
        return ok

    def stop_all(self) -> None:
        """Stop every track (sends All Notes Off to all 8 track channels)."""
        for track in range(self.MIN_TRACK, self.MAX_TRACK + 1):
            self.stop(track)

    # ------------------------------------------------------------------
    # Track mixer
    # ------------------------------------------------------------------

    def track_mute(self, track: int, on: bool = True) -> bool:
        """Mute (``on=True``) or unmute (``on=False``) a track.

        Sends CC 94 on the track's MIDI channel.
        """
        channel = self._track_channel(track)
        if not isinstance(on, bool):
            raise ValueError(f"on must be a bool, got {type(on).__name__}")
        value = 127 if on else 0
        return self._midi.send_cc(channel, self.CC_MUTE, value)

    def track_solo(self, track: int, on: bool = True) -> bool:
        """Solo (``on=True``) or unsolo (``on=False``) a track.

        Sends CC 95 on the track's MIDI channel.
        """
        channel = self._track_channel(track)
        if not isinstance(on, bool):
            raise ValueError(f"on must be a bool, got {type(on).__name__}")
        value = 127 if on else 0
        return self._midi.send_cc(channel, self.CC_SOLO, value)

    def track_volume(self, track: int, value: int) -> bool:
        """Set a track's volume.

        Parameters
        ----------
        track:
            Track number, ``1``–``8``.
        value:
            Volume ``0``–``127`` (MIDI standard channel volume).
        """
        channel = self._track_channel(track)
        self._validate_int("value", value, 0, 127)
        return self._midi.send_cc(channel, self.CC_VOLUME, value)

    def track_pan(self, track: int, value: int) -> bool:
        """Set a track's stereo pan.

        Parameters
        ----------
        track:
            Track number, ``1``–``8``.
        value:
            Pan ``0``–``127`` (``0`` = full left, ``64`` = center,
            ``127`` = full right).
        """
        channel = self._track_channel(track)
        self._validate_int("value", value, 0, 127)
        return self._midi.send_cc(channel, self.CC_PAN, value)
