"""Sound / tone data models for the MC-707.

This module defines the structured representation of an MC-707 Tone /
Instrument using Pydantic v2. The models are intentionally narrow — only
the most-used Tone parameters are exposed — to keep the surface area
small and the JSON round-trip predictable.

SCOPE
-----
A Tone on the MC-707 has hundreds of editable parameters. This module
covers the **19 most-frequently-used parameters** spread across the five
standard synth sections:

  * Oscillator (wave, pitch, level)
  * Filter (type, cutoff, resonance, env amount)
  * Amplitude envelope (A, D, S, R)
  * Filter envelope (A, D, S, R, amount)
  * LFO (rate, depth, target)

Anything beyond this scope (MFX detail, partial editing, per-step
sequence data, …) is intentionally **not** modelled here. Extend the
section sub-models and update ``Sound.to_param_dict`` /
``Sound.from_param_dict`` to grow the surface.

EDUCATED GUESS MARKERS
----------------------
Every numeric range below follows the standard 7-bit MIDI convention
(0..127), except where signed ranges are explicitly noted
(``filter.env_amount``, ``filter_envelope.amount``: −64..+63). They have
NOT been verified against the official MC-707 MIDI Implementation
Chart. The MC-707 may use 14-bit values for some parameters (cutoff,
pitch) — we currently model them as a single 7-bit byte and document
this limitation here.

ROLES
-----
* :class:`Sound` is the addressable unit used by :class:`SoundEditor`
  for live parameter editing via SysEx DT1.
* ``Sound.to_param_dict`` / ``Sound.from_param_dict`` provide the
  canonical mapping between the structured model and the flat parameter
  namespace consumed by the editor. The mapping tables
  (``_WAVE_TO_ID`` etc.) are EDUCATED GUESSES — verify the IDs against
  the MIDI Implementation Chart.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Waveform = Literal["sine", "triangle", "saw", "square", "pulse", "noise"]
FilterType = Literal["lpf", "hpf", "bpf"]
LfoTarget = Literal["pitch", "cutoff", "amp", "pan"]
SoundCategory = Literal[
    "lead", "bass", "pad", "pluck", "keys", "fx", "drum", "other"
]

# ---------------------------------------------------------------------------
# ID mapping tables — TEMPLATE / EDUCATED GUESS
# ---------------------------------------------------------------------------
# These map between the human-friendly enum values used by the Sound model
# and the integer IDs the MC-707 expects over MIDI. The assignments below
# follow the standard Roland tone-edit convention but have NOT been
# verified against the MC-707 MIDI Implementation Chart. Adjust when the
# real device IDs are known.

_WAVE_TO_ID: dict[str, int] = {
    "sine": 0,
    "triangle": 1,
    "saw": 2,
    "square": 3,
    "pulse": 4,
    "noise": 5,
}
_ID_TO_WAVE: dict[int, str] = {v: k for k, v in _WAVE_TO_ID.items()}

_FILTER_TO_ID: dict[str, int] = {"lpf": 0, "hpf": 1, "bpf": 2}
_ID_TO_FILTER: dict[int, str] = {v: k for k, v in _FILTER_TO_ID.items()}

_LFO_TARGET_TO_ID: dict[str, int] = {"pitch": 0, "cutoff": 1, "amp": 2, "pan": 3}
_ID_TO_LFO_TARGET: dict[int, str] = {v: k for k, v in _LFO_TARGET_TO_ID.items()}


# ---------------------------------------------------------------------------
# Section sub-models
# ---------------------------------------------------------------------------


class OscillatorParams(BaseModel):
    """OSC section: waveform, pitch (semitones), level (0..127).

    ``pitch`` is signed (−24..+24 semitones); ``level`` is unsigned.
    """

    model_config = ConfigDict(extra="forbid")

    wave: Waveform = "saw"
    pitch: int = Field(0, ge=-24, le=24, description="Semitone offset")
    level: int = Field(100, ge=0, le=127)


class FilterParams(BaseModel):
    """Filter section: type, cutoff, resonance, envelope amount.

    ``env_amount`` is signed (−64..+63) per typical synth convention.
    Verify against the MC-707 spec — the device may use a different
    signed range or store it as two unsigned bytes.
    """

    model_config = ConfigDict(extra="forbid")

    type: FilterType = "lpf"
    cutoff: int = Field(64, ge=0, le=127)
    resonance: int = Field(0, ge=0, le=127)
    env_amount: int = Field(32, ge=-64, le=63)


class AmpEnvelope(BaseModel):
    """Amplitude ADSR envelope. All four stages are 0..127."""

    model_config = ConfigDict(extra="forbid")

    attack: int = Field(0, ge=0, le=127)
    decay: int = Field(64, ge=0, le=127)
    sustain: int = Field(96, ge=0, le=127)
    release: int = Field(64, ge=0, le=127)


class FilterEnvelope(BaseModel):
    """Filter ADSR envelope + amount. ``amount`` is signed (−64..+63)."""

    model_config = ConfigDict(extra="forbid")

    attack: int = Field(0, ge=0, le=127)
    decay: int = Field(64, ge=0, le=127)
    sustain: int = Field(64, ge=0, le=127)
    release: int = Field(64, ge=0, le=127)
    amount: int = Field(32, ge=-64, le=63)


class LFOParams(BaseModel):
    """LFO: rate, depth, sync flag, modulation target.

    ``sync`` is a TEMPLATE flag — the MC-707 may use tempo-sync per-LFO
    via a separate parameter; treat this as the most-likely shape.
    """

    model_config = ConfigDict(extra="forbid")

    rate: int = Field(32, ge=0, le=127)
    depth: int = Field(0, ge=0, le=127)
    sync: bool = False
    target: LfoTarget = "pitch"


# ---------------------------------------------------------------------------
# Top-level Sound
# ---------------------------------------------------------------------------


class Sound(BaseModel):
    """An MC-707 Tone / Instrument definition.

    Combines the five per-section parameter models into one addressable
    unit. Use ``Sound.model_dump_json()`` / ``Sound.model_validate_json()``
    for persistence (handled by :class:`SoundStore`).
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field("Init", min_length=1, max_length=32)
    category: SoundCategory = "other"
    oscillator: OscillatorParams = Field(default_factory=OscillatorParams)
    filter: FilterParams = Field(default_factory=FilterParams)
    amp_envelope: AmpEnvelope = Field(default_factory=AmpEnvelope)
    filter_envelope: FilterEnvelope = Field(default_factory=FilterEnvelope)
    lfo: LFOParams = Field(default_factory=LFOParams)

    # ------------------------------------------------------------------
    # Param-dict projection (used by SoundEditor)
    # ------------------------------------------------------------------

    def to_param_dict(self) -> dict[str, int]:
        """Flatten the Sound to ``{param_name: value}``.

        The output is consumed by :class:`SoundEditor` for live DT1
        dispatch. The key set is fixed and is the canonical parameter
        namespace — see :data:`mc707.control.sound_editor.PARAM_ADDRESSES`.

        Signed fields (pitch, env_amount) are shifted into the unsigned
        7-bit MIDI range via ``value + 64``. Enum fields are mapped to
        integer IDs via the module-level tables above.
        """
        return {
            # OSC
            "osc_wave": _WAVE_TO_ID[self.oscillator.wave],
            "osc_pitch": self._shift_signed(self.oscillator.pitch),
            "osc_level": self.oscillator.level,
            # Filter
            "filter_type": _FILTER_TO_ID[self.filter.type],
            "filter_cutoff": self.filter.cutoff,
            "filter_resonance": self.filter.resonance,
            "filter_env_amount": self._shift_signed(self.filter.env_amount),
            # Amp envelope
            "amp_attack": self.amp_envelope.attack,
            "amp_decay": self.amp_envelope.decay,
            "amp_sustain": self.amp_envelope.sustain,
            "amp_release": self.amp_envelope.release,
            # Filter envelope
            "filter_env_attack": self.filter_envelope.attack,
            "filter_env_decay": self.filter_envelope.decay,
            "filter_env_sustain": self.filter_envelope.sustain,
            "filter_env_release": self.filter_envelope.release,
            "filter_env_amount_total": self._shift_signed(self.filter_envelope.amount),
            # LFO
            "lfo_rate": self.lfo.rate,
            "lfo_depth": self.lfo.depth,
            "lfo_target": _LFO_TARGET_TO_ID[self.lfo.target],
        }

    @classmethod
    def from_param_dict(cls, params: dict[str, int]) -> "Sound":
        """Build a Sound from a ``{param_name: value}`` dict.

        Missing keys fall back to model defaults. Unknown keys are
        silently ignored — extending the parameter surface only requires
        updating this method (and :meth:`to_param_dict`). Out-of-range
        values are clamped into each sub-model's allowed range so the
        result is always a valid Sound.
        """
        sound = cls()

        def u(name: str, default: int, lo: int = 0, hi: int = 127) -> int:
            if name not in params:
                return default
            return max(lo, min(hi, int(params[name])))

        # OSC
        if "osc_wave" in params:
            sound.oscillator.wave = _ID_TO_WAVE.get(int(params["osc_wave"]), "sine")  # type: ignore[arg-type]
        if "osc_pitch" in params:
            sound.oscillator.pitch = max(-24, min(24, int(params["osc_pitch"]) - 64))
        sound.oscillator.level = u("osc_level", sound.oscillator.level)

        # Filter
        if "filter_type" in params:
            sound.filter.type = _ID_TO_FILTER.get(int(params["filter_type"]), "lpf")  # type: ignore[arg-type]
        sound.filter.cutoff = u("filter_cutoff", sound.filter.cutoff)
        sound.filter.resonance = u("filter_resonance", sound.filter.resonance)
        if "filter_env_amount" in params:
            sound.filter.env_amount = max(
                -64, min(63, int(params["filter_env_amount"]) - 64)
            )

        # Amp envelope
        sound.amp_envelope.attack = u("amp_attack", sound.amp_envelope.attack)
        sound.amp_envelope.decay = u("amp_decay", sound.amp_envelope.decay)
        sound.amp_envelope.sustain = u("amp_sustain", sound.amp_envelope.sustain)
        sound.amp_envelope.release = u("amp_release", sound.amp_envelope.release)

        # Filter envelope
        sound.filter_envelope.attack = u("filter_env_attack", sound.filter_envelope.attack)
        sound.filter_envelope.decay = u("filter_env_decay", sound.filter_envelope.decay)
        sound.filter_envelope.sustain = u("filter_env_sustain", sound.filter_envelope.sustain)
        sound.filter_envelope.release = u("filter_env_release", sound.filter_envelope.release)
        if "filter_env_amount_total" in params:
            sound.filter_envelope.amount = max(
                -64, min(63, int(params["filter_env_amount_total"]) - 64)
            )

        # LFO
        sound.lfo.rate = u("lfo_rate", sound.lfo.rate)
        sound.lfo.depth = u("lfo_depth", sound.lfo.depth)
        if "lfo_target" in params:
            sound.lfo.target = _ID_TO_LFO_TARGET.get(int(params["lfo_target"]), "pitch")  # type: ignore[arg-type]

        return sound

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _shift_signed(value: int) -> int:
        """Shift a signed value in −64..+63 into unsigned 7-bit (0..127).

        Used for fields like ``oscillator.pitch`` and ``env_amount``
        which the MC-707 represents as a single unsigned byte where 64
        means "zero".
        """
        return max(0, min(127, value + 64))


__all__ = [
    "AmpEnvelope",
    "FilterEnvelope",
    "FilterParams",
    "LFOParams",
    "LfoTarget",
    "OscillatorParams",
    "Sound",
    "SoundCategory",
    "Waveform",
]