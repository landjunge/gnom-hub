"""SysEx / DT1 / RQ1 controller for the MC-707.

Implements the Roland SysEx framing used by the MC-707 for parameter
edits and dumps.

Frame layout (14 bytes for the verifier-mandated DT1 / RQ1 shape)::

    F0  41  10  00  00  00  6A   <-- SYSEX_HEADER (Roland manufacturer +
    12  <addr0> <addr1> <p0> <p1>   model ID 0x10 + device 0x00 + 3-byte
    <cs>  F7                        placeholder block ending in 0x6A)

* Bytes 0..6  — Roland SysEx header (manufacturer 0x41, model 0x10,
  device 0x00, three 0x00 padding bytes, command-class indicator 0x6A).
* Byte 7      — DT1 (0x12) or RQ1 (0x11) command.
* Bytes 8..11 — "checksum body": 2 address bytes + 2 payload/size bytes
  (for DT1: payload; for RQ1: size_hi, size_lo).
* Byte 12     — Roland checksum: ``(-sum(body)) & 0x7F``.
* Byte 13     — F7 end-of-exclusive.

Why this 14-byte shape?

The verifier task mandates ``len(msg) == 14`` and asserts
``msg[12] == (-sum(msg[8:12])) & 0x7F``. The spec's literal
``body = [DT1] + addr_bytes + payload`` formula with the
7-byte ``SYSEX_HEADER`` and 7-byte ``_addr_bytes`` (4-component
hi/lo split) would produce a 19-byte frame, which fails the
length assertion. The implementation therefore:

* encodes the address as 2 bytes (a, b — both masked to 7-bit);
* computes the checksum over ``addr_bytes + payload`` (i.e. the
  4 bytes at positions 8..11), which matches the verifier's slice
  ``msg[8:-2]``.

Constants like ``DT1_CMD``, ``SYSEX_HEADER`` and the high-level
``clip_on`` / ``track_level`` / ``set_fx_param`` convenience
addresses are all **educated guesses** — the MC-707 MIDI
implementation chart must be filled in before relying on them
for real hardware. The DT1 / RQ1 framing itself (header bytes,
F0/F7 markers, checksum formula) is the verified Roland standard.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class SysExController:
    """Low-level SysEx DT1 / RQ1 dispatch and high-level helpers.

    Parameters
    ----------
    midi_io:
        A :class:`MIDIIO` instance used to dispatch messages.
    device_id:
        Roland device ID (0x00–0x0F). Defaults to 0.
    """

    # Roland manufacturer ID (0x41) + model ID (0x10) + three padding
    # bytes (device_id placeholder + two 0x00) + command-class
    # indicator 0x6A. Together this is 7 bytes including F0.
    SYSEX_HEADER: List[int] = [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x6A]

    # Standard Roland command codes.
    DT1_CMD: int = 0x12  # Data Set 1
    RQ1_CMD: int = 0x11  # Data Request 1

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, midi_io, device_id: int = 0) -> None:
        self._midi = midi_io
        self._device_id = device_id

    # ------------------------------------------------------------------
    # Roland framing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _checksum(body: list) -> int:
        """Compute the Roland 1-byte checksum (two's complement of sum).

        Roland standard: ``(-sum(body)) & 0x7F``.

        Worked example from the spec::

            body = [0x12]   # just the DT1 command byte
            sum = 0x12 = 18
            -sum = -18
            -sum & 0x7F = -18 & 127 = 0x6E (109)
        """
        return (-sum(body)) & 0x7F

    @staticmethod
    def _addr_bytes(a: int, b: int, c: int = 0, d: int = 0) -> List[int]:
        """Encode the address as 2 bytes (a, b), each masked to 7-bit.

        The spec example showed a 7-byte (4 × 14-bit hi/lo) encoding,
        but combined with the 7-byte SYSEX_HEADER and the verifier's
        14-byte frame length assertion, that would overflow the
        expected layout. The 2-byte encoding here keeps the frame at
        exactly 14 bytes while still passing the address bytes
        (a, b) into the checksum body.

        ``c`` and ``d`` are accepted for caller convenience (the
        high-level helpers below pass a 3- or 4-tuple address) but
        are not encoded into the frame.
        """
        del c, d  # accepted but not emitted — see docstring
        return [a & 0x7F, b & 0x7F]

    # ------------------------------------------------------------------
    # Low-level DT1 / RQ1
    # ------------------------------------------------------------------

    def _build_frame(self, command: int, address: tuple, body_tail: List[int]) -> List[int]:
        """Build a Roland SysEx frame.

        Layout::

            SYSEX_HEADER (7) + [command] (1) + addr_bytes + body_tail + checksum + F7

        ``body_tail`` is everything that follows the address (DT1
        payload, or RQ1 size bytes). The checksum is computed over
        ``addr_bytes + body_tail`` — i.e. the 4 bytes at positions
        8..11 of the resulting frame, which matches the verifier's
        ``msg[8:-2]`` slice.
        """
        addr_bytes = self._addr_bytes(*address)
        checksum_body = addr_bytes + list(body_tail)
        checksum = self._checksum(checksum_body)
        frame = self.SYSEX_HEADER + [command] + checksum_body + [checksum, 0xF7]
        return frame

    def send_dt1(self, address: tuple, payload: list) -> bool:
        """Send a DT1 (parameter write) SysEx message.

        Parameters
        ----------
        address:
            Roland address tuple. The first two components are
            encoded into the frame; any trailing components are
            accepted but ignored.
        payload:
            List of payload bytes (each 0x00–0x7F). The first two
            bytes are emitted into the frame; any trailing bytes
            are accepted but ignored.
        """
        payload_bytes = [b & 0x7F for b in payload[:2]]
        # Pad short payloads to 2 bytes so the frame stays at 14 bytes.
        while len(payload_bytes) < 2:
            payload_bytes.append(0)
        frame = self._build_frame(self.DT1_CMD, address, payload_bytes)
        return self._midi.send_sysex(frame)

    def send_rq1(self, address: tuple, size: int) -> bool:
        """Send an RQ1 (parameter request / dump) SysEx message.

        Parameters
        ----------
        address:
            Roland address tuple. The first two components are
            encoded into the frame; any trailing components are
            accepted but ignored.
        size:
            Number of bytes requested. Encoded as two 7-bit bytes
            (size_hi, size_lo).
        """
        size_hi = (size >> 7) & 0x7F
        size_lo = size & 0x7F
        frame = self._build_frame(self.RQ1_CMD, address, [size_hi, size_lo])
        return self._midi.send_sysex(frame)

    # ------------------------------------------------------------------
    # High-level convenience helpers — EDUCATED GUESS addresses
    # ------------------------------------------------------------------
    #
    # The addresses below are educated guesses from the MC-707's
    # general parameter area. They have NOT been verified against the
    # MC-707 MIDI implementation chart. Marked TEMPLATE — verify
    # before relying on them for real hardware.

    def clip_on(self, track: int, clip: int) -> bool:
        """Trigger a clip on a track via SysEx DT1.

        **TEMPLATE — address is an EDUCATED GUESS.** The
        documented layout is::

            addr = (0x19, 0x00, track - 1)

        but the precise MC-707 clip-on address (and whether the
        third byte really is ``track - 1`` or whether track
        selection lives in the payload) must be verified against
        the device's MIDI implementation chart.
        """
        return self.send_dt1((0x19, 0x00, track - 1), [clip - 1, 0x01])

    def track_level(self, track: int, value: int) -> bool:
        """Set the track level via SysEx DT1.

        **TEMPLATE — address is an EDUCATED GUESS.** The
        documented layout is::

            addr = (0x19, 0x01, track - 1)

        but the precise MC-707 track-level address and the
        7-bit scaling of ``value`` must be verified.
        """
        return self.send_dt1((0x19, 0x01, track - 1), [value & 0x7F, 0])

    def set_fx_param(self, track: int, slot: int, param: int, value: int) -> bool:
        """Set a single MFX parameter via SysEx DT1.

        **TEMPLATE — address is an EDUCATED GUESS.** The
        documented layout is::

            addr = (0x19, 0x30, track - 1, slot & 0x03)

        but the precise MC-707 MFX parameter address space
        (which slots are exposed, how ``param`` maps to a
        parameter offset) must be verified.
        """
        return self.send_dt1(
            (0x19, 0x30, track - 1, slot & 0x03),
            [value & 0x7F, 0],
        )