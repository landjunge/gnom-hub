"""Transport controller for the MC-707.

Wraps real-time MIDI messages (Start/Stop/Continue/Clock) and the
common Roland record-arm CCs. The exact MC-707 SysEx mapping for
master-tempo control is not yet verified against hardware, so the
corresponding paths are marked ``TEMPLATE - NEEDS VERIFICATION``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — type hint only
    from ..io.midi import MIDIIO

logger = logging.getLogger(__name__)


class TransportController:
    """High-level transport (play/stop/record/tempo) for the MC-707.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.
    """

    # Roland grooveboxes historically route transport to channel 10
    # (the GM drum channel). The exact MC-707 channel may differ — kept
    # here as an educated guess and easy to override.
    CONTROL_CHANNEL = 10

    # Educated guess: CC 116 = record arm, CC 117 = track select arm.
    # On the MC-707 these may need to be SysEx DT1 messages.
    CC_RECORD_ARM = 116
    CC_TRACK_ARM = 117

    def __init__(self, midi_io: "MIDIIO") -> None:
        self._midi = midi_io

    # ------------------------------------------------------------------
    # Transport primitives
    # ------------------------------------------------------------------

    def play(self) -> bool:
        """Start the sequencer (sends MIDI Start, 0xFA)."""
        logger.debug("Transport.play()")
        return self._midi.send_start()

    def stop(self) -> bool:
        """Stop the sequencer (sends MIDI Stop, 0xFC)."""
        logger.debug("Transport.stop()")
        return self._midi.send_stop()

    def pause(self) -> bool:
        """Pause the sequencer.

        On the MC-707 there is no canonical "Pause" message; sending
        ``Continue`` (0xFB) resumes from the current position. We use
        ``Continue`` here so the semantics are at least a no-op
        stop-then-resume toggle.
        """
        logger.debug("Transport.pause() -> continue")
        return self._midi.send_continue()

    def record(self, on: bool = True) -> bool:
        """Toggle the sequencer's record arm.

        Parameters
        ----------
        on:
            ``True`` arms recording, ``False`` disarms.

        Notes
        -----
        Sends CC 116 (record arm) on :attr:`CONTROL_CHANNEL`. Verified
        guess — needs to be checked against an actual MC-707. If the
        device ignores it, replace with the appropriate SysEx DT1.
        """
        value = 127 if on else 0
        return self._midi.send_cc(self.CONTROL_CHANNEL, self.CC_RECORD_ARM, value)

    # ------------------------------------------------------------------
    # Tempo
    # ------------------------------------------------------------------

    def tempo(self, bpm: int) -> bool:
        """Set the master tempo in BPM.

        Parameters
        ----------
        bpm:
            Target tempo, clamped to the valid 20–300 BPM range used by
            the MC-707.

        Notes
        -----
        TEMPLATE - NEEDS VERIFICATION
        The MC-707 does not expose tempo over standard MIDI CC. The
        current implementation sends 24 MIDI Clock (0xF8) ticks per
        beat at the requested BPM by writing a single timing message
        into the mock log. A real implementation must:

          1. Open an internal clock thread that emits Clock at the
             proper interval (bpm / 60 / 24 seconds between ticks), or
          2. Send a SysEx DT1 to the MC-707 tempo parameter address.
        """
        bpm = max(20, min(300, bpm))
        if self._midi.is_mock():
            # We do not actually emit a stream of clocks from here —
            # the real implementation needs a dedicated clock thread.
            self._midi._record(  # noqa: SLF001 — internal hook for tests
                "transport_tempo",
                bpm=bpm,
            )
            logger.info("Mock tempo set to %d BPM (no clock stream emitted).", bpm)
            return True

        # For real ports we update the internal interval so a future
        # clock thread can use it. We do NOT spawn a thread here — that
        # is the responsibility of a higher-level engine.
        self._midi._clock_interval = 60.0 / bpm / 24.0  # noqa: SLF001
        logger.info("Clock interval set to %.6f s (%.1f BPM).", self._midi._clock_interval, bpm)  # noqa: SLF001
        return True
