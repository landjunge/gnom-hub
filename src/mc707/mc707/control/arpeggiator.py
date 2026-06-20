"""Arpeggiator controller for the Roland MC-707.

This module exposes :class:`ArpeggiatorController`, a façade for
turning the MC-707's built-in arpeggiator on/off and adjusting its
runtime parameters (rate, gate length, style, octave range).

TEMPLATE - VERIFY WITH MC-707 MIDI CHART
----------------------------------------
**All five CC numbers in this module are educated guesses.** The
MC-707 MIDI Implementation Chart needs to confirm:

    * :attr:`CC_ARP_ON`    (=58) — on/off toggle
    * :attr:`CC_ARP_RATE`  (=59) — note rate / tempo-division
    * :attr:`CC_ARP_GATE`  (=60) — gate length
    * :attr:`CC_ARP_STYLE` (=61) — Up / Down / UpDown / Random
    * :attr:`CC_ARP_OCTAVE`(=62) — octave range (0..3)

In reality the arpeggiator is almost certainly addressed through
SysEx DT1 to the arp parameter area; CCs 58–62 are placeholder slots
so the dispatch path is exercisable in mock mode today.

Even where the numbers are guesses, every method below writes a
``control_change`` entry to the mock log (and the corresponding CC on a
real port), so the test surface is usable now.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — type hint only
    from ..io.midi import MIDIIO

logger = logging.getLogger(__name__)


class ArpeggiatorController:
    """Arpeggiator on/off and parameter control for the MC-707.

    The controller maps the MC-707 arpeggiator's user-facing knobs
    (on/off, rate, gate, style, octave) onto dedicated CC numbers on
    the :attr:`CONTROL_CHANNEL`. The mapping is currently a best-effort
    placeholder — see the module docstring for the EDUCATED-GUESS
    marker.

    Parameters
    ----------
    midi_io:
        A :class:`mc707.io.midi.MIDIIO`
        instance used to dispatch messages.

    Attributes
    ----------
    _enabled:
        Last on/off value requested via :meth:`on`. Useful for
        introspection but does **not** track the real hardware state
        (no RQ1 polling is performed).

    Notes
    -----
    All five CC numbers below need verification against the MC-707 MIDI
    Implementation Chart. The current values (58..62) are educated
    guesses from the Roland synth-parameter convention.
    """

    # ------------------------------------------------------------------
    # Channel & style constants
    # ------------------------------------------------------------------

    # 1-based MIDI channel used for the arpeggiator CCs. Matches the
    # project-wide CONTROL_CHANNEL convention.
    CONTROL_CHANNEL: int = 10

    # Arpeggiator style enum values.
    STYLE_UP: int = 0
    STYLE_DOWN: int = 1
    STYLE_UPDOWN: int = 2
    STYLE_RANDOM: int = 3

    # ------------------------------------------------------------------
    # CC constants — TEMPLATE - VERIFY WITH MC-707 MIDI CHART
    # ------------------------------------------------------------------

    CC_ARP_ON: int = 58       # TEMPLATE - VERIFY WITH MC-707 MIDI CHART
    CC_ARP_RATE: int = 59     # TEMPLATE - VERIFY WITH MC-707 MIDI CHART
    CC_ARP_GATE: int = 60     # TEMPLATE - VERIFY WITH MC-707 MIDI CHART
    CC_ARP_STYLE: int = 61    # TEMPLATE - VERIFY WITH MC-707 MIDI CHART
    CC_ARP_OCTAVE: int = 62   # TEMPLATE - VERIFY WITH MC-707 MIDI CHART

    # ------------------------------------------------------------------
    # Range constants
    # ------------------------------------------------------------------

    # Standard MIDI CC value range.
    MIN_CC_VALUE: int = 0
    MAX_CC_VALUE: int = 127

    # Octave range (number of octaves spanned by the arpeggio).
    MIN_OCTAVE: int = 0
    MAX_OCTAVE: int = 3

    # Style range — Up/Down/UpDown/Random plus 4 more unspecified slots.
    MIN_STYLE: int = 0
    MAX_STYLE: int = 3

    def __init__(self, midi_io: "MIDIIO") -> None:
        self._midi = midi_io
        self._enabled: bool = False

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
    def _validate_style(value: int) -> int:
        """Validate that *value* is one of the four arp-style enums."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"style must be an int in 0..3, "
                f"got {type(value).__name__}"
            )
        if value < 0 or value > 3:
            raise ValueError(
                f"style must be 0 (Up), 1 (Down), 2 (UpDown) or 3 (Random), "
                f"got {value}"
            )
        return value

    @staticmethod
    def _validate_octave(value: int) -> int:
        """Validate that *value* is an int in ``0..3`` (number of octaves)."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"octave must be an int in 0..3, "
                f"got {type(value).__name__}"
            )
        if value < 0 or value > 3:
            raise ValueError(
                f"octave must be between 0 and 3 (number of octaves), "
                f"got {value}"
            )
        return value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on(self, on: bool = True) -> bool:
        """Enable or disable the arpeggiator.

        Parameters
        ----------
        on:
            ``True`` to enable the arpeggiator, ``False`` to disable it.

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``on`` is not a ``bool``.

        Notes
        -----
        Sends CC :attr:`CC_ARP_ON` (=58) on :attr:`CONTROL_CHANNEL`
        with value ``127`` for *on* or ``0`` for *off*.

        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 58 is an educated
        guess; the MC-707 may use a different CC or a SysEx DT1 toggle.

        In a MIDI monitor you would observe:

        .. code-block:: text

            Ch 10  CC 58  value=127   (enable)
            Ch 10  CC 58  value=0     (disable)
        """
        if not isinstance(on, bool):
            raise ValueError(
                f"on must be a bool, got {type(on).__name__}"
            )
        self._enabled = on
        value = 127 if on else 0
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_ARP_ON, value,
        )

    def off(self) -> bool:
        """Disable the arpeggiator. Convenience wrapper for ``self.on(on=False)``."""
        return self.on(on=False)

    def rate(self, value: int) -> bool:
        """Set the arpeggiator note rate.

        Parameters
        ----------
        value:
            Rate position, ``0``–``127``. The exact mapping from value to
            note-rate (1/32 ... 1/1) is device-specific; 0 = slowest,
            127 = fastest as a working assumption.

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        Sends CC :attr:`CC_ARP_RATE` (=59) on :attr:`CONTROL_CHANNEL`.

        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 59 is an educated
        guess. The MC-707 may express the rate as a tempo-division
        index (``0..15``) rather than a free ``0..127`` value.

        In a MIDI monitor:

        .. code-block:: text

            Ch 10  CC 59  value=<value>
        """
        self._validate_cc_value("rate", value)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_ARP_RATE, value,
        )

    def gate(self, value: int) -> bool:
        """Set the arpeggiator gate length.

        Parameters
        ----------
        value:
            Gate length, ``0``–``127``. Conventionally a percentage of
            the step length (small = staccato, large = legato); the
            MC-707's exact mapping needs verification.

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..127``.

        Notes
        -----
        Sends CC :attr:`CC_ARP_GATE` (=60) on :attr:`CONTROL_CHANNEL`.

        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 60 is an educated
        guess.

        In a MIDI monitor:

        .. code-block:: text

            Ch 10  CC 60  value=<value>
        """
        self._validate_cc_value("gate", value)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_ARP_GATE, value,
        )

    def style(self, value: int) -> bool:
        """Set the arpeggiator playing style.

        Parameters
        ----------
        value:
            One of :attr:`STYLE_UP` (0), :attr:`STYLE_DOWN` (1),
            :attr:`STYLE_UPDOWN` (2), :attr:`STYLE_RANDOM` (3).
            Values ``4..7`` may be reserved for additional styles on
            the MC-707 (e.g. Chord, Octave-Random) but are currently
            rejected here.

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..3``.

        Notes
        -----
        Sends CC :attr:`CC_ARP_STYLE` (=61) on :attr:`CONTROL_CHANNEL`.

        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 61 is an educated
        guess. The MC-707 may support additional styles beyond
        Up/Down/UpDown/Random; the range will need to be widened once
        the real style table is known.

        In a MIDI monitor:

        .. code-block:: text

            Ch 10  CC 61  value=<value>
        """
        self._validate_style(value)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_ARP_STYLE, value,
        )

    def octave(self, value: int) -> bool:
        """Set the arpeggiator octave range.

        Parameters
        ----------
        value:
            Number of octaves spanned by the arpeggio, ``0``–``3``.
            ``0`` means the arpeggio stays on the original note,
            ``3`` spans three octaves (e.g. C3–C6).

        Returns
        -------
        bool
            ``True`` if the CC was dispatched.

        Raises
        ------
        ValueError
            If ``value`` is outside ``0..3``.

        Notes
        -----
        Sends CC :attr:`CC_ARP_OCTAVE` (=62) on :attr:`CONTROL_CHANNEL`.

        TEMPLATE - VERIFY WITH MC-707 MIDI CHART — CC 62 is an educated
        guess. The MC-707 may allow a wider octave range (e.g. ``0..4``).

        In a MIDI monitor:

        .. code-block:: text

            Ch 10  CC 62  value=<value>
        """
        self._validate_octave(value)
        return self._midi.send_cc(
            self.CONTROL_CHANNEL, self.CC_ARP_OCTAVE, value,
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """Return the last requested on/off state.

        This mirrors the most recent :meth:`on` call only — it does not
        read back the hardware state. Use :class:`StatusController` for
        a live read-back.
        """
        return self._enabled