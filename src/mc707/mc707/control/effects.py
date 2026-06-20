"""Effects controller for the Roland MC-707.

This module exposes :class:`EffectsController`, a façade that translates
high-level effect-parameter calls into MIDI Control Change (CC) messages
on the MC-707's control channel. The CC numbers used here follow the
Roland convention for synth / filter / envelope parameters and the
standard send-level CCs for master effects.

TEMPLATE - VERIFY WITH MC-707 MIDI CHART
----------------------------------------
All CC numbers in this module are **educated guesses** derived from the
Roland synth-parameter convention used on the MC-101 and other MC-series
grooveboxes. The actual MC-707 mapping **must** be verified against the
official *MC-707 MIDI Implementation Chart* before relying on this
controller to drive real hardware.

Specifically still unverified:
    * :attr:`EffectsController.CC_FILTER_TYPE` (CC 77) — the MC-707
      may switch filter-type via a SysEx DT1 message instead of a CC.
    * :meth:`EffectsController.set_fx` — the formula
      ``send_cc(track + 9, 20 + slot, value)`` is a best-effort guess.
      The real MFX parameter protocol is almost certainly SysEx DT1 to
      the track-level FX address area, not a CC.

Even where the underlying numbers are guesses, the **dispatch path is
real**: every method below writes a ``control_change`` entry to the
mock log (and the corresponding CC on a real port), so the test surface
is exercisable today.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — type hint only
    from ..io.midi import MIDIIO

logger = logging.getLogger(__name__)


class EffectsController:
    """Master and per-track effect parameter control for the MC-707.

    The controller exposes two families of operations:

    * **Filter / envelope / master-send parameters** — addressed to the
      *control channel* (:attr:`CONTROL_CHANNEL`). These CCs apply
      globally to the current track's synth (cutoff, resonance,
      attack, decay, sustain, release) or to the master effect bus
      (reverb, chorus, delay, distortion).
    * **Filter-type selection** — also addressed to the control channel
      but using a small enum value (``0..3``).
    * **Per-track MFX slot parameters** — addressed to the track's own
      MIDI channel via :meth:`set_fx`. Track-to-channel mapping follows
      the project convention ``channel = track + 9``.

    Parameters
    ----------
    midi_io:
        A :class:`mc707.io.midi.MIDIIO`
        instance used to dispatch messages.

    Notes
    -----
    See the module docstring for the EDUCATED-GUESS markers. Every CC
    number below needs verification against the MC-707 MIDI
    Implementation Chart before this controller can be trusted to drive
    real hardware.
    """

    # ------------------------------------------------------------------
    # Channel & filter-type constants
    # ------------------------------------------------------------------

    # 1-based MIDI channel used for master effect CCs (cutoff, reverb,
    # etc.). Matches the project-wide CONTROL_CHANNEL convention used by
    # transport / scenes / arpeggiator.
    CONTROL_CHANNEL: int = 10

    # Filter-type enum values exposed to callers.
    FILTER_LPF: int = 0
    FILTER_HPF: int = 1
    FILTER_BPF: int = 2
    FILTER_NOTCH: int = 3

    # ------------------------------------------------------------------
    # CC constants (Roland synth convention — VERIFY AGAINST MC-707 MIDI CHART)
    # ------------------------------------------------------------------

    # Synth / filter envelope CCs.
    CC_CUTOFF: int = 74
    CC_RESONANCE: int = 71
    CC_ATTACK: int = 73
    CC_DECAY: int = 75
    CC_SUSTAIN: int = 79
    CC_RELEASE: int = 72

    # Master send levels.
    CC_REVERB: int = 91
    CC_CHORUS: int = 93
    CC_DELAY: int = 92
    CC_DISTORTION: int = 94

    # Filter-type selector.
    CC_FILTER_TYPE: int = 77       # TEMPLATE - VERIFY WITH MC-707 MIDI CHART

    # ------------------------------------------------------------------
    # MFX slot mapping (per-track set_fx)
    # ------------------------------------------------------------------

    MIN_TRACK: int = 1
    MAX_TRACK: int = 8

    # 1-based MIDI channel offset for track addressing.
    # Track 1 → MIDI channel ``1 + 9 = 10``; track 8 → MIDI channel 17
    # (which is outside the 1..16 MIDI range and gets silently clamped
    # to channel 16 by the underlying MIDIIO). The MC-707 might map
    # tracks to a different channel range — verify against hardware.
    TRACK_CHANNEL_OFFSET: int = 9   # TEMPLATE - VERIFY WITH MC-707 MIDI CHART

    # Base CC number used for per-track MFX slot addressing. The CC
    # number passed to the wire is ``CC_FX_SLOT_BASE + slot`` (slot 0..3).
    # TEMPLATE - VERIFY WITH MC-707 MIDI CHART (likely SysEx in reality).
    CC_FX_SLOT_BASE: int = 20

    MIN_SLOT: int = 0
    MAX_SLOT: int = 3
    MIN_PARAM: int = 0
    MAX_PARAM: int = 127
    MIN_CC_VALUE: int = 0
    MAX_CC_VALUE: int = 127

    def __init__(self, midi_io: "MIDIIO") -> None:
        self._midi = midi_io

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_cc_value(name: str, value: int) -> int:
        """Validate that *value* is an int in ``0..127``.

        Raises :class:`ValueError` with a clear message otherwise.
        Rejects ``bool`` explicitly (Python treats it as an int subclass
        but mapping ``True`` → ``1`` here is almost always a bug).
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{name} must be an int in 0..127, "
                f"got {type(value).__name__}"
            )
        if value < 0 or value > 127:
            raise ValueError(
                f"{name} must be between 0 and 127 (inclusive), got {value}"
            )
        return value

    @staticmethod
    def _validate_filter_type(filter_type: int) -> int:
        """Validate that *filter_type* is one of the four enum values.

        Allowed values: :attr:`FILTER_LPF` (0), :attr:`FILTER_HPF` (1),
        :attr:`FILTER_BPF` (2), :attr:`FILTER_NOTCH` (3).
        """
        if isinstance(filter_type, bool) or not isinstance(filter_type, int):
            raise ValueError(
                f"filter_type must be an int in 0..3, "
                f"got {type(filter_type).__name__}"
            )
        if filter_type < 0 or filter_type > 3:
            raise ValueError(
                f"filter_type must be 0 (LPF), 1 (HPF), 2 (BPF) or 3 (Notch), "
                f"got {filter_type}"
            )
        return filter_type

    def _validate_track(self, track: int) -> int:
        """Validate that *track* is in ``1..8`` (the MC-707's track range)."""
        if isinstance(track, bool) or not isinstance(track, int):
            raise ValueError(
                f"track must be an int in 1..8, got {type(track).__name__}"
            )
        if track < self.MIN_TRACK or track > self.MAX_TRACK:
            raise ValueError(
                f"track must be between {self.MIN_TRACK} and {self.MAX_TRACK} "
                f"(MC-707 has 8 tracks), got {track}"
            )
        return track

    # ------------------------------------------------------------------
    # Filter envelope
    # ------------------------------------------------------------------

    def cutoff(self, value: int) -> bool:
        """Set the filter cutoff.

        Parameters
        ----------
        value:
            Cutoff position, ``0``–``127`` (inclusive).

        Returns
        -------
        bool
            ``True`` if the CC was dispatched (always ``True`` in mock mode).

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127`` or has the wrong type.

        Notes
        -----
        Sends CC :attr:`CC_CUTOFF` (=74) on the :attr:`CONTROL_CHANNEL`.
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 74 follows the
        Roland synth-parameter convention but the MC-707 might assign
        cutoff to a different controller number.

        In a MIDI monitor you would observe:

        .. code-block:: text

            Ch 10  CC 74  value=<value>
        """
        self._validate_cc_value("cutoff", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_CUTOFF, value)

    def resonance(self, value: int) -> bool:
        """Set the filter resonance (CC :attr:`CC_RESONANCE` on the control channel).

        Parameters
        ----------
        value:
            Resonance amount, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 71 is the Roland
        synth convention.
        """
        self._validate_cc_value("resonance", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_RESONANCE, value)

    def filter_type(self, filter_type: int) -> bool:
        """Set the filter type.

        Parameters
        ----------
        filter_type:
            One of :attr:`FILTER_LPF` (0), :attr:`FILTER_HPF` (1),
            :attr:`FILTER_BPF` (2), :attr:`FILTER_NOTCH` (3).

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``filter_type`` is outside ``0..3``.

        Notes
        -----
        Sends CC :attr:`CC_FILTER_TYPE` (=77) on the control channel.
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — the MC-707 may use a
        SysEx DT1 to the filter-type address rather than a CC; CC 77 is
        the best-effort guess so the dispatch path is exercisable today.
        """
        self._validate_filter_type(filter_type)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_FILTER_TYPE, filter_type,
        )

    # ------------------------------------------------------------------
    # Amp envelope
    # ------------------------------------------------------------------

    def attack(self, value: int) -> bool:
        """Set the amp-envelope attack (CC :attr:`CC_ATTACK` on the control channel).

        Parameters
        ----------
        value:
            Attack time, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 73 is the Roland
        synth convention.
        """
        self._validate_cc_value("attack", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_ATTACK, value)

    def decay(self, value: int) -> bool:
        """Set the amp-envelope decay (CC :attr:`CC_DECAY` on the control channel).

        Parameters
        ----------
        value:
            Decay time, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.
        """
        self._validate_cc_value("decay", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_DECAY, value)

    def sustain(self, value: int) -> bool:
        """Set the amp-envelope sustain level (CC :attr:`CC_SUSTAIN`).

        Parameters
        ----------
        value:
            Sustain level, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.
        """
        self._validate_cc_value("sustain", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_SUSTAIN, value)

    def release(self, value: int) -> bool:
        """Set the amp-envelope release time (CC :attr:`CC_RELEASE`).

        Parameters
        ----------
        value:
            Release time, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.
        """
        self._validate_cc_value("release", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_RELEASE, value)

    # ------------------------------------------------------------------
    # Master effect sends
    # ------------------------------------------------------------------

    def reverb(self, value: int) -> bool:
        """Set the master reverb send level (CC :attr:`CC_REVERB` on the control channel).

        Parameters
        ----------
        value:
            Send level, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 91 is the standard
        "Effects 1 Depth" controller used by most Roland synths for
        reverb send.
        """
        self._validate_cc_value("reverb", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_REVERB, value)

    def chorus(self, value: int) -> bool:
        """Set the master chorus send level (CC :attr:`CC_CHORUS` on the control channel).

        Parameters
        ----------
        value:
            Send level, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 93 is the standard
        "Effects 3 Depth" controller used by most Roland synths for
        chorus send.
        """
        self._validate_cc_value("chorus", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_CHORUS, value)

    def delay(self, value: int) -> bool:
        """Set the master delay send level (CC :attr:`CC_DELAY` on the control channel).

        Parameters
        ----------
        value:
            Send level, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 92 is the standard
        "Effects 2 Depth" controller used by most Roland synths for
        delay send.
        """
        self._validate_cc_value("delay", value)
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_DELAY, value)

    def distortion(self, value: int) -> bool:
        """Set the master distortion send level (CC :attr:`CC_DISTORTION`).

        Parameters
        ----------
        value:
            Send level, ``0``–``127``.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 94 is the standard
        "Effects 4 Depth" controller; whether the MC-707 exposes a
        dedicated distortion send via CC 94 is unverified.
        """
        self._validate_cc_value("distortion", value)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_DISTORTION, value,
        )

    # ------------------------------------------------------------------
    # Per-track MFX slot parameter
    # ------------------------------------------------------------------

    def set_fx(self, track: int, slot: int, param: int, value: int) -> bool:
        """Set a parameter on a specific MFX slot of a track.

        Parameters
        ----------
        track:
            Target track, ``1``–``8``. The track's MIDI channel is
            computed as ``track + TRACK_CHANNEL_OFFSET`` (= track + 9).
        slot:
            MFX slot index on the track, ``0``–``3`` (0 = MFX1,
            1 = MFX2, etc.). The CC number written to the wire is
            ``CC_FX_SLOT_BASE + slot`` (= 20 + slot).
        param:
            Parameter index within the effect, ``0``–``127``. Currently
            accepted but **not** packed into the CC value — the real
            parameter addressing requires a SysEx DT1 (see notes below).
        value:
            Parameter value, ``0``–``127``.

        Returns
        -------
        bool
            ``True`` if the CC was dispatched (always ``True`` in mock mode).

        Raises
        ------
        ValueError
            If ``track`` is outside ``1..8``, ``slot`` outside ``0..3``,
            ``param`` outside ``0..127``, or ``value`` outside ``0..127``.

        Notes
        -----
        TEMPLATE - VERIFY WITH MC-707 MIDI CHART
        ---------------------------------------
        The MC-707's per-track MFX parameters are most likely addressed
        via SysEx DT1 to the track-level FX address area, **not** via
        CC. The current CC-based dispatch
        ``send_cc(track + 9, 20 + slot, value)`` is a best-effort
        placeholder so the test surface is exercisable in mock mode
        today. The slot→CC mapping is also an educated guess; the
        *param* argument is currently ignored at the wire level.

        Known limitation: ``track = 8`` maps to MIDI channel 17, which
        is outside the 1..16 MIDI range; :meth:`MIDIIO.send_cc` clamps
        this silently to channel 16. If you need track 8 to address a
        distinct channel, this method will need to be reworked against
        the real MC-707 MIDI chart.

        In a MIDI monitor you would observe:

        .. code-block:: text

            Ch <track + 9>  CC <20 + slot>  value=<value>
        """
        self._validate_track(track)
        if isinstance(slot, bool) or not isinstance(slot, int):
            raise ValueError(
                f"slot must be an int in {self.MIN_SLOT}..{self.MAX_SLOT}, "
                f"got {type(slot).__name__}"
            )
        if slot < self.MIN_SLOT or slot > self.MAX_SLOT:
            raise ValueError(
                f"slot must be between {self.MIN_SLOT} and {self.MAX_SLOT}, "
                f"got {slot}"
            )
        self._validate_cc_value("param", param)
        self._validate_cc_value("value", value)

        channel = track + self.TRACK_CHANNEL_OFFSET
        cc_number = self.CC_FX_SLOT_BASE + slot
        return self._midi.send_cc(channel, cc_number, value)