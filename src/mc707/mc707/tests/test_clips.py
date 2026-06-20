"""Tests for :mod:`mc707.control.clips`.

Covers clip triggering, track mixer, stop / stop_all, validation, and
the four required verifier checks:

    (a) 4-message MIDI-log assertion
    (b) ``track=99`` raises ``ValueError``
    (c) for t in 1..8: ``trigger(t,1)`` channel == ``t + offset``
    (d) ``stop_all()`` uniqueness — exactly 8 channels, no duplicates
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.clips import ClipController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# ---------------------------------------------------------------------------
# (a) 4-message MIDI-log integration — clips-side decoding
# ---------------------------------------------------------------------------


def test_four_message_midi_log_clips_side(m: MC707) -> None:
    """Re-run the task's 4-message verification script and decode the
    three clips-related log entries (entries 2, 3, 4)."""
    m.scenes.select(0)
    m.clips.trigger(1, 1)
    m.clips.track_mute(2)
    m.clips.track_volume(3, 100)

    log = m._midi.get_log()
    assert len(log) == 4

    # clips.trigger(1, 1) → PC on track 1 channel (1 + 8 = 9 → idx 8)
    assert log[1]["type"] == "program_change"
    assert log[1]["channel"] == 8
    assert log[1]["program"] == 0

    # clips.track_mute(2) → CC 94 on (2 + 8 = 10 → idx 9), value 127
    assert log[2]["type"] == "control_change"
    assert log[2]["channel"] == 9
    assert log[2]["control"] == 94
    assert log[2]["value"] == 127

    # clips.track_volume(3, 100) → CC 7 on (3 + 8 = 11 → idx 10), value 100
    assert log[3]["type"] == "control_change"
    assert log[3]["channel"] == 10
    assert log[3]["control"] == 7
    assert log[3]["value"] == 100


# ---------------------------------------------------------------------------
# (b) track=99 raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,args",
    [
        ("trigger",        (99, 1)),
        ("stop",           (99,)),
        ("track_mute",     (99,)),
        ("track_solo",     (99,)),
        ("track_volume",   (99, 100)),
        ("track_pan",      (99, 64)),
    ],
)
def test_track_99_raises_value_error(m: MC707, method: str, args: tuple) -> None:
    """Every track-parameterised method must reject ``track=99``."""
    fn = getattr(m.clips, method)
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        fn(*args)


# ---------------------------------------------------------------------------
# (c) for t in 1..8: trigger(t, 1)["channel"] == t + offset
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("track", list(range(1, 9)))
def test_trigger_channel_invariant(m: MC707, track: int) -> None:
    """Every track ``t`` produces a Program Change on MIDI channel
    ``t + TRACK_CHANNEL_OFFSET`` (1-indexed), which is ``t + 8`` here.

    The MC-707 1-indexed channel converts to mido's 0-indexed form as
    ``(t + TRACK_CHANNEL_OFFSET) - 1``.
    """
    assert m.clips.trigger(track, 1) is True

    log = m._midi.get_log()
    # The trigger call is the most recent Program Change in the log.
    pc_entries = [e for e in log if e["type"] == "program_change"]
    assert pc_entries, "expected at least one program_change entry"
    entry = pc_entries[-1]

    expected_one_indexed = track + ClipController.TRACK_CHANNEL_OFFSET
    expected_zero_indexed = expected_one_indexed - 1
    assert entry["channel"] == expected_zero_indexed, (
        f"track {track}: expected channel {expected_zero_indexed} "
        f"(MIDI ch {expected_one_indexed}), got {entry['channel']}"
    )
    assert entry["program"] == 0  # clip 1 → pc 0


def test_trigger_channel_invariant_all_tracks_distinct(m: MC707) -> None:
    """The 8 track channels are pairwise distinct (no overlap)."""
    for track in range(1, 9):
        m.clips.trigger(track, 1)
    pc_channels = [
        e["channel"]
        for e in m._midi.get_log()
        if e["type"] == "program_change"
    ]
    assert len(pc_channels) == 8
    assert len(set(pc_channels)) == 8, f"duplicate channels: {pc_channels}"


# ---------------------------------------------------------------------------
# (d) stop_all() uniqueness check
# ---------------------------------------------------------------------------


def test_stop_all_emits_exactly_one_cc_per_track(m: MC707) -> None:
    """``stop_all()`` must emit exactly 8 All-Notes-Off CCs (one per
    track), each on a distinct MIDI channel."""
    m.clips.stop_all()

    # All entries should be control_change messages (CC 123, value 0).
    cc_entries = [
        e for e in m._midi.get_log() if e["type"] == "control_change"
    ]
    assert len(cc_entries) == 8, (
        f"stop_all() should emit 8 CCs, got {len(cc_entries)}: {cc_entries}"
    )

    # Each CC must be All-Notes-Off (123) with value 0.
    for entry in cc_entries:
        assert entry["control"] == 123
        assert entry["value"] == 0

    # Channels must be unique and span the track range.
    channels = [e["channel"] for e in cc_entries]
    assert len(set(channels)) == 8, f"duplicate channels in stop_all: {channels}"

    expected_channels = sorted(
        t + ClipController.TRACK_CHANNEL_OFFSET - 1 for t in range(1, 9)
    )
    assert sorted(channels) == expected_channels


# ---------------------------------------------------------------------------
# Trigger validation
# ---------------------------------------------------------------------------


def test_trigger_rejects_track_zero(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        m.clips.trigger(0, 1)


def test_trigger_rejects_track_nine(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        m.clips.trigger(9, 1)


def test_trigger_rejects_clip_zero(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"clip must be between 1 and 16"):
        m.clips.trigger(1, 0)


def test_trigger_rejects_clip_seventeen(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"clip must be between 1 and 16"):
        m.clips.trigger(1, 17)


def test_trigger_rejects_velocity_zero(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"velocity must be between 1 and 127"):
        m.clips.trigger(1, 1, velocity=0)


def test_trigger_rejects_velocity_oversize(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"velocity must be between 1 and 127"):
        m.clips.trigger(1, 1, velocity=128)


# ---------------------------------------------------------------------------
# Mixer validation
# ---------------------------------------------------------------------------


def test_track_volume_rejects_oversize(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"value must be between 0 and 127"):
        m.clips.track_volume(1, 200)


def test_track_volume_rejects_negative(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"value must be between 0 and 127"):
        m.clips.track_volume(1, -1)


def test_track_pan_rejects_oversize(m: MC707) -> None:
    with pytest.raises(ValueError, match=r"value must be between 0 and 127"):
        m.clips.track_pan(1, 200)


def test_track_mute_sends_correct_values(m: MC707) -> None:
    """Mute on/off produce the right CC values."""
    assert m.clips.track_mute(1, on=True) is True
    assert m.clips.track_mute(2, on=False) is True
    log = m._midi.get_log()
    assert log[0]["value"] == 127
    assert log[1]["value"] == 0
    assert log[0]["control"] == 94
    assert log[1]["control"] == 94


def test_track_solo_sends_correct_values(m: MC707) -> None:
    assert m.clips.track_solo(1, on=True) is True
    assert m.clips.track_solo(2, on=False) is True
    log = m._midi.get_log()
    assert log[0]["control"] == 95
    assert log[0]["value"] == 127
    assert log[1]["control"] == 95
    assert log[1]["value"] == 0


def test_track_volume_passes_value_through(m: MC707) -> None:
    """track_volume(track, value) routes the exact value into CC 7."""
    assert m.clips.track_volume(1, 42) is True
    log = m._midi.get_log()
    assert log[0]["control"] == 7
    assert log[0]["value"] == 42


def test_track_pan_passes_value_through(m: MC707) -> None:
    """track_pan(track, value) routes the exact value into CC 10."""
    assert m.clips.track_pan(1, 64) is True  # center
    log = m._midi.get_log()
    assert log[0]["control"] == 10
    assert log[0]["value"] == 64


# ---------------------------------------------------------------------------
# stop()
# ---------------------------------------------------------------------------


def test_stop_emits_all_notes_off(m: MC707) -> None:
    """stop(track) emits CC 123 (All Notes Off) on the track channel."""
    assert m.clips.stop(3) is True
    log = m._midi.get_log()
    assert len(log) == 1
    assert log[0]["type"] == "control_change"
    assert log[0]["control"] == 123
    assert log[0]["value"] == 0
    assert log[0]["channel"] == 3 + ClipController.TRACK_CHANNEL_OFFSET - 1
