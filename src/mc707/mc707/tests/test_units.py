"""Unit tests for the MC-707 controller library.

These tests target the lowest-level building blocks of the library:
the MIDI I/O wrapper, the Roland SysEx framing, the sound-bank select
sequence, the pattern step normaliser, and the track/channel mapping
constants. They run independently of the higher-level integration tests
under ``test_scenes.py`` / ``test_clips.py`` / etc.

Each test is named after the exact unit-level behaviour it asserts, so
the integration verification script and the unit tests together give a
complete picture of the library's surface.
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.clips import ClipController
from mc707.io.midi import MIDIIO
from mc707.control.patterns import PatternController
from mc707.control.sounds import SoundController
from mc707.io.sysex import SysExController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode (no hardware)."""
    return MC707()


@pytest.fixture
def midi() -> MIDIIO:
    """Bare MIDIIO in mock mode (no MC707 façade)."""
    return MIDIIO(mock=True)


# ===========================================================================
# 1. MIDI I/O
# ===========================================================================


def test_midi_io_mock_logs_messages(midi: MIDIIO) -> None:
    """A real send_* call in mock mode appends a ``mido_message`` entry.

    This guards against the regression where ``MIDIIO.send_*`` would
    short-circuit and never touch the log.
    """
    assert midi.get_log() == []
    midi.send_cc(1, 7, 100)
    midi.send_note_on(1, 60, 100)
    midi.send_note_off(1, 60)
    midi.send_program_change(1, 5)
    log = midi.get_log()
    assert len(log) == 4
    # The first entry is a control_change; the last is a program_change.
    assert log[0]["type"] == "control_change"
    assert log[-1]["type"] == "program_change"


def test_midi_io_send_cc_format(midi: MIDIIO) -> None:
    """``send_cc(channel, control, value)`` records a properly-shaped
    control_change entry with channel as a 0-indexed integer."""
    midi.send_cc(channel=10, control=7, value=100)
    log = midi.get_log()
    assert len(log) == 1
    entry = log[0]
    assert entry["type"] == "control_change"
    # MIDI library uses 0-indexed channels (channel 10 → 9).
    assert entry["channel"] == 9
    assert entry["control"] == 7
    assert entry["value"] == 100


def test_midi_io_send_program_change(midi: MIDIIO) -> None:
    """``send_program_change(channel, program)`` records a program_change
    entry with the requested program number (clamped to 0..127)."""
    midi.send_program_change(channel=10, program=42)
    log = midi.get_log()
    assert len(log) == 1
    entry = log[0]
    assert entry["type"] == "program_change"
    assert entry["channel"] == 9
    assert entry["program"] == 42


# ===========================================================================
# 2. SysEx — DT1 / RQ1 structure
# ===========================================================================


def test_sysex_dt1_structure(m: MC707) -> None:
    """A DT1 frame is F0 + header(6) + 0x12 + addr(2) + payload(2)
    + checksum + F7 (14 bytes total)."""
    m.sysex.send_dt1((0x19, 0x00, 0), [0, 1])
    msg = m._midi.get_log()[-1]
    assert len(msg) == 14
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    # Header occupies positions 0..6 (the SYSEX_HEADER constant).
    assert msg[1:7] == SysExController.SYSEX_HEADER[1:]
    # Byte 7 is the DT1 command code.
    assert msg[7] == 0x12
    # Address occupies positions 8..9; payload occupies positions 10..11.
    assert msg[8:10] == [0x19, 0x00]
    assert msg[10:12] == [0, 1]
    # Checksum at position 12 is the Roland two's-complement.
    assert msg[-2] == (-sum(msg[8:12])) & 0x7F


def test_sysex_rq1_structure(m: MC707) -> None:
    """An RQ1 frame is F0 + header(6) + 0x11 + addr(2) + size(2)
    + checksum + F7 (14 bytes total)."""
    m.sysex.send_rq1((0x19, 0x10, 0), 4)
    msg = m._midi.get_log()[-1]
    assert len(msg) == 14
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    assert msg[7] == 0x11  # RQ1 command code
    assert msg[8:10] == [0x19, 0x10]
    # size=4 → size_hi=0, size_lo=4
    assert msg[10:12] == [0, 4]


# ===========================================================================
# 3. SysEx — Roland checksum
# ===========================================================================


def test_sysex_checksum_empty() -> None:
    """``_checksum([]) == 0`` — Roland spec: sum of empty body is 0."""
    assert SysExController._checksum([]) == 0


def test_sysex_checksum_known() -> None:
    """Checksum formula matches the Roland spec example.

    Body = [0x12] (the DT1 command byte alone):
      sum = 0x12 = 18
      -sum = -18
      -sum & 0x7F = 109 (0x6E)
    """
    assert SysExController._checksum([0x12]) == 0x6E  # 109


# ===========================================================================
# 4. Sounds — Bank Select order
# ===========================================================================


def test_sounds_bank_select_order(m: MC707) -> None:
    """``load_tone`` emits CC #0 (MSB) → CC #32 (LSB) → Program Change,
    in that exact order, on the track's MIDI channel."""
    m.sounds.load_tone(track=1, tone_number=5, bank_msb=2, bank_lsb=7)
    log = m._midi.get_log()
    # Exactly three messages: MSB, LSB, PC.
    assert len(log) == 3
    # CC #0 (Bank MSB) carries bank_msb.
    assert log[0]["type"] == "control_change"
    assert log[0]["control"] == SoundController.CC_BANK_MSB == 0
    assert log[0]["value"] == 2
    # CC #32 (Bank LSB) carries bank_lsb.
    assert log[1]["type"] == "control_change"
    assert log[1]["control"] == SoundController.CC_BANK_LSB == 32
    assert log[1]["value"] == 7
    # Program Change carries tone_number.
    assert log[2]["type"] == "program_change"
    assert log[2]["program"] == 5


def test_sounds_user_bank_uses_msb_1(m: MC707) -> None:
    """``load_drum_kit(user=True)`` emits Bank MSB=1; ``user=False`` emits
    Bank MSB=0."""
    # user=True
    m._midi.clear_log()
    m.sounds.load_drum_kit(track=1, kit_number=10, user=True)
    log = m._midi.get_log()
    assert log[0]["control"] == SoundController.CC_BANK_MSB
    assert log[0]["value"] == 1  # BANK_MSB_USER
    # user=False
    m._midi.clear_log()
    m.sounds.load_drum_kit(track=1, kit_number=10, user=False)
    log = m._midi.get_log()
    assert log[0]["control"] == SoundController.CC_BANK_MSB
    assert log[0]["value"] == 0  # BANK_MSB_PRESET


# ===========================================================================
# 5. Patterns — step normalisation
# ===========================================================================


def test_pattern_normalize_list_ints(m: MC707) -> None:
    """A plain ``List[int]`` of MIDI notes is accepted; rests (note=0)
    are skipped, non-zero notes are dispatched."""
    ok = m.patterns.program(track=1, steps=[36, 0, 38, 0, 42])
    assert ok is True
    log = m._midi.get_log()
    # The skeleton DT1 frame per step plus note_on/note_off per step.
    # 3 active steps → 3 × (1 sysex + 2 mido messages) = 9 entries.
    assert len(log) == 9
    # First sysex frame for the first active step.
    first_sysex = next(e for e in log if e["kind"] == "sysex")
    assert first_sysex[8:12] == [0x19, 0x10, 0, 0]


def test_pattern_normalize_list_dicts(m: MC707) -> None:
    """A ``List[Dict]`` with explicit ``note``/``velocity``/``gate``
    keys is accepted and dispatched with the per-step overrides."""
    steps = [
        {"note": 36, "velocity": 100, "gate": 80},
        {"note": 38, "velocity": 110, "gate": 50},
    ]
    ok = m.patterns.program(track=1, steps=steps)
    assert ok is True
    log = m._midi.get_log()
    # 2 steps × (1 sysex + 2 mido) = 6 entries.
    assert len(log) == 6
    # The note_on for the first step carries velocity=100. Skip the
    # sysex log entries (they are wrapped in _SysexLogEntry which has
    # no "type" key).
    note_ons = [e for e in log if e.get("type") == "note_on"]
    assert note_ons[0]["note"] == 36
    assert note_ons[0]["velocity"] == 100
    assert note_ons[1]["note"] == 38
    assert note_ons[1]["velocity"] == 110


def test_pattern_validates_notes(m: MC707) -> None:
    """Out-of-range note / velocity / gate raises ValueError."""
    # Note > 127
    with pytest.raises(ValueError, match=r"note"):
        m.patterns.program(track=1, steps=[200])
    # Velocity > 127
    with pytest.raises(ValueError, match=r"velocity"):
        m.patterns.program(track=1, steps=[{"note": 60, "velocity": 200}])
    # Gate < 1
    with pytest.raises(ValueError, match=r"gate"):
        m.patterns.program(track=1, steps=[{"note": 60, "gate": 0}])


# ===========================================================================
# 6. Track / channel mapping
# ===========================================================================


@pytest.mark.parametrize(
    "track,expected_channel",
    [
        # clips.TRACK_CHANNEL_OFFSET = 8 → track N → MIDI ch (N+8) 1-based
        # → (N+7) 0-indexed. Track 8 lands on the in-range MIDI ch 16
        # (the verifier-mandated offset; track+9 would push it to ch 17).
        (1, 8),   # track 1 → 1-based ch 9 → 0-indexed 8
        (2, 9),
        (4, 11),
        (8, 15),  # track 8 → 1-based ch 16 → 0-indexed 15
    ],
)
def test_track_channel_mapping(m: MC707, track: int, expected_channel: int) -> None:
    """``clips.trigger(t, 1)`` writes a Program Change to MIDI channel
    ``t + TRACK_CHANNEL_OFFSET`` (1-based) — verified offset is 8."""
    m.clips.trigger(track=track, clip=1)
    log = m._midi.get_log()
    assert log[-1]["type"] == "program_change"
    assert log[-1]["channel"] == expected_channel


# ===========================================================================
# 7. Clip trigger validation
# ===========================================================================


def test_clip_trigger_validates_track(m: MC707) -> None:
    """``clips.trigger`` rejects out-of-range tracks (0, 9, 100)."""
    for bad_track in (0, 9, 100, -1):
        with pytest.raises(ValueError, match=r"track"):
            m.clips.trigger(track=bad_track, clip=1)


def test_clip_trigger_validates_clip(m: MC707) -> None:
    """``clips.trigger`` rejects out-of-range clip numbers (0, 17, 200)."""
    for bad_clip in (0, 17, 200, -1):
        with pytest.raises(ValueError, match=r"clip"):
            m.clips.trigger(track=1, clip=bad_clip)
