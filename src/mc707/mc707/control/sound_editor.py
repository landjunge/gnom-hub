"""Live parameter editing for MC-707 Sounds via SysEx DT1.

Maps high-level parameter names (the keys of
:meth:`Sound.to_param_dict`) to SysEx DT1 frames and dispatches them
through :class:`SysExController`. The mapping is centralised in
:data:`PARAM_ADDRESSES` so the surface is easy to extend and audit.

TEMPLATE MARKERS
----------------
**Every entry in** :data:`PARAM_ADDRESSES` **is an EDUCATED GUESS**
derived from a generic Roland tone-edit parameter layout. The MC-707
may use different block IDs and offsets — verify each entry against the
official MIDI Implementation Chart before relying on it for live
hardware edits.

VERIFY HOOK
-----------
The dispatch path is exercised by ``tests/test_sound_system.py``: each
``set_param(name, value)`` call must produce a real DT1 SysEx frame in
the MIDI log (mock-mode), not silently swallow the value. The cache
update happens **only** after a successful dispatch, so a failing
``send_dt1`` is observable via :meth:`get_param` returning ``None``.

READ-BACK LIMITATION  (TODO / TEMPLATE)
---------------------------------------
``get_param`` and :meth:`capture` are **cache-only** — they reflect
only the values this process wrote via ``set_param`` / ``apply``.
The MC-707 UI / Web-UI cannot use them to display the *actual* current
device state.

A real read-back needs:

  1. Issue RQ1 for a known parameter address.
  2. Wait asynchronously for the matching DT1 response (midimux /
     ``mido`` port polling, or a callback registered on
     :class:`StatusController`).
  3. Parse the 2-byte payload out of the response frame.

This is **TODO** for a later track (planned for Track 4 — WebUI live
state display) and is marked **TEMPLATE** here because the MC-707 DT1
response format (single-param vs. bulk dump, byte order for 14-bit
values) needs verification against the MIDI Implementation Chart.

Until then:

  * The WebUI MUST show "(cached — last written by this session)"
    next to slider values, never pretend it knows the live state.
  * Live monitoring of the device should go through
    :class:`StatusController` callbacks, not through this editor.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

from ..models.sound import Sound

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parameter address table
# ---------------------------------------------------------------------------
#
# Address shape: (block_hi, block_lo, param_offset).
#
# EDUCATED GUESS — the MC-707 layout is assumed to follow a generic
# Roland tone-edit structure:
#
#   0x18 0x00  = OSC block
#   0x18 0x10  = Filter block
#   0x18 0x20  = Amp envelope block
#   0x18 0x30  = Filter envelope block
#   0x18 0x40  = LFO block
#
# The exact addresses need verification against the MC-707 MIDI
# Implementation Chart.

PARAM_ADDRESSES: Dict[str, Tuple[int, int, int]] = {
    # OSC block ----------------------------------------------------------
    "osc_wave":          (0x18, 0x00, 0x00),
    "osc_pitch":         (0x18, 0x00, 0x01),
    "osc_level":         (0x18, 0x00, 0x02),
    # Filter block -------------------------------------------------------
    "filter_type":       (0x18, 0x10, 0x00),
    "filter_cutoff":     (0x18, 0x10, 0x01),
    "filter_resonance":  (0x18, 0x10, 0x02),
    "filter_env_amount": (0x18, 0x10, 0x03),
    # Amp envelope block -------------------------------------------------
    "amp_attack":        (0x18, 0x20, 0x00),
    "amp_decay":         (0x18, 0x20, 0x01),
    "amp_sustain":       (0x18, 0x20, 0x02),
    "amp_release":       (0x18, 0x20, 0x03),
    # Filter envelope block ---------------------------------------------
    "filter_env_attack":       (0x18, 0x30, 0x00),
    "filter_env_decay":        (0x18, 0x30, 0x01),
    "filter_env_sustain":      (0x18, 0x30, 0x02),
    "filter_env_release":      (0x18, 0x30, 0x03),
    "filter_env_amount_total": (0x18, 0x30, 0x04),
    # LFO block ----------------------------------------------------------
    "lfo_rate":          (0x18, 0x40, 0x00),
    "lfo_depth":         (0x18, 0x40, 0x01),
    "lfo_target":        (0x18, 0x40, 0x02),
}


class SoundEditor:
    """Live parameter editor for MC-707 Sounds.

    Wraps :class:`SysExController` and provides a name-based API on top
    of the low-level DT1 dispatch. Writes update an internal cache so
    :meth:`get_param` / :meth:`capture` reflect the most-recently
    successful values within the session.

    Parameters
    ----------
    sysex_controller:
        A :class:`mc707.io.sysex.SysExController`
        instance used to dispatch DT1 frames.
    """

    def __init__(self, sysex_controller) -> None:
        self._sysex = sysex_controller
        self._cache: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    @staticmethod
    def known_params() -> list[str]:
        """Return the parameter names this editor can address."""
        return list(PARAM_ADDRESSES.keys())

    @staticmethod
    def address_of(name: str) -> Tuple[int, int, int]:
        """Return the SysEx address tuple for a known parameter name."""
        if name not in PARAM_ADDRESSES:
            raise ValueError(
                f"Unknown parameter {name!r}. Known: {sorted(PARAM_ADDRESSES.keys())}"
            )
        return PARAM_ADDRESSES[name]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate(name: str, value: int) -> None:
        """Raise ``ValueError`` if *name* is unknown or *value* is out of range.

        All wire values are 7-bit unsigned (0..127); signed Sound fields
        are shifted into that range by :meth:`Sound.to_param_dict`
        before reaching the editor.
        """
        if name not in PARAM_ADDRESSES:
            raise ValueError(
                f"Unknown parameter {name!r}. Known: {sorted(PARAM_ADDRESSES.keys())}"
            )
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"value must be int, got {type(value).__name__}")
        if not (0 <= value <= 127):
            raise ValueError(f"value for {name!r} must be in 0..127, got {value}")

    # ------------------------------------------------------------------
    # Single-parameter read / write
    # ------------------------------------------------------------------

    def set_param(self, name: str, value: int) -> bool:
        """Write a single parameter to the device via SysEx DT1.

        Returns ``True`` on successful dispatch, ``False`` on dispatch
        failure. On success the cache is updated so subsequent
        :meth:`get_param` / :meth:`capture` calls see the new value.
        On failure the cache is left untouched.
        """
        self.validate(name, value)
        address = PARAM_ADDRESSES[name]
        ok = self._sysex.send_dt1(address, [value, 0])
        if ok:
            self._cache[name] = value
            logger.info("set_param %s = %d (addr=%s)", name, value, address)
        else:
            logger.error(
                "set_param %s = %d FAILED (addr=%s)", name, value, address
            )
        return ok

    # TODO (Track 4 / WebUI): replace cache-only implementation with a
    # real RQ1 round-trip (request → wait for DT1 response → parse).
    # Until then the WebUI must label any value shown to the user as
    # "cached, last written by this session" — never as live device state.
    def get_param(self, name: str) -> Optional[int]:
        """Return the most-recently-written value, or ``None`` if unset.

        TEMPLATE — cache-only. A live RQ1 read-back would need response
        framing and is out of scope. See module docstring.
        """
        return self._cache.get(name)

    def cached_params(self) -> dict[str, int]:
        """Return a copy of the full param cache."""
        return dict(self._cache)

    def clear_cache(self) -> None:
        """Reset the param cache. Does not touch the device."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def apply(self, sound: Sound) -> bool:
        """Push every parameter from a Sound to the device via DT1.

        Returns ``True`` only if every parameter dispatched
        successfully. A single failure short-circuits the loop and
        returns ``False`` — partial dispatch is observable via
        :meth:`cached_params` (succeeded) vs. unset keys (failed).
        """
        ok_all = True
        for name, value in sound.to_param_dict().items():
            ok_all = self.set_param(name, value) and ok_all
        return ok_all

    def apply_partial(self, sound: Sound, params: list[str]) -> bool:
        """Push only the listed parameters from *sound*, preserving order.

        Raises ``ValueError`` if any name in *params* is not present in
        ``sound.to_param_dict()``. Dispatch failure of a single param
        short-circuits and returns ``False``.
        """
        values = sound.to_param_dict()
        for name in params:
            if name not in values:
                raise ValueError(
                    f"Param {name!r} not in Sound {sound.name!r}"
                )
        ok_all = True
        for name in params:
            ok_all = self.set_param(name, values[name]) and ok_all
        return ok_all

    # TODO (Track 4 / WebUI): replace cache-only implementation with a
    # real RQ1 round-trip. See module docstring for the design notes
    # (response framing, 14-bit handling, StatusController integration).
    def capture(self, template: Optional[Sound] = None) -> Sound:
        """Return a Sound populated from the local cache.

        TEMPLATE — full hardware capture would require RQ1 round-trip
        handling (request → wait for DT1 response → parse). This method
        returns a Sound reflecting only the params previously written
        via :meth:`set_param` / :meth:`apply` / :meth:`apply_partial`;
        unset keys fall back to model defaults.

        Parameters
        ----------
        template:
            Optional reference Sound. If provided, its ``name``,
            ``category``, and other metadata fields are preserved on the
            returned Sound — only the per-section parameter sub-models
            are replaced with the cached values. If ``None`` (the
            default), the returned Sound has the model's default
            metadata; pass the Sound you last applied to round-trip the
            full identity.
        """
        cached = Sound.from_param_dict(self._cache)
        if template is None:
            return cached
        # Preserve the template's metadata; overwrite only the
        # parameter sections with the cached values.
        return template.model_copy(
            update={
                "oscillator": cached.oscillator,
                "filter": cached.filter,
                "amp_envelope": cached.amp_envelope,
                "filter_envelope": cached.filter_envelope,
                "lfo": cached.lfo,
            }
        )


__all__ = ["PARAM_ADDRESSES", "SoundEditor"]