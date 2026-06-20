"""Tests for :mod:`mc707.control.patterns`.

Covers step-pattern programming for both ``List[int]`` and ``List[Dict]``
input shapes, the strict ValueError validation contract, and the
required-verification log layout.
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.patterns import PatternController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# ---------------------------------------------------------------------------
# (a) Headline integration test — matches task verification script
# ---------------------------------------------------------------------------


def test_required_verification_script(m: MC707) -> None:
    """Exact log layout produced by the task's required verification script.

    Reproduced verbatim:
      - First call: 8 int steps, 4 active (notes 36/38/36/42) → 4 × 3 = 12 entries
      - Second call: 3 dict steps, 2 active (notes 36/38) → 2 × 3 = 6 entries
      - Total: 18 entries
    """
    m.patterns.program(1, [36, 0, 38, 0, 36, 0, 42, 0])
    m.patterns.program(1, [
        {"note": 36, "velocity": 110, "gate": 85},
        {"note": 0},
        {"note": 38, "velocity": 95},
    ])

    log = m._midi.get_log()
    assert len(log) == 18, (
        f"expected 18 log entries (12 + 6), got {len(log)}: {log}"
    )


# Skeleton DT1 payload tail layout (after the 10-byte header):
#   payload[-4] = step_num
#   payload[-3] = note
#   payload[-2] = velocity
#   payload[-1] = gate


def test_int_steps_emit_sysex_note_on_note_off_per_active_step(m: MC707) -> None:
    """Plain int steps emit 3 messages (sysex + note_on + note_off) per active note."""
    m._midi.clear_log()
    m.patterns.program(1, [36, 0, 38, 0, 36, 0, 42, 0])

    log = m._midi.get_log()
    assert len(log) == 12  # 4 active steps × 3 messages

    # First triplet: step 0, note 36, defaults vel=100 / gate=80.
    assert log[0]["kind"] == "sysex"
    assert log[1]["type"] == "note_on"
    assert log[1]["channel"] == 9   # track 1 → MIDI ch 10 → 0-indexed 9
    assert log[1]["note"] == 36
    assert log[1]["velocity"] == 100
    assert log[2]["type"] == "note_off"
    assert log[2]["channel"] == 9
    assert log[2]["note"] == 36
    assert log[0]["payload"][-4:] == [0, 36, 100, 80]

    # Step 2 (rest at index 1) is skipped — the next sysex is for step 2.
    assert log[3]["kind"] == "sysex"
    assert log[3]["payload"][-4:] == [2, 38, 100, 80]
    assert log[4]["type"] == "note_on"
    assert log[4]["note"] == 38
    assert log[4]["velocity"] == 100
    assert log[5]["type"] == "note_off"
    assert log[5]["note"] == 38

    # Step 6, note 42.
    assert log[9]["kind"] == "sysex"
    assert log[9]["payload"][-4:] == [6, 42, 100, 80]
    assert log[10]["type"] == "note_on"
    assert log[10]["note"] == 42
    assert log[11]["type"] == "note_off"
    assert log[11]["note"] == 42


def test_dict_steps_use_per_step_velocity_and_gate(m: MC707) -> None:
    """Dict steps with explicit velocity/gate flow through to note_on."""
    m._midi.clear_log()
    m.patterns.program(1, [
        {"note": 36, "velocity": 110, "gate": 85},
        {"note": 0},
        {"note": 38, "velocity": 95},
    ])

    log = m._midi.get_log()
    assert len(log) == 6  # 2 active × 3

    # First note 36 vel=110, gate=85.
    assert log[1]["type"] == "note_on"
    assert log[1]["note"] == 36
    assert log[1]["velocity"] == 110
    assert log[0]["payload"][-4:] == [0, 36, 110, 85]

    # Second note 38 vel=95, default gate=80.
    assert log[4]["type"] == "note_on"
    assert log[4]["note"] == 38
    assert log[4]["velocity"] == 95
    assert log[3]["payload"][-4:] == [2, 38, 95, 80]


def test_dict_steps_fall_back_to_top_level_defaults(m: MC707) -> None:
    """Dict steps that omit velocity/gate use the top-level defaults."""
    m._midi.clear_log()
    m.patterns.program(1, [{"note": 60}], velocity=120, gate=70)

    log = m._midi.get_log()
    assert len(log) == 3
    assert log[1]["type"] == "note_on"
    assert log[1]["note"] == 60
    assert log[1]["velocity"] == 120
    assert log[0]["payload"][-4:] == [0, 60, 120, 70]


# ---------------------------------------------------------------------------
# Track → channel mapping
# ---------------------------------------------------------------------------


def test_track_to_channel_offset_is_nine(m: MC707) -> None:
    """Tracks 1..8 → MIDI channels 10..17 (offset = 9), clamped by MIDIIO.

    Note: ``mido`` and the underlying backend only support channels 1..16,
    so tracks 1..7 land on 0-indexed channels 9..15 and track 8 silently
    clamps to channel 15. This matches the behaviour of
    :class:`SoundController` (see ``sounds.py`` docstring).
    """
    expected_channels = {
        1: 9, 2: 10, 3: 11, 4: 12,
        5: 13, 6: 14, 7: 15, 8: 15,   # track 8 clamps to channel 16 → idx 15
    }
    for track, expected in expected_channels.items():
        m._midi.clear_log()
        m.patterns.program(track, [60])
        log = m._midi.get_log()
        assert log[1]["channel"] == expected, (
            f"track {track}: expected 0-indexed channel {expected}, "
            f"got {log[1]['channel']}"
        )


# ---------------------------------------------------------------------------
# Rest steps
# ---------------------------------------------------------------------------


def test_note_zero_is_a_rest_and_emits_nothing(m: MC707) -> None:
    """A step whose note == 0 is a rest — no MIDI is dispatched for it."""
    m._midi.clear_log()
    m.patterns.program(1, [0, 0, 0])
    assert m._midi.get_log() == []


def test_mixed_rest_and_active_steps(m: MC707) -> None:
    """Only active steps emit messages; rests are skipped cleanly."""
    m._midi.clear_log()
    m.patterns.program(1, [60, 0, 62])
    log = m._midi.get_log()
    # Two active notes (60, 62) → 6 messages (2 × 3).
    assert len(log) == 6
    assert log[1]["note"] == 60
    assert log[4]["note"] == 62
    # Skeleton frame for step 0 (note 60).
    assert log[0]["payload"][-4:] == [0, 60, 100, 80]
    # Skeleton frame for step 2 (note 62).
    assert log[3]["payload"][-4:] == [2, 62, 100, 80]


# ---------------------------------------------------------------------------
# Empty / degenerate inputs
# ---------------------------------------------------------------------------


def test_empty_steps_list_is_a_noop(m: MC707) -> None:
    """An empty list returns True and emits nothing."""
    assert m.patterns.program(1, []) is True
    assert m._midi.get_log() == []


# ---------------------------------------------------------------------------
# ValueError contract
# ---------------------------------------------------------------------------


def test_track_zero_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        m.patterns.program(0, [36])


def test_track_nine_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        m.patterns.program(9, [36])


def test_track_non_int_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be an int"):
        m.patterns.program("1", [36])  # type: ignore[arg-type]


def test_track_bool_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be an int"):
        m.patterns.program(True, [36])  # type: ignore[arg-type]


def test_step_str_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"must be int or dict"):
        m.patterns.program(1, [36, "foo", 38])


def test_step_none_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"must be int or dict"):
        m.patterns.program(1, [None])


def test_step_bool_rejected(m: MC707) -> None:
    """Bool steps are rejected explicitly (bool is int subclass)."""
    with pytest.raises(ValueError, match=r"must be int or dict"):
        m.patterns.program(1, [True])


def test_dict_step_missing_note_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"missing required 'note' key"):
        m.patterns.program(1, [{"velocity": 100}])


def test_dict_step_note_oversize_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"note must be between 0 and 127"):
        m.patterns.program(1, [{"note": 200}])


def test_dict_step_note_negative_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"note must be between 0 and 127"):
        m.patterns.program(1, [{"note": -1}])


def test_velocity_zero_rejected(m: MC707) -> None:
    """Velocity 0 is MIDI for Note-Off, so it is rejected."""
    with pytest.raises(ValueError, match=r"velocity must be between 1 and 127"):
        m.patterns.program(1, [{"note": 36, "velocity": 0}])


def test_velocity_oversize_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"velocity must be between 1 and 127"):
        m.patterns.program(1, [{"note": 36, "velocity": 200}])


def test_gate_zero_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"gate must be between 1 and 127"):
        m.patterns.program(1, [{"note": 36, "gate": 0}])


def test_gate_oversize_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"gate must be between 1 and 127"):
        m.patterns.program(1, [{"note": 36, "gate": 200}])


def test_top_level_velocity_zero_rejected(m: MC707) -> None:
    """The top-level ``velocity`` default is also validated."""
    with pytest.raises(ValueError, match=r"velocity must be between 1 and 127"):
        m.patterns.program(1, [36], velocity=0)


def test_top_level_gate_oversize_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"gate must be between 1 and 127"):
        m.patterns.program(1, [36], gate=200)


def test_pattern_number_negative_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"pattern_number must be between 0 and 127"):
        m.patterns.program(1, [36], pattern_number=-1)


def test_pattern_number_oversize_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"pattern_number must be between 0 and 127"):
        m.patterns.program(1, [36], pattern_number=128)


def test_steps_not_a_list_rejected(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"steps must be a list"):
        m.patterns.program(1, (36, 38))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# pattern_number logging contract
# ---------------------------------------------------------------------------


def test_pattern_number_is_logged_but_does_not_emit_messages(m: MC707) -> None:
    """``pattern_number`` only logs; it does not change the dispatch count."""
    m._midi.clear_log()
    result = m.patterns.program(1, [60], pattern_number=5)
    assert result is True
    # One active step → 3 messages, no extra scene-select PC.
    assert len(m._midi.get_log()) == 3
    # None of them is a program_change.
    for entry in m._midi.get_log():
        assert entry.get("type") != "program_change"


def test_pattern_number_zero_is_accepted(m: MC707) -> None:
    """``pattern_number=0`` is the lower bound and must be accepted."""
    assert m.patterns.program(1, [60], pattern_number=0) is True


def test_pattern_number_max_is_accepted(m: MC707) -> None:
    """``pattern_number=127`` is the upper bound and must be accepted."""
    assert m.patterns.program(1, [60], pattern_number=127) is True


# ---------------------------------------------------------------------------
# Return value contract
# ---------------------------------------------------------------------------


def test_program_returns_true_for_all_active_steps(m: MC707) -> None:
    assert m.patterns.program(1, [60, 0, 62, 0, 64]) is True


def test_program_returns_true_for_empty_steps(m: MC707) -> None:
    assert m.patterns.program(1, []) is True


def test_program_returns_true_for_only_rests(m: MC707) -> None:
    assert m.patterns.program(1, [0, 0, 0, 0]) is True


# ---------------------------------------------------------------------------
# Constants / class API surface
# ---------------------------------------------------------------------------


def test_class_constants() -> None:
    """Public class constants match the spec."""
    assert PatternController.MIN_TRACK == 1
    assert PatternController.MAX_TRACK == 8
    assert PatternController.MIN_NOTE == 0
    assert PatternController.MAX_NOTE == 127
    assert PatternController.MIN_VELOCITY == 1
    assert PatternController.MAX_VELOCITY == 127
    assert PatternController.MIN_GATE == 1
    assert PatternController.MAX_GATE == 127
    assert PatternController.DEFAULT_VELOCITY == 100
    assert PatternController.DEFAULT_GATE == 80
    assert PatternController.TRACK_CHANNEL_OFFSET == 9
    assert PatternController.MIN_PATTERN == 0
    assert PatternController.MAX_PATTERN == 127


def test_skeleton_sysex_frame_layout(m: MC707) -> None:
    """The skeleton DT1 frame keeps the documented Roland header shape."""
    m._midi.clear_log()
    m.patterns.program(1, [60])
    log = m._midi.get_log()
    frame = log[0]["frame"]
    # Roland header: F0 41 10 00 00 00 6A 12  <addr4>  <payload...>  F7
    assert frame[0] == 0xF0
    assert frame[1] == 0x41
    assert frame[2] == 0x10
    assert frame[3] == 0x00  # device_id
    assert frame[4] == 0x00
    assert frame[5] == 0x00
    assert frame[6] == 0x6A
    assert frame[7] == 0x12  # CMD_DT1
    # Address bytes (educated guess): 0x19, 0x10, track-1.
    assert frame[8] == 0x19
    assert frame[9] == 0x10
    assert frame[10] == 0x00  # track 1 → (track - 1) = 0
    # Payload: step_num, note, vel, gate.
    assert frame[11] == 0   # step_num
    assert frame[12] == 60  # note
    assert frame[13] == 100  # default vel
    assert frame[14] == 80   # default gate
    assert frame[-1] == 0xF7