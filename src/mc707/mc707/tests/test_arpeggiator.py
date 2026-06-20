"""Tests for :mod:`mc707.control.arpeggiator`.

Covers the arp-method dispatch on the controller's :attr:`CONTROL_CHANNEL`,
the strict ``ValueError`` validation on every parameter, the on/off
toggle semantics, and the public CC constant exports.

Every method is expected to write exactly one ``control_change`` entry
per call in the mock log; the CC numbers used (58..62) are marked
``TEMPLATE - VERIFY WITH MC-707 MIDI CHART`` and live as class
attributes so they can be updated in one place once the real MC-707
mapping is known.
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.arpeggiator import (
    ArpeggiatorController,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# Convenience — control channel in mido's 0-indexed form.
_CTRL_MIDO_CH = ArpeggiatorController.CONTROL_CHANNEL - 1


# ---------------------------------------------------------------------------
# (1) Every arp method dispatches a single control_change
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,args,expected_cc,expected_value",
    [
        ("on",    (True,),   ArpeggiatorController.CC_ARP_ON,     127),
        ("on",    (False,),  ArpeggiatorController.CC_ARP_ON,     0),
        ("rate",  (64,),     ArpeggiatorController.CC_ARP_RATE,   64),
        ("rate",  (0,),      ArpeggiatorController.CC_ARP_RATE,   0),
        ("rate",  (127,),    ArpeggiatorController.CC_ARP_RATE,   127),
        ("gate",  (64,),     ArpeggiatorController.CC_ARP_GATE,   64),
        ("style", (0,),      ArpeggiatorController.CC_ARP_STYLE,  0),
        ("style", (2,),      ArpeggiatorController.CC_ARP_STYLE,  2),
        ("style", (3,),      ArpeggiatorController.CC_ARP_STYLE,  3),
        ("octave",(0,),      ArpeggiatorController.CC_ARP_OCTAVE, 0),
        ("octave",(3,),      ArpeggiatorController.CC_ARP_OCTAVE, 3),
    ],
)
def test_arp_method_dispatch(
    m: MC707, method: str, args: tuple, expected_cc: int, expected_value: int,
) -> None:
    """Every arp method writes exactly one ``control_change`` on the
    control channel with the expected CC number and value."""
    fn = getattr(m.arpeggiator, method)
    assert fn(*args) is True

    log = m._midi.get_log()
    assert len(log) == 1
    entry = log[0]
    assert entry["type"] == "control_change"
    assert entry["channel"] == _CTRL_MIDO_CH
    assert entry["control"] == expected_cc
    assert entry["value"] == expected_value


# ---------------------------------------------------------------------------
# (2) Producer verification — arp entries at slots 6, 7, 8 of a 9-call sequence
# ---------------------------------------------------------------------------


def test_producer_arp_entries_in_sequence(m: MC707) -> None:
    """Re-run the three arp entries from the producer verification
    script and confirm the on → rate → style ordering."""
    m.effects.cutoff(100)
    m.effects.reverb(80)
    m.effects.delay(64)
    m.effects.distortion(50)
    m.effects.filter_type(1)
    m.effects.set_fx(1, 0, 1, 100)
    m.arpeggiator.on()
    m.arpeggiator.rate(120)
    m.arpeggiator.style(2)  # UpDown

    log = m._midi.get_log()
    assert len(log) == 9

    # Entries 6..8 are the arp calls.
    assert log[6]["control"] == ArpeggiatorController.CC_ARP_ON
    assert log[6]["value"] == 127

    assert log[7]["control"] == ArpeggiatorController.CC_ARP_RATE
    assert log[7]["value"] == 120

    assert log[8]["control"] == ArpeggiatorController.CC_ARP_STYLE
    assert log[8]["value"] == 2

    # ``enabled`` mirrors the latest on() call.
    assert m.arpeggiator.enabled is True


def test_on_off_toggle(m: MC707) -> None:
    """``on(False)`` writes CC ARP_ON with value 0; ``enabled`` updates."""
    m.arpeggiator.on(True)
    m.arpeggiator.on(False)

    log = m._midi.get_log()
    assert len(log) == 2
    assert log[0]["control"] == ArpeggiatorController.CC_ARP_ON
    assert log[0]["value"] == 127
    assert log[1]["control"] == ArpeggiatorController.CC_ARP_ON
    assert log[1]["value"] == 0
    assert m.arpeggiator.enabled is False


# ---------------------------------------------------------------------------
# (3) ValueError on out-of-range / wrong-type inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [-1, 4, 5, 99])
def test_style_validation(m: MC707, bad: int) -> None:
    """``style`` rejects values outside ``0..3`` with ValueError."""
    with pytest.raises(ValueError, match=r"style must be"):
        m.arpeggiator.style(bad)


@pytest.mark.parametrize("bad", [-1, 4, 5, 99])
def test_octave_validation(m: MC707, bad: int) -> None:
    """``octave`` rejects values outside ``0..3`` with ValueError."""
    with pytest.raises(ValueError, match=r"octave must be"):
        m.arpeggiator.octave(bad)


@pytest.mark.parametrize(
    "method,args",
    [
        ("rate", (-1,)),
        ("rate", (128,)),
        ("gate", (-1,)),
        ("gate", (128,)),
    ],
)
def test_arp_cc_value_validation(
    m: MC707, method: str, args: tuple,
) -> None:
    """``rate`` / ``gate`` reject values outside ``0..127`` with ValueError."""
    fn = getattr(m.arpeggiator, method)
    with pytest.raises(ValueError):
        fn(*args)


@pytest.mark.parametrize(
    "bad_type", [True, "64", 1.5, None, [64]],
)
def test_arp_rejects_non_int(m: MC707, bad_type) -> None:
    """Non-int inputs are rejected with a clear ValueError."""
    with pytest.raises(ValueError):
        m.arpeggiator.rate(bad_type)
    with pytest.raises(ValueError):
        m.arpeggiator.gate(bad_type)
    with pytest.raises(ValueError):
        m.arpeggiator.style(bad_type)
    with pytest.raises(ValueError):
        m.arpeggiator.octave(bad_type)


@pytest.mark.parametrize("bad", [0, 1, "yes", None, [True]])
def test_on_requires_bool(m: MC707, bad) -> None:
    """``on`` requires a real ``bool`` — no implicit int/bool coercion."""
    with pytest.raises(ValueError, match=r"on must be a bool"):
        m.arpeggiator.on(bad)


def test_default_on_is_true() -> None:
    """``on()`` without arguments enables the arpeggiator (value=127)."""
    m = MC707()
    assert m.arpeggiator.on() is True
    log = m._midi.get_log()
    assert log[-1]["control"] == ArpeggiatorController.CC_ARP_ON
    assert log[-1]["value"] == 127
    assert m.arpeggiator.enabled is True


# ---------------------------------------------------------------------------
# (4) CC constant exports — TEMPLATE markers visible
# ---------------------------------------------------------------------------


def test_all_required_arp_cc_constants_exported() -> None:
    """Every arp CC constant listed in the task spec is defined as a
    class attribute and is an int in the standard 7-bit MIDI range."""
    expected = {
        "CC_ARP_ON": 58,
        "CC_ARP_RATE": 59,
        "CC_ARP_GATE": 60,
        "CC_ARP_STYLE": 61,
        "CC_ARP_OCTAVE": 62,
    }
    for name, expected_value in expected.items():
        assert hasattr(ArpeggiatorController, name), f"missing constant {name}"
        actual = getattr(ArpeggiatorController, name)
        assert isinstance(actual, int), f"{name} is not int: {type(actual)}"
        assert 0 <= actual <= 127, f"{name}={actual} out of CC range"
        assert actual == expected_value, (
            f"{name}: expected {expected_value}, got {actual}"
        )


def test_control_channel_is_ten() -> None:
    """``CONTROL_CHANNEL`` is 10 (matches project convention)."""
    assert ArpeggiatorController.CONTROL_CHANNEL == 10


def test_style_enum_constants() -> None:
    """Style enum values are the four documented integers."""
    assert ArpeggiatorController.STYLE_UP == 0
    assert ArpeggiatorController.STYLE_DOWN == 1
    assert ArpeggiatorController.STYLE_UPDOWN == 2
    assert ArpeggiatorController.STYLE_RANDOM == 3