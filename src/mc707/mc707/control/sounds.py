"""Sound / patch loader for the Roland MC-707.

The MC-707 organises its sounds in a *bank / program* hierarchy:
  - Tones (single patches for melodic tracks)
  - Drum Kits (full kits for rhythm tracks)

Both are addressed through the standard MIDI Bank Select mechanism
(CC #0 = MSB, CC #32 = LSB) followed by a Program Change.

This module exposes a high-level façade — :class:`SoundController` —
that wraps the three messages into clean ``load_*`` calls.

----------------------------------------------------------------------------
EDUCATED GUESS MARKERS
----------------------------------------------------------------------------
All bank-layout values used here are **educated guesses** derived from
the Roland convention and from ``docs/mc707_handoff.md``. They MUST be
verified against the official *MC-707 MIDI Implementation Chart* once
it is available — especially:

  - **Bank MSB semantics** — "Bank 0 = Preset, Bank 1 = User" is an
    EDUCATED GUESS. The real MC-707 may split preset vs. user across
    a much wider MSB range (the MC-707 has hundreds of tones and kits,
    so the bank numbering is almost certainly non-trivial).
  - **Drum-Kit vs. Instrument bank slots** — the two categories may
    share the same MSB range or live in separate MSB spaces. This
    EDUCATED GUESS assumes they share the same MSB axis and differ
    only in the LSB (or in the track configuration).
  - **Track-to-channel mapping** — Track 1 = MIDI channel 10, Track 2
    = channel 11, …, Track 8 = channel 17. Channel 17 is outside the
    1–16 range and gets silently clamped to channel 16 by the underlying
    MIDI backend; this is a known limitation until a dedicated MC-707
    transport driver is wired in.

**Verification required** against the MC-707 MIDI Implementation Chart
before relying on this module to address real hardware.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SoundController:
    """Sound / patch loader for the MC-707.

    The controller translates high-level load requests into the three-
    message MIDI sequence (Bank MSB, Bank LSB, Program Change) on the
    MIDI channel that belongs to the addressed track.

    Parameters
    ----------
    midi_io:
        A :class:`mc707.io.midi.MIDIIO`
        instance used to dispatch messages.

    Attributes
    ----------
    CC_BANK_MSB, CC_BANK_LSB:
        Standard MIDI Bank-Select controller numbers (CC#0 / CC#32).
        These are MIDI standard and not device-specific.

    Notes
    -----
    See the module docstring for the EDUCATED GUESS markers — every
    bank-layout value below needs verification against the official
    MC-707 MIDI Implementation Chart.
    """

    # Standard MIDI Bank Select CCs (not device-specific).
    CC_BANK_MSB: int = 0
    CC_BANK_LSB: int = 32

    # Track range on the MC-707 (8 tracks per project).
    MIN_TRACK: int = 1
    MAX_TRACK: int = 8

    # MIDI channel offset: Track 1 → MIDI channel 10, Track 8 → channel 17.
    # MC-707 convention. EDUCATED GUESS — verify against MIDI Implementation
    # Chart. (See module docstring.)
    TRACK_CHANNEL_OFFSET: int = 9

    # EDUCATED GUESS: bank MSB semantics for the MC-707.
    BANK_MSB_PRESET: int = 0
    BANK_MSB_USER: int = 1

    def __init__(self, midi_io) -> None:
        self._midi = midi_io

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_track(self, track: int) -> None:
        """Raise ``ValueError`` if *track* is outside the MC-707 range."""
        if not isinstance(track, int) or isinstance(track, bool):
            raise ValueError(
                f"track must be an int in {self.MIN_TRACK}..{self.MAX_TRACK}, "
                f"got {track!r}"
            )
        if not (self.MIN_TRACK <= track <= self.MAX_TRACK):
            raise ValueError(
                f"track must be in {self.MIN_TRACK}..{self.MAX_TRACK} "
                f"(MC-707 has 8 tracks), got {track}"
            )

    def _validate_program(self, tone_number: int, label: str = "tone_number") -> None:
        """Raise ``ValueError`` if *tone_number* is outside the 0–127 MIDI range."""
        if not isinstance(tone_number, int) or isinstance(tone_number, bool):
            raise ValueError(
                f"{label} must be an int in 0..127, got {tone_number!r}"
            )
        if not (0 <= tone_number <= 127):
            raise ValueError(
                f"{label} must be in 0..127, got {tone_number}"
            )

    def _validate_bank(self, bank_msb: int, bank_lsb: int) -> None:
        """Raise ``ValueError`` if either bank value is outside 0–127."""
        if not isinstance(bank_msb, int) or isinstance(bank_msb, bool):
            raise ValueError(f"bank_msb must be an int in 0..127, got {bank_msb!r}")
        if not isinstance(bank_lsb, int) or isinstance(bank_lsb, bool):
            raise ValueError(f"bank_lsb must be an int in 0..127, got {bank_lsb!r}")
        if not (0 <= bank_msb <= 127):
            raise ValueError(f"bank_msb must be in 0..127, got {bank_msb}")
        if not (0 <= bank_lsb <= 127):
            raise ValueError(f"bank_lsb must be in 0..127, got {bank_lsb}")

    def _track_channel(self, track: int) -> int:
        """Map an MC-707 track index to its MIDI channel (1-based).

        Track 1 → channel 10, Track 8 → channel 17. The result is the
        1-based channel number expected by :meth:`MIDIIO.send_cc` /
        :meth:`MIDIIO.send_program_change`.
        """
        return track + self.TRACK_CHANNEL_OFFSET

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_tone(
        self,
        track: int,
        tone_number: int,
        bank_msb: int = 0,
        bank_lsb: int = 0,
    ) -> bool:
        """Load a Tone onto a track via Bank-Select + Program-Change.

        Sends, in order, on the track's MIDI channel:

          1. ``CC #0``   (Bank Select MSB) with ``bank_msb``
          2. ``CC #32``  (Bank Select LSB) with ``bank_lsb``
          3. ``Program Change`` with ``tone_number``

        Parameters
        ----------
        track:
            MC-707 track index, **1–8**. Raises ``ValueError`` outside
            this range (no silent clamping — the caller should know).
        tone_number:
            Tone number / Program-Change value, **0–127**.
        bank_msb:
            Bank Select MSB (CC#0), **0–127**. Default ``0`` (preset bank).
        bank_lsb:
            Bank Select LSB (CC#32), **0–127**. Default ``0``.

        Returns
        -------
        bool
            ``True`` if every message was dispatched (in mock mode this
            is always true). ``False`` if the underlying ``MIDIIO``
            reported a send failure on any of the three messages.

        Raises
        ------
        ValueError
            If ``track`` is outside 1–8, or ``tone_number`` / ``bank_msb``
            / ``bank_lsb`` are outside 0–127, or if any parameter has the
            wrong type.

        Notes
        -----
        EDUCATED GUESS — Bank MSB/LSB semantics for the MC-707 need
        verification against the official MIDI Implementation Chart.
        The "Bank 0 = Preset, Bank 1 = User" convention used by
        :meth:`load_drum_kit` / :meth:`load_instrument` is also an
        educated guess.
        """
        self._validate_track(track)
        self._validate_program(tone_number, label="tone_number")
        self._validate_bank(bank_msb, bank_lsb)

        channel = self._track_channel(track)

        # Bank Select MSB (CC #0).
        if not self._midi.send_cc(channel, self.CC_BANK_MSB, bank_msb):
            logger.error(
                "Failed to send Bank-Select MSB (track=%d, channel=%d, "
                "bank_msb=%d).",
                track, channel, bank_msb,
            )
            return False

        # Bank Select LSB (CC #32).
        if not self._midi.send_cc(channel, self.CC_BANK_LSB, bank_lsb):
            logger.error(
                "Failed to send Bank-Select LSB (track=%d, channel=%d, "
                "bank_lsb=%d).",
                track, channel, bank_lsb,
            )
            return False

        # Program Change.
        if not self._midi.send_program_change(channel, tone_number):
            logger.error(
                "Failed to send Program-Change (track=%d, channel=%d, "
                "tone=%d).",
                track, channel, tone_number,
            )
            return False

        logger.info(
            "Loaded tone on track %d (channel %d): bank_msb=%d bank_lsb=%d "
            "program=%d.",
            track, channel, bank_msb, bank_lsb, tone_number,
        )
        return True

    def load_drum_kit(
        self,
        track: int,
        kit_number: int,
        user: bool = False,
    ) -> bool:
        """Load a Drum Kit onto a track.

        Convenience wrapper around :meth:`load_tone` that selects the
        appropriate bank based on the ``user`` flag.

        Parameters
        ----------
        track:
            MC-707 track index, **1–8**.
        kit_number:
            Kit number / Program-Change value, **0–127**.
        user:
            ``False`` → preset bank (``bank_msb = 0``),
            ``True``  → user bank   (``bank_msb = 1``).

        Returns
        -------
        bool
            Result of the underlying :meth:`load_tone` call.

        Raises
        ------
        ValueError
            If ``track`` is outside 1–8 or ``kit_number`` outside 0–127.

        Notes
        -----
        EDUCATED GUESS — Both the preset/user MSB split (0 / 1) **and**
        the assumption that Drum-Kits and Instruments share the same
        MSB axis need verification against the MC-707 MIDI Implementation
        Chart.
        """
        self._validate_track(track)
        self._validate_program(kit_number, label="kit_number")

        bank_msb = self.BANK_MSB_USER if user else self.BANK_MSB_PRESET
        return self.load_tone(track, kit_number, bank_msb=bank_msb, bank_lsb=0)

    def load_instrument(
        self,
        track: int,
        tone_number: int,
        user: bool = False,
    ) -> bool:
        """Load an Instrument Tone onto a track.

        Convenience wrapper around :meth:`load_tone` that selects the
        appropriate bank based on the ``user`` flag.

        Parameters
        ----------
        track:
            MC-707 track index, **1–8**.
        tone_number:
            Tone number / Program-Change value, **0–127**.
        user:
            ``False`` → preset bank (``bank_msb = 0``),
            ``True``  → user bank   (``bank_msb = 1``).

        Returns
        -------
        bool
            Result of the underlying :meth:`load_tone` call.

        Raises
        ------
        ValueError
            If ``track`` is outside 1–8 or ``tone_number`` outside 0–127.

        Notes
        -----
        EDUCATED GUESS — Drum-Kit vs. Instrument bank slots are an
        educated guess; this method currently writes the same MSB as
        :meth:`load_drum_kit` and relies on track configuration to
        disambiguate. Verify against the MC-707 MIDI Implementation
        Chart.
        """
        self._validate_track(track)
        self._validate_program(tone_number, label="tone_number")

        bank_msb = self.BANK_MSB_USER if user else self.BANK_MSB_PRESET
        return self.load_tone(track, tone_number, bank_msb=bank_msb, bank_lsb=0)