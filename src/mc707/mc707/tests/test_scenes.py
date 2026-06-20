"""Tests for :mod:`mc707.control.scenes`.

Covers scene selection, next/previous clamping, validation, and the
shared integration log used in the task's verification script.
"""

from __future__ import annotations

import pytest

from mc707 import MC707


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# ---------------------------------------------------------------------------
# (a) Headline 4-message MIDI-log integration test
# ---------------------------------------------------------------------------


def test_four_message_midi_log_integration(m: MC707) -> None:
    """Exact 4-message MIDI log produced by the task's verification script.

    The script is reproduced verbatim from the task body. Each entry is
    decoded into (type, channel, control/program, value) and compared to
    the expected MC-707 mapping.
    """
    m.scenes.select(0)
    m.clips.trigger(1, 1)
    m.clips.track_mute(2)
    m.clips.track_volume(3, 100)

    log = m._midi.get_log()
    assert len(log) == 4, f"expected 4 log entries, got {len(log)}: {log}"

    # 1. scenes.select(0) → Program Change on CONTROL_CHANNEL (= 10),
    #    channel 9 is the 0-indexed equivalent.
    assert log[0]["type"] == "program_change"
    assert log[0]["channel"] == 9
    assert log[0]["program"] == 0

    # 2. clips.trigger(1, 1) → Program Change on (track + offset).
    #    track=1, offset=8 → MIDI ch 9 → 0-indexed channel 8, program 0.
    assert log[1]["type"] == "program_change"
    assert log[1]["channel"] == 8
    assert log[1]["program"] == 0

    # 3. clips.track_mute(2) → CC 94 on (track + offset) = 10 → 0-indexed 9.
    assert log[2]["type"] == "control_change"
    assert log[2]["channel"] == 9
    assert log[2]["control"] == 94
    assert log[2]["value"] == 127

    # 4. clips.track_volume(3, 100) → CC 7 on (track + offset) = 11 → idx 10.
    assert log[3]["type"] == "control_change"
    assert log[3]["channel"] == 10
    assert log[3]["control"] == 7
    assert log[3]["value"] == 100


# ---------------------------------------------------------------------------
# Scene selection
# ---------------------------------------------------------------------------


def test_select_dispatches_program_change(m: MC707) -> None:
    """``select(n)`` emits a Program Change on the control channel."""
    m.scenes.select(5)
    log = m._midi.get_log()
    assert len(log) == 1
    assert log[0]["type"] == "program_change"
    assert log[0]["channel"] == 9  # CONTROL_CHANNEL=10 → 0-indexed
    assert log[0]["program"] == 5


def test_select_updates_current_state(m: MC707) -> None:
    """``select(n)`` updates the cached current scene."""
    assert m.scenes.current() == 0
    assert m.scenes.select(7) is True
    assert m.scenes.current() == 7


def test_select_boundaries(m: MC707) -> None:
    """``select(0)`` and ``select(127)`` are accepted at the edges."""
    assert m.scenes.select(0) is True
    assert m.scenes.current() == 0
    assert m.scenes.select(127) is True
    assert m.scenes.current() == 127


def test_select_rejects_negative(m: MC707) -> None:
    """Out-of-range below 0 raises ValueError."""
    with pytest.raises(ValueError, match=r"scene must be between 0 and 127"):
        m.scenes.select(-1)


def test_select_rejects_oversize(m: MC707) -> None:
    """Out-of-range above 127 raises ValueError."""
    with pytest.raises(ValueError, match=r"scene must be between 0 and 127"):
        m.scenes.select(128)


def test_select_rejects_non_int(m: MC707) -> None:
    """Non-integer (e.g. str) raises ValueError."""
    with pytest.raises(ValueError, match=r"scene must be an int"):
        m.scenes.select("5")  # type: ignore[arg-type]


def test_select_rejects_bool(m: MC707) -> None:
    """Booleans are explicitly rejected (bool is int subclass)."""
    with pytest.raises(ValueError, match=r"scene must be an int"):
        m.scenes.select(True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# next / previous clamping
# ---------------------------------------------------------------------------


def test_next_advances_by_one(m: MC707) -> None:
    m.scenes.select(3)
    assert m.scenes.next() is True
    assert m.scenes.current() == 4


def test_next_clamps_at_max(m: MC707) -> None:
    """At the upper bound, next() stays put (no wrap-around)."""
    m.scenes.select(127)
    assert m.scenes.next() is True
    assert m.scenes.current() == 127


def test_previous_decrements_by_one(m: MC707) -> None:
    m.scenes.select(3)
    assert m.scenes.previous() is True
    assert m.scenes.current() == 2


def test_previous_clamps_at_zero(m: MC707) -> None:
    """At the lower bound, previous() stays put (no wrap-around)."""
    m.scenes.select(0)
    assert m.scenes.previous() is True
    assert m.scenes.current() == 0


def test_initial_current_is_zero(m: MC707) -> None:
    """Default state on a fresh controller is scene 0."""
    assert m.scenes.current() == 0
