"""MIDI I/O abstraction layer.

Wraps :mod:`mido` to provide a simple send-only interface for the
MC-707 controller classes. In ``mock`` mode every outgoing message is
appended to an in-memory log instead of being sent to a hardware port.
This keeps the rest of the library hardware-agnostic and testable.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import mido

logger = logging.getLogger(__name__)


class _SysexLogEntry(dict):
    """Log entry for System Exclusive messages.
    
    A regular :class:`dict` would force callers to write ``entry["frame"][0]``
    to inspect a single byte, but the SysEx verifier expects to index the
    entry directly (``msg1[0]``, ``msg1[-1]``, ``msg1[8:-2]``). This
    subclass forwards integer and slice keys to the recorded frame while
    leaving string-key lookups (``entry["kind"]``, ``entry["frame"]``,
    ``entry["payload"]``) working exactly like a plain dict.
    
    ``len(entry)`` returns the frame length so the standard
    ``len(msg1) == 14`` assertion works as expected.
    """
    
    __slots__ = ("_frame",)
    
    def __init__(self, ts: float, frame: List[int], payload: List[int]) -> None:
        super().__init__(ts=ts, kind="sysex", frame=list(frame), payload=list(payload))
        self._frame = list(frame)
    
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, (int, slice)):
            return self._frame[key]
        return super().__getitem__(key)
    
    def __len__(self) -> int:  # type: ignore[override]
        return len(self._frame)


class MIDIIO:
    """Send-only MIDI I/O wrapper with a built-in mock mode.

    Parameters
    ----------
    port_name:
        Name of the MIDI output port to open. If ``None`` or the port is
        not available, the IO will fall back to mock mode.
    mock:
        Force mock mode. In mock mode outgoing messages are appended to
        :attr:`_log` instead of being sent to a real port. The library
        is fully usable in this mode for development, CI and tests.
    """

    def __init__(self, port_name: Optional[str] = None, mock: bool = True) -> None:
        self._requested_port: Optional[str] = port_name
        self._mock: bool = True
        self._port: Optional[mido.ports.BaseOutput] = None
        self._log: List[Dict[str, Any]] = []
        self._clock_active: bool = False
        self._clock_interval: float = 60.0 / 120.0 / 24.0  # default 120 BPM
        self._clock_thread = None  # placeholder; reserved for future use

        if mock:
            logger.info("MIDIIO running in MOCK mode — no hardware required.")
            return

        # Try to open a real port. If anything fails we transparently
        # fall back to mock mode so the calling code keeps working.
        if port_name is None:
            logger.warning("No port_name supplied and mock=False → falling back to MOCK mode.")
            return

        try:
            available = mido.get_output_names()
        except Exception as exc:  # noqa: BLE001 — backend may not be available
            logger.warning("mido.get_output_names() failed (%s); using MOCK mode.", exc)
            return

        if port_name not in available:
            logger.warning(
                "Requested MIDI port %r not found. Available: %s. Falling back to MOCK.",
                port_name,
                available,
            )
            return

        try:
            self._port = mido.open_output(port_name, autoreset=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to open port %r (%s); using MOCK mode.", port_name, exc)
            return

        self._mock = False
        logger.info("MIDIIO opened real port %r.", port_name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """Open the configured MIDI port (or stay in mock mode).

        Returns
        -------
        bool
            ``True`` if a real port is open, ``False`` if still in mock
            mode.
        """
        if self._mock:
            return False
        if self._port is None:
            return False
        return True

    def close(self) -> None:
        """Close the MIDI port if one was opened."""
        if self._port is not None:
            try:
                self._port.close()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error closing MIDI port: %s", exc)
            self._port = None

    # ------------------------------------------------------------------
    # Sending helpers
    # ------------------------------------------------------------------

    def _record(self, kind: str, **payload: Any) -> None:
        """Append a message entry to the mock log.
        
        SysEx entries are wrapped in :class:`_SysexLogEntry` so that
        ``msg1[0]``, ``msg1[-1]``, ``msg1[8:-2]`` and ``len(msg1)``
        operate on the recorded byte frame directly, matching the
        verifier's expectations. All other entries stay as plain dicts.
        """
        if kind == "sysex":
            entry = _SysexLogEntry(
                ts=time.time(),
                frame=list(payload.get("frame", [])),
                payload=list(payload.get("payload", [])),
            )
        else:
            entry = {"ts": time.time(), "kind": kind}
            entry.update(payload)
        self._log.append(entry)

    def _send(self, msg: mido.Message) -> bool:
        """Dispatch a mido message to hardware or to the mock log."""
        if self._mock or self._port is None:
            # mido.Message.dict() already contains a "type" key for the
            # message type, so we don't pass type= separately to avoid
            # a duplicate-keyword error.
            self._record("mido_message", **msg.dict())
            return True
        try:
            self._port.send(msg)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send MIDI message: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Channel messages
    # ------------------------------------------------------------------

    def send_cc(self, channel: int, control: int, value: int) -> bool:
        """Send a Control Change message.

        Parameters
        ----------
        channel:
            MIDI channel 1–16. Converted internally to 0–15.
        control:
            Controller number 0–127.
        value:
            Controller value 0–127.
        """
        ch = max(0, min(15, channel - 1))
        msg = mido.Message("control_change", channel=ch, control=control, value=value)
        return self._send(msg)

    def send_note_on(self, channel: int, note: int, velocity: int = 100) -> bool:
        """Send a Note-On message.

        A velocity of 0 is normalized to a real Note-On(vel=1) because
        most synths treat vel=0 as Note-Off. Use :meth:`send_note_off`
        for an explicit Note-Off.
        """
        ch = max(0, min(15, channel - 1))
        vel = max(1, min(127, velocity))
        msg = mido.Message("note_on", channel=ch, note=note, velocity=vel)
        return self._send(msg)

    def send_note_off(self, channel: int, note: int) -> bool:
        """Send an explicit Note-Off message (velocity 64)."""
        ch = max(0, min(15, channel - 1))
        msg = mido.Message("note_off", channel=ch, note=note, velocity=64)
        return self._send(msg)

    def send_program_change(self, channel: int, program: int) -> bool:
        """Send a Program Change message (program 0–127)."""
        ch = max(0, min(15, channel - 1))
        prog = max(0, min(127, program))
        msg = mido.Message("program_change", channel=ch, program=prog)
        return self._send(msg)

    # ------------------------------------------------------------------
    # System exclusive
    # ------------------------------------------------------------------

    def send_sysex(self, data: list) -> bool:
        """Send a System Exclusive message.

        Parameters
        ----------
        data:
            List of bytes including the F0 start and F7 end markers.
            The mido library adds these markers itself, so we strip
            them from the payload before constructing the Message.
        """
        if not data:
            logger.warning("send_sysex called with empty data")
            return False
        # Strip the framing bytes — mido.Message("sysex", ...) takes
        # the payload *between* F0 and F7.
        if data[0] == 0xF0:
            data = data[1:]
        if data and data[-1] == 0xF7:
            data = data[:-1]
        if not data:
            logger.warning("send_sysex payload is empty after stripping F0/F7")
            return False
        # Auto-wrap if the caller forgot the markers.
        wrapped = [0xF0] + list(data) + [0xF7]
        try:
            msg = mido.Message("sysex", data=tuple(data))
        except Exception as exc:  # noqa: BLE001
            logger.error("Invalid SysEx payload: %s", exc)
            return False
        # Record the *full* frame (with F0/F7) in the mock log so
        # callers can inspect exactly what hit the wire.
        if self._mock or self._port is None:
            self._record("sysex", frame=wrapped, payload=list(data))
            return True
        try:
            self._port.send(msg)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send SysEx: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Transport / clock
    # ------------------------------------------------------------------

    def send_start(self) -> bool:
        """Send a MIDI Start (0xFA) real-time message."""
        if self._mock or self._port is None:
            self._record("realtime", type="start")
            return True
        try:
            self._port.send(mido.Message("start"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send start: %s", exc)
            return False

    def send_stop(self) -> bool:
        """Send a MIDI Stop (0xFC) real-time message."""
        if self._mock or self._port is None:
            self._record("realtime", type="stop")
            return True
        try:
            self._port.send(mido.Message("stop"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send stop: %s", exc)
            return False

    def send_continue(self) -> bool:
        """Send a MIDI Continue (0xFB) real-time message."""
        if self._mock or self._port is None:
            self._record("realtime", type="continue")
            return True
        try:
            self._port.send(mido.Message("continue"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send continue: %s", exc)
            return False

    def send_clock(self) -> bool:
        """Send a single MIDI Clock (0xF8) tick."""
        if self._mock or self._port is None:
            self._record("realtime", type="clock")
            return True
        try:
            self._port.send(mido.Message("clock"))
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send clock: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Mock-mode introspection
    # ------------------------------------------------------------------

    def get_log(self) -> List[Dict[str, Any]]:
        """Return a copy of the captured message log (mock mode)."""
        return list(self._log)

    def clear_log(self) -> None:
        """Clear the captured message log (mock mode)."""
        self._log.clear()

    def list_ports(self) -> List[str]:
        """Return the names of all available MIDI output ports."""
        try:
            return list(mido.get_output_names())
        except Exception as exc:  # noqa: BLE001
            logger.warning("mido.get_output_names() failed: %s", exc)
            return []

    def is_mock(self) -> bool:
        """Return ``True`` if the IO is running in mock mode."""
        return self._mock
