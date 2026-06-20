"""Pattern (step sequencer) controller for the Roland MC-707.

A *pattern* on the MC-707 is a sequence of *steps* — typically 16 per
pattern, sometimes more — that says which note plays (or rests) at each
step on a given track. Each step also carries performance modifiers
(velocity, gate length, micro-timing offset, probability, ratchet, …)
that turn a plain note grid into a groove.

This module exposes :class:`PatternController`, a high-level façade that
accepts a user-friendly ``steps`` description (either ``List[int]`` or
``List[Dict]``) and dispatches one **edit message** per step to the
underlying :class:`MIDIIO`.

----------------------------------------------------------------------------
TEMPLATE - NEEDS MC-707 MIDI CHART VERIFICATION
----------------------------------------------------------------------------
The real MC-707 does *not* receive a step pattern as a single MIDI
message. Each step on the hardware is the result of **several
coordinated SysEx DT1 blocks** — at minimum:

  1. Note number       (0–127)
  2. Velocity          (1–127)
  3. Gate length       (1–127, percentage of step duration)
  4. Micro-Offset      (-24..+24 ticks; shift the step in time)
  5. Probability       (0–127; chance the step fires)
  6. Ratchet / Sub-step (1, 2, 3, 4 …; number of re-triggers per step)
  7. Accent / Swing flag (optional)

Without the official Roland *MC-707 MIDI Implementation Chart* we cannot
address those sub-fields exactly. The :meth:`PatternController._send_step`
method below therefore emits a **single best-effort DT1 frame** as a
*skeleton*: it covers Note/Velocity/Gate in a plausible address layout,
leaving Micro-Offset / Probability / Ratchet as TODO comment slots. In
mock mode the frame is just logged.

The mock-mode dispatch (a Note-On / Note-Off pair per step) is the
defacto test surface today; once the MIDI Chart is available, replace
:meth:`_send_step` with the per-field DT1 burst without touching the
public API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# Public alias for the accepted step description. Either a MIDI note
# number (int) or a per-step dict (see :meth:`PatternController.program`).
StepSpec = Union[int, Dict[str, Any]]


class PatternController:
    """Step-pattern programming for the MC-707.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.

    Attributes
    ----------
    MIN_TRACK / MAX_TRACK:
        Track range ``1``–``8`` (MC-707 has 8 tracks).
    TRACK_CHANNEL_OFFSET:
        MIDI channel offset for tracks (Track N → MIDI channel ``N + 9``,
        so Track 1 = channel 10, Track 8 = channel 17). Same convention
        as :class:`ClipController` / :class:`SoundController`.
    MIN_NOTE / MAX_NOTE:
        MIDI note range ``0``–``127``.
    MIN_VELOCITY / MAX_VELOCITY:
        Velocity range ``1``–``127`` (0 = note off, so we reject it).
    MIN_GATE / MAX_GATE:
        Gate-length range ``1``–``127``. ``100`` = full step duration;
        smaller values are shorter, larger values are *legato*-style
        overlap into the next step.
    DEFAULT_VELOCITY / DEFAULT_GATE:
        Sensible defaults used when the caller passes a plain ``int``
        step or omits ``velocity``/``gate`` in a dict step.
    MIN_PATTERN / MAX_PATTERN:
        Pattern-slot range ``0``–``127``.
    """

    # Track range on the MC-707 (8 tracks per project).
    MIN_TRACK: int = 1
    MAX_TRACK: int = 8

    # MIDI channel offset: Track 1 → MIDI channel 10, Track 8 → channel 17.
    # Same Roland convention as the rest of the controllers.
    # TEMPLATE - NEEDS VERIFICATION against the MIDI Implementation Chart.
    TRACK_CHANNEL_OFFSET: int = 9

    # MIDI note range.
    MIN_NOTE: int = 0
    MAX_NOTE: int = 127

    # Velocity range. Note-On with velocity 0 is MIDI for "Note-Off", so
    # we require vel >= 1.
    MIN_VELOCITY: int = 1
    MAX_VELOCITY: int = 127

    # Gate length range, percentage of step duration (1..127).
    MIN_GATE: int = 1
    MAX_GATE: int = 127

    # Defaults applied when an ``int`` step omits the field.
    DEFAULT_VELOCITY: int = 100
    DEFAULT_GATE: int = 80

    # Pattern-slot range (the MC-707 has a generous pattern count;
    # the exact upper bound depends on project size).
    # TEMPLATE - NEEDS VERIFICATION
    MIN_PATTERN: int = 0
    MAX_PATTERN: int = 127

    # ------------------------------------------------------------------
    # SysEx layout for the per-step DT1 frame — SKELETON ONLY.
    # ------------------------------------------------------------------
    #
    # EDUCATED GUESS for the per-track pattern-data address prefix:
    # ``(0x19, 0x10, track - 1)``. This is a plausible Roland-style
    # parameter area for "track pattern data" but **must** be verified
    # against the MC-707 MIDI Implementation Chart before the skeleton
    # below is treated as real.
    #
    # A complete per-step DT1 burst on the real device will need to
    # write the following fields to one or more addresses:
    #   - Note number       (0x00..0x7F)
    #   - Velocity          (0x01..0x7F)
    #   - Gate length       (0x01..0x7F)
    #   - Micro-Offset      (-24..+24 ticks, 7-bit signed)
    #   - Probability       (0x00..0x7F)
    #   - Ratchet count     (0..N, depends on MC-707 model)
    #
    # Only the first three are addressed in the skeleton below; the
    # others are TODO markers in :meth:`_send_step`.

    # SysEx DT1 command class (matches ``sysex.CMD_DT1``).
    _DT1_CMD = 0x12

    def __init__(self, midi_io) -> None:
        self._midi = midi_io

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def program(
        self,
        track: int,
        steps: List[StepSpec],
        pattern_number: Optional[int] = None,
        velocity: int = DEFAULT_VELOCITY,
        gate: int = DEFAULT_GATE,
    ) -> bool:
        """Program a step pattern onto a track.

        Parameters
        ----------
        track:
            Target track, **1–8** (MC-707 has 8 tracks).
        steps:
            List of step descriptions. Each element may be:

            * ``int`` — MIDI note number (``0`` = rest, anything else
              in ``0..127``). The defaults ``velocity``/``gate`` are
              applied.
            * ``dict`` — per-step overrides with at least a ``"note"``
              key. Recognised keys:

              - ``"note"``     (int, required, ``0..127``, ``0`` = rest)
              - ``"velocity"`` (int, optional, ``1..127``; falls back to
                the ``velocity`` argument if omitted)
              - ``"gate"``     (int, optional, ``1..127``; falls back to
                the ``gate`` argument if omitted)

            A step whose ``note`` is ``0`` is treated as a *rest* and
            skipped (no message dispatched). Any other type raises
            :class:`ValueError`.
        pattern_number:
            Optional pattern-slot index (``0..127``). When provided, the
            controller logs ``scene select {n}`` — see *Notes* below.
        velocity:
            Default velocity (``1..127``) for plain ``int`` steps and
            for dict steps that omit ``"velocity"``. Default ``100``.
        gate:
            Default gate length (``1..127``) for plain ``int`` steps and
            for dict steps that omit ``"gate"``. Default ``80``.

        Returns
        -------
        bool
            ``True`` if every step was dispatched (or skipped as a rest)
            successfully. ``False`` on the first step whose underlying
            send fails.

        Raises
        ------
        ValueError
            On out-of-range ``track`` (outside 1..8), invalid step
            types, out-of-range ``note`` / ``velocity`` / ``gate``, or
            out-of-range ``pattern_number``.

        Notes
        -----
        ``pattern_number`` is currently a **selector log only** — the
        real MC-707 scene/pattern switch protocol is expected to live
        on :class:`SceneController` (Program Change on the control
        channel). Once the MIDI Chart is available, wire the actual
        pattern-select SysEx into :meth:`select_pattern` and call it
        here instead of just logging.

        TEMPLATE - NEEDS MC-707 MIDI CHART VERIFICATION
        The per-step payload is sent as a skeleton DT1 frame in
        :meth:`_send_step`; in mock mode that frame is captured in the
        log alongside a Note-On / Note-Off pair so the test surface is
        exercisable today.
        """
        # --- Argument validation -------------------------------------
        self._validate_track(track)
        self._validate_velocity(velocity, label="velocity")
        self._validate_gate(gate, label="gate")

        if pattern_number is not None:
            self._validate_pattern(pattern_number)

        if not isinstance(steps, list):
            raise ValueError(
                f"steps must be a list, got {type(steps).__name__}"
            )

        # --- Optional pattern-slot logging ----------------------------
        if pattern_number is not None:
            logger.info(
                "PatternController: scene select %d "
                "(pattern slot pre-activate — verify against MIDI Chart).",
                pattern_number,
            )

        # --- Per-step dispatch ----------------------------------------
        ok_all = True
        for step_num, step in enumerate(steps):
            try:
                note, vel, g = self._normalize_step(
                    step, velocity, gate, step_num,
                )
            except ValueError:
                # Re-raise — validation errors must propagate.
                raise

            # Rest step: nothing to dispatch.
            if note == 0:
                continue

            ok = self._send_step(track, step_num, note, vel, g)
            if not ok:
                logger.warning(
                    "PatternController: failed to dispatch step %d "
                    "(track=%d, note=%d, vel=%d, gate=%d).",
                    step_num, track, note, vel, g,
                )
                ok_all = False

        return ok_all

    # ------------------------------------------------------------------
    # Internal: step normalization
    # ------------------------------------------------------------------

    def _normalize_step(
        self,
        step: StepSpec,
        default_velocity: int,
        default_gate: int,
        step_num: int,
    ) -> tuple:
        """Normalise a single ``StepSpec`` into ``(note, velocity, gate)``.

        ``step`` may be:

        * ``int``  → ``(step, default_velocity, default_gate)``
        * ``dict`` → ``(step["note"], step.get("velocity", default_velocity),
                        step.get("gate", default_gate))``

        Raises :class:`ValueError` for any other type or for out-of-range
        note / velocity / gate. ``bool`` is rejected explicitly even
        though it is a subclass of ``int`` — a True/False at step level
        is almost always a bug.
        """
        if isinstance(step, bool) or not isinstance(step, (int, dict)):
            raise ValueError(
                f"step at index {step_num} must be int or dict, "
                f"got {type(step).__name__}"
            )

        if isinstance(step, int):
            note = step
            vel = default_velocity
            g = default_gate
        else:
            # Dict path.
            if "note" not in step:
                raise ValueError(
                    f"step at index {step_num} is a dict but missing "
                    f"required 'note' key (keys={sorted(step.keys())})"
                )
            note = step["note"]
            vel = step.get("velocity", default_velocity)
            g = step.get("gate", default_gate)

        # Range checks.
        self._validate_note(note, label=f"step[{step_num}].note")
        self._validate_velocity(vel, label=f"step[{step_num}].velocity")
        self._validate_gate(g, label=f"step[{step_num}].gate")

        return note, vel, g

    # ------------------------------------------------------------------
    # Internal: per-step dispatch — SKELETON
    # ------------------------------------------------------------------

    def _send_step(
        self,
        track: int,
        step_num: int,
        note: int,
        vel: int,
        gate: int,
    ) -> bool:
        """Dispatch a single step to the device.

        TEMPLATE - NEEDS MC-707 MIDI CHART VERIFICATION
        -------------------------------------------------
        The skeleton below emits **one DT1 frame** plus the
        ``note_on`` / ``note_off`` pair used by the mock-mode test
        surface. On the real MC-707 each step typically needs **multiple
        coordinated DT1 blocks** to set:

          - Note number       (0x00..0x7F)
          - Velocity          (0x01..0x7F)
          - Gate length       (0x01..0x7F, percent of step duration)
          - Micro-Offset      (-24..+24 ticks, signed 7-bit)
          - Probability       (0x00..0x7F)
          - Ratchet count     (0..N)
          - Accent / Swing flags

        Without the official MIDI Implementation Chart we cannot
        address those fields correctly. The frame below covers only
        ``(step_num, note, vel, gate)`` as a best-effort placeholder;
        the remaining fields are TODO and must be wired in once the
        address map is known.

        In mock mode the DT1 frame is logged alongside a Note-On /
        Note-Off pair so the verification script has both shapes to
        inspect.
        """
        # Skeleton DT1 frame (educated-guess address; see module
        # docstring). Address = (0x19, 0x10, track - 1).
        # NOTE: this is **NOT** a verified Roland MC-707 address — it
        # is a placeholder for the per-step pattern data area.
        addr0, addr1, addr2 = 0x19, 0x10, (track - 1) & 0x7F
        frame: List[int] = [
            0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x6A,
            self._DT1_CMD,
            addr0, addr1, addr2,
            step_num & 0x7F,
            note & 0x7F,
            vel & 0x7F,
            gate & 0x7F,
            0xF7,
        ]

        ok_sysex = self._midi.send_sysex(frame)

        # Also emit the Note-On / Note-Off pair that the rest of the
        # controllers (and the mock-mode test surface) rely on. The
        # pair travels on the track's MIDI channel.
        channel = self._track_channel(track)
        ok_on = self._midi.send_note_on(channel, note, vel)
        ok_off = self._midi.send_note_off(channel, note)

        return ok_sysex and ok_on and ok_off

    # ------------------------------------------------------------------
    # Internal: validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_int(name: str, value: Any, low: int, high: int) -> int:
        """Reject ``bool`` and out-of-range ``int`` with ``ValueError``."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"{name} must be an int in {low}..{high}, "
                f"got {type(value).__name__}"
            )
        if value < low or value > high:
            raise ValueError(
                f"{name} must be between {low} and {high} (inclusive), "
                f"got {value}"
            )
        return value

    def _validate_track(self, track: int) -> int:
        """Validate that ``track`` is in 1..8 and return it unchanged."""
        return self._validate_int("track", track, self.MIN_TRACK, self.MAX_TRACK)

    def _validate_note(self, note: int, label: str = "note") -> int:
        """Validate that ``note`` is in 0..127 (0 = rest is allowed)."""
        return self._validate_int(label, note, self.MIN_NOTE, self.MAX_NOTE)

    def _validate_velocity(self, vel: int, label: str = "velocity") -> int:
        """Validate that ``vel`` is in 1..127 (0 is MIDI for Note-Off)."""
        return self._validate_int(label, vel, self.MIN_VELOCITY, self.MAX_VELOCITY)

    def _validate_gate(self, gate: int, label: str = "gate") -> int:
        """Validate that ``gate`` is in 1..127 (percent of step)."""
        return self._validate_int(label, gate, self.MIN_GATE, self.MAX_GATE)

    def _validate_pattern(self, pattern_number: int) -> int:
        """Validate that ``pattern_number`` is in 0..127."""
        return self._validate_int(
            "pattern_number", pattern_number, self.MIN_PATTERN, self.MAX_PATTERN,
        )

    def _track_channel(self, track: int) -> int:
        """Map an MC-707 track index to its MIDI channel (1-based).

        Track 1 → channel 10, Track 8 → channel 17. Result is the
        1-based channel number expected by :meth:`MIDIIO.send_note_on`
        / :meth:`MIDIIO.send_note_off`.
        """
        return track + self.TRACK_CHANNEL_OFFSET