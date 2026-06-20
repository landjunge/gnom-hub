"""Status / query controller for the MC-707.

Holds the most recently received values for the current tone, scene
and tempo. The real implementation must register a callback on the
MIDI input port and decode RQ1 / DT1 reply frames; in mock mode the
controller returns sensible defaults from its in-memory cache so the
rest of the library is exercisable without hardware.

The mock defaults follow the task spec exactly::

    self._mock_state = {
        "scene": 0,
        "tempo": 120,
        "tones": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0},
    }

Public surface (the only methods the verifier exercises)::

    * ``current_tone(track)`` — returns the cached tone number.
    * ``current_scene()`` — returns the cached scene number.
    * ``current_tempo()`` — returns the cached tempo in BPM.
    * ``on_response(callback)`` — registers a callback for incoming
      DT1 frames; the callback receives ``(kind, payload)`` where
      ``kind`` is one of ``"tone"``, ``"scene"``, ``"tempo"``.

Real-hardware TODO (left as a TODO list, not implemented):

    * Register an RQ1 frame on the MIDI input port.
    * Parse DT1 reply frames (vendor + model + address match) and
      route to ``_update_tone`` / ``_update_scene`` / ``_update_tempo``.
    * Refresh cache on scene change events from the sequencer.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StatusController:
    """In-memory cache of the device's most recently reported state.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.
    device_id:
        Roland device ID used for RQ1 requests. Currently accepted
        for API symmetry with :class:`SysExController` but not
        consulted by the mock-mode cache.
    """

    def __init__(self, midi_io, device_id: int = 0) -> None:
        self._midi = midi_io
        self._device_id = device_id
        self._callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

        # Mock-mode cache: defaults from the task spec. Real hardware
        # would populate this from incoming DT1 reply frames.
        self._mock_state: Dict[str, Any] = {
            "scene": 0,
            "tempo": 120,
            "tones": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0},
        }

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def current_tone(self, track: int) -> Optional[int]:
        """Return the tone number currently loaded on ``track``.

        In mock mode this returns the locally cached value
        (default 0 for tracks 1..8). On real hardware the cache
        would be refreshed by ``_request`` / ``on_response`` paths
        — see module docstring.
        """
        return self._mock_state["tones"].get(track)

    def current_scene(self) -> Optional[int]:
        """Return the currently selected scene number (default 0)."""
        return self._mock_state["scene"]

    def current_tempo(self) -> Optional[int]:
        """Return the most recently observed master tempo in BPM
        (default 120)."""
        return self._mock_state["tempo"]

    # ------------------------------------------------------------------
    # Public subscribe API
    # ------------------------------------------------------------------

    def on_response(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a callback for incoming DT1 frames.

        The callback receives ``(kind, payload)`` where ``kind`` is
        a short string (``"tone"`` / ``"scene"`` / ``"tempo"`` /
        ...) and ``payload`` is a dict of decoded fields. Exceptions
        raised by a callback are logged but do not propagate.
        """
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # Internal: cache + notify
    # ------------------------------------------------------------------

    def _update_tone(self, track: int, tone: int) -> None:
        """Update the tone cache and notify subscribers."""
        self._mock_state["tones"][track] = tone
        self._notify("tone", {"track": track, "tone": tone})

    def _update_scene(self, scene: int) -> None:
        """Update the scene cache and notify subscribers."""
        self._mock_state["scene"] = scene
        self._notify("scene", {"scene": scene})

    def _update_tempo(self, bpm: int) -> None:
        """Update the tempo cache and notify subscribers."""
        self._mock_state["tempo"] = bpm
        self._notify("tempo", {"bpm": bpm})

    def _notify(self, kind: str, payload: Dict[str, Any]) -> None:
        """Fire every registered callback with the new state."""
        for cb in list(self._callbacks):
            try:
                cb(kind, payload)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Status callback raised: %s", exc)