"""Tests for :mod:`mc707.io.sysex`.

Covers the DT1 / RQ1 frame construction, the Roland checksum formula,
the SYSEX_HEADER / command constants, and the high-level
``clip_on`` / ``track_level`` / ``set_fx_param`` convenience methods
(verified to dispatch via ``send_dt1``).
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.io.sysex import SysExController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# ---------------------------------------------------------------------------
# Class constants
# ---------------------------------------------------------------------------


def test_sysex_header_constant_is_seven_bytes() -> None:
    """The Roland header includes F0 + 6 prefix bytes (total 7)."""
    assert SysExController.SYSEX_HEADER == [0xF0, 0x41, 0x10, 0x00, 0x00, 0x00, 0x6A]
    assert len(SysExController.SYSEX_HEADER) == 7


def test_command_constants_match_roland_spec() -> None:
    """DT1 = 0x12, RQ1 = 0x11 per the Roland SysEx spec."""
    assert SysExController.DT1_CMD == 0x12
    assert SysExController.RQ1_CMD == 0x11


# ---------------------------------------------------------------------------
# Frame construction (DT1)
# ---------------------------------------------------------------------------


def test_dt1_frame_is_14_bytes(m: MC707) -> None:
    """A minimal DT1 frame is exactly 14 bytes."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    assert len(msg) == 14


def test_dt1_frame_starts_with_f0_and_ends_with_f7(m: MC707) -> None:
    """Every SysEx frame is bracketed by F0 and F7."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7


def test_dt1_frame_carries_dt1_command_byte(m: MC707) -> None:
    """Byte 7 is the DT1 command code 0x12."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    assert msg[7] == SysExController.DT1_CMD == 0x12


def test_dt1_frame_address_and_payload_are_at_positions_8_to_11(m: MC707) -> None:
    """Address (a, b) at positions 8..9, payload bytes at 10..11."""
    m.sysex.send_dt1((0x19, 0x05, 0), [0x42, 0x00])
    msg = m._midi.get_log()[-1]
    assert msg[8] == 0x19
    assert msg[9] == 0x05
    assert msg[10] == 0x42
    assert msg[11] == 0x00


def test_dt1_checksum_matches_roland_formula(m: MC707) -> None:
    """Checksum byte at position 12 equals (-sum(msg[8:12])) & 0x7F."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    body = msg[8:-2]
    expected = (-sum(body)) & 0x7F
    assert msg[-2] == expected


def test_dt1_checksum_independent_of_header(m: MC707) -> None:
    """Changing the address/payload changes the checksum; the header
    bytes (positions 0..7) do not contribute to the checksum."""
    m._midi.clear_log()
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    cs_a = m._midi.get_log()[-1][-2]
    m._midi.clear_log()
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 2])
    cs_b = m._midi.get_log()[-1][-2]
    # Different payload (last byte) → different checksum.
    assert cs_a != cs_b


# ---------------------------------------------------------------------------
# Frame construction (RQ1)
# ---------------------------------------------------------------------------


def test_rq1_frame_is_bracketed_by_f0_and_f7(m: MC707) -> None:
    """RQ1 frames are bracketed by F0 and F7 like DT1."""
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    msg = m._midi.get_log()[-1]
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7


def test_rq1_frame_carries_rq1_command_byte(m: MC707) -> None:
    """Byte 7 is the RQ1 command code 0x11."""
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    msg = m._midi.get_log()[-1]
    assert msg[7] == SysExController.RQ1_CMD == 0x11


def test_rq1_frame_address_at_positions_8_to_9(m: MC707) -> None:
    """RQ1 places the address at positions 8..9 (same as DT1)."""
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    msg = m._midi.get_log()[-1]
    assert msg[8] == 0x19
    assert msg[9] == 0x10


def test_rq1_frame_size_split_into_hi_lo_at_10_and_11(m: MC707) -> None:
    """Size is encoded as two 7-bit bytes (size_hi, size_lo)."""
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    msg = m._midi.get_log()[-1]
    # 4 → size_hi=0, size_lo=4
    assert msg[10] == 0
    assert msg[11] == 4


def test_rq1_size_128_splits_correctly(m: MC707) -> None:
    """Size 128 = 0x80 → size_hi=1, size_lo=0."""
    m.sysex.send_rq1((0x19, 0x10, 0), 128)
    msg = m._midi.get_log()[-1]
    assert msg[10] == 1
    assert msg[11] == 0


# ---------------------------------------------------------------------------
# Roland checksum formula
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body,expected",
    [
        ([0x12], 0x6E),                                       # spec example: -18 & 127 = 109
        ([], 0x00),                                            # empty body
        ([0x00, 0x00, 0x00, 0x00], 0x00),                     # all zero
        ([0x19, 0x00, 0x00, 0x01], 0x66),                     # the verifier body: -26 & 127 = 102
        ([0x7F, 0x7F, 0x7F, 0x7F], (-(0x7F * 4)) & 0x7F),    # max bytes
    ],
)
def test_checksum_formula_is_minus_sum_mod_128(body: list, expected: int) -> None:
    """Static ``_checksum`` matches (-sum(body)) & 0x7F for representative inputs."""
    assert SysExController._checksum(body) == expected


# ---------------------------------------------------------------------------
# Address encoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,c,d,expected",
    [
        (0x19, 0x00, 0, 0, [0x19, 0x00]),
        (0x19, 0x10, 0, 0, [0x19, 0x10]),
        (0x00, 0x00, 0, 0, [0x00, 0x00]),
        (0x7F, 0x7F, 0, 0, [0x7F, 0x7F]),
    ],
)
def test_addr_bytes_returns_two_bytes(a: int, b: int, c: int, d: int, expected: list) -> None:
    """``_addr_bytes`` packs (a, b) as two 7-bit bytes (c, d are accepted
    but not encoded — see module docstring)."""
    assert SysExController._addr_bytes(a, b, c, d) == expected


# ---------------------------------------------------------------------------
# Mock-mode log entry shape (indexable as bytes + dict-like)
# ---------------------------------------------------------------------------


def test_sysex_log_entry_supports_integer_indexing(m: MC707) -> None:
    """The mock log entry for a sysex message supports ``msg[0]`` /
    ``msg[-1]`` / ``msg[8:-2]`` style indexing directly."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    # Integer indexing works on the recorded frame.
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    assert isinstance(msg[8:-2], list)


def test_sysex_log_entry_supports_string_lookup(m: MC707) -> None:
    """String-key access (``entry["kind"]`` etc.) still works for
    backward compatibility with the existing patterns / scenes / clips
    tests."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    assert msg["kind"] == "sysex"
    assert msg["frame"][0] == 0xF0
    assert msg["frame"][-1] == 0xF7


# ---------------------------------------------------------------------------
# High-level convenience helpers (educated-guess addresses)
# ---------------------------------------------------------------------------


def test_clip_on_dispatches_a_dt1_frame(m: MC707) -> None:
    """``clip_on`` calls ``send_dt1`` and emits a 14-byte frame."""
    m.sysex.clip_on(1, 5)
    msg = m._midi.get_log()[-1]
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    assert len(msg) == 14


def test_track_level_dispatches_a_dt1_frame(m: MC707) -> None:
    """``track_level`` calls ``send_dt1`` and emits a 14-byte frame."""
    m.sysex.track_level(3, 100)
    msg = m._midi.get_log()[-1]
    assert len(msg) == 14


def test_set_fx_param_dispatches_a_dt1_frame(m: MC707) -> None:
    """``set_fx_param`` calls ``send_dt1`` and emits a 14-byte frame."""
    m.sysex.set_fx_param(2, 1, 5, 64)
    msg = m._midi.get_log()[-1]
    assert len(msg) == 14


# ---------------------------------------------------------------------------
# Device ID
# ---------------------------------------------------------------------------


def test_device_id_is_stored() -> None:
    """The ``device_id`` constructor argument is kept on the instance."""
    ctrl = SysExController(MC707()._midi, device_id=5)
    assert ctrl._device_id == 5


def test_default_device_id_is_zero() -> None:
    """The default ``device_id`` is 0 (per spec)."""
    ctrl = SysExController(MC707()._midi)
    assert ctrl._device_id == 0