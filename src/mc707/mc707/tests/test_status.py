"""Tests for :mod:`mc707.control.status`.

Covers the StatusController mock-state cache, the public read API
(``current_tone`` / ``current_scene`` / ``current_tempo``), and the
``on_response`` callback registration path.
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.status import StatusController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# ---------------------------------------------------------------------------
# Defaults from the spec
# ---------------------------------------------------------------------------


def test_default_scene_is_zero(m: MC707) -> None:
    """Mock state: ``scene`` defaults to 0 (per spec)."""
    assert m.status.current_scene() == 0


def test_default_tempo_is_120(m: MC707) -> None:
    """Mock state: ``tempo`` defaults to 120 (per spec)."""
    assert m.status.current_tempo() == 120


@pytest.mark.parametrize("track", [1, 2, 3, 4, 5, 6, 7, 8])
def test_default_tone_for_every_track_is_zero(m: MC707, track: int) -> None:
    """Mock state: every track's tone defaults to 0 (per spec)."""
    assert m.status.current_tone(track) == 0


# ---------------------------------------------------------------------------
# current_tone edge cases
# ---------------------------------------------------------------------------


def test_current_tone_for_unknown_track_is_none(m: MC707) -> None:
    """``current_tone(track)`` returns ``None`` for tracks outside 1..8."""
    assert m.status.current_tone(0) is None
    assert m.status.current_tone(9) is None
    assert m.status.current_tone(99) is None


# ---------------------------------------------------------------------------
# on_response callback registration
# ---------------------------------------------------------------------------


def test_on_response_appends_callback(m: MC707) -> None:
    """``on_response`` adds the callback to the internal list."""
    cb = lambda kind, payload: None  # noqa: E731
    m.status.on_response(cb)
    assert cb in m.status._callbacks


def test_multiple_callbacks_all_registered(m: MC707) -> None:
    """Multiple ``on_response`` calls accumulate callbacks."""
    cb_a = lambda k, p: None  # noqa: E731
    cb_b = lambda k, p: None  # noqa: E731
    m.status.on_response(cb_a)
    m.status.on_response(cb_b)
    assert cb_a in m.status._callbacks
    assert cb_b in m.status._callbacks


def test_callback_fires_on_tone_update(m: MC707) -> None:
    """Updating a tone via ``_update_tone`` invokes every registered callback."""
    received = []

    def cb(kind, payload):
        received.append((kind, payload))

    m.status.on_response(cb)
    m.status._update_tone(3, 42)

    assert received == [("tone", {"track": 3, "tone": 42})]
    # Cache is also updated.
    assert m.status.current_tone(3) == 42


def test_callback_fires_on_scene_update(m: MC707) -> None:
    """Updating a scene invokes every registered callback."""
    received = []

    def cb(kind, payload):
        received.append((kind, payload))

    m.status.on_response(cb)
    m.status._update_scene(5)

    assert received == [("scene", {"scene": 5})]
    assert m.status.current_scene() == 5


def test_callback_fires_on_tempo_update(m: MC707) -> None:
    """Updating a tempo invokes every registered callback."""
    received = []

    def cb(kind, payload):
        received.append((kind, payload))

    m.status.on_response(cb)
    m.status._update_tempo(140)

    assert received == [("tempo", {"bpm": 140})]
    assert m.status.current_tempo() == 140


def test_callback_exception_is_swallowed(m: MC707) -> None:
    """A callback that raises does not propagate; other callbacks still fire."""
    def bad_cb(kind, payload):
        raise RuntimeError("boom")

    received = []

    def good_cb(kind, payload):
        received.append((kind, payload))

    m.status.on_response(bad_cb)
    m.status.on_response(good_cb)
    # Should not raise.
    m.status._update_scene(7)
    assert received == [("scene", {"scene": 7})]


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_constructor_stores_midi_io_and_device_id() -> None:
    """The constructor wires up ``_midi`` and ``_device_id``."""
    midi = MC707()._midi
    ctrl = StatusController(midi, device_id=3)
    assert ctrl._midi is midi
    assert ctrl._device_id == 3


def test_default_device_id_is_zero() -> None:
    """The default ``device_id`` is 0 (per spec)."""
    midi = MC707()._midi
    ctrl = StatusController(midi)
    assert ctrl._device_id == 0


def test_callback_list_starts_empty(m: MC707) -> None:
    """A fresh controller has no registered callbacks."""
    assert m.status._callbacks == []


# ---------------------------------------------------------------------------
# MC707 façade wiring
# ---------------------------------------------------------------------------


def test_mc707_facade_exposes_status() -> None:
    """The MC707 façade exposes ``status`` as a StatusController."""
    m = MC707()
    assert isinstance(m.status, StatusController)


def test_mc707_facade_exposes_sysex() -> None:
    """The MC707 façade exposes ``sysex`` as a SysExController."""
    from mc707.io.sysex import SysExController

    m = MC707()
    assert isinstance(m.sysex, SysExController)