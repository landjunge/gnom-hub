"""Tests for :mod:`mc707.control.effects`.

Covers the producer-required 9-message verification, every effect
method's CC dispatch, strict ``ValueError`` validation on filter_type
(0..3) and ``set_fx(track 1..8, slot 0..3)``, and the public CC
constant exports.

The mock log is the source of truth — every method is expected to
write exactly one ``control_change`` entry per call on the controller's
:attr:`CONTROL_CHANNEL`.
"""

from __future__ import annotations

import pytest

from mc707 import MC707
from mc707.control.effects import EffectsController


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode."""
    return MC707()


# Convenience for accessing the mido-channel index that MIDIIO records.
# CONTROL_CHANNEL = 10 (1-based) → mido channel 9 (0-based).
_CTRL_MIDO_CH = EffectsController.CONTROL_CHANNEL - 1


# ---------------------------------------------------------------------------
# (1) Producer verification — 9 messages in the right order
# ---------------------------------------------------------------------------


def test_producer_nine_message_sequence(m: MC707) -> None:
    """Re-run the producer verification script from the task spec.

    The expected sequence is:

        0. cutoff(100)
        1. reverb(80)
        2. delay(64)
        3. distortion(50)
        4. filter_type(1)             # HPF
        5. set_fx(1, 0, 1, 100)       # track 1, slot 0
        6. arpeggiator.on()
        7. arpeggiator.rate(120)
        8. arpeggiator.style(2)       # UpDown

    The arp entries (6..8) are exercised here only to confirm the
    effects calls land in the right slots before the arp entries —
    dedicated arp coverage lives in ``test_arpeggiator.py``.
    """
    m.effects.cutoff(100)
    m.effects.reverb(80)
    m.effects.delay(64)
    m.effects.distortion(50)
    m.effects.filter_type(1)  # HPF
    m.effects.set_fx(1, 0, 1, 100)
    m.arpeggiator.on()
    m.arpeggiator.rate(120)
    m.arpeggiator.style(2)  # UpDown

    log = m._midi.get_log()
    assert len(log) == 9

    # Each entry is a control_change on the control channel
    # (mido ch 9 == MIDI ch 10) unless the call routed to a per-track
    # channel via set_fx(track=1).
    expected = [
        # (control, value, channel)
        (74, 100, _CTRL_MIDO_CH),  # cutoff
        (91, 80, _CTRL_MIDO_CH),   # reverb
        (92, 64, _CTRL_MIDO_CH),   # delay
        (94, 50, _CTRL_MIDO_CH),   # distortion
        (77, 1, _CTRL_MIDO_CH),    # filter_type HPF
        (20, 100, _CTRL_MIDO_CH),  # set_fx(1, 0, 1, 100) → ch 10, CC 20+0=20
        (58, 127, _CTRL_MIDO_CH),  # arp.on() → CC 58 val 127
        (59, 120, _CTRL_MIDO_CH),  # arp.rate(120) → CC 59 val 120
        (61, 2, _CTRL_MIDO_CH),    # arp.style(2) → CC 61 val 2
    ]
    for idx, (cc, val, ch) in enumerate(expected):
        entry = log[idx]
        assert entry["type"] == "control_change", f"entry {idx}: {entry}"
        assert entry["channel"] == ch, (
            f"entry {idx}: channel {entry['channel']} != {ch}"
        )
        assert entry["control"] == cc, (
            f"entry {idx}: control {entry['control']} != {cc}"
        )
        assert entry["value"] == val, (
            f"entry {idx}: value {entry['value']} != {val}"
        )


# ---------------------------------------------------------------------------
# (2) Every effects method dispatches on the control channel
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,args,expected_cc",
    [
        ("cutoff",      (64,),  EffectsController.CC_CUTOFF),
        ("resonance",   (64,),  EffectsController.CC_RESONANCE),
        ("attack",      (64,),  EffectsController.CC_ATTACK),
        ("decay",       (64,),  EffectsController.CC_DECAY),
        ("sustain",     (64,),  EffectsController.CC_SUSTAIN),
        ("release",     (64,),  EffectsController.CC_RELEASE),
        ("reverb",      (64,),  EffectsController.CC_REVERB),
        ("chorus",      (64,),  EffectsController.CC_CHORUS),
        ("delay",       (64,),  EffectsController.CC_DELAY),
        ("distortion",  (64,),  EffectsController.CC_DISTORTION),
        ("filter_type", (0,),   EffectsController.CC_FILTER_TYPE),
    ],
)
def test_single_cc_method_dispatch(
    m: MC707, method: str, args: tuple, expected_cc: int,
) -> None:
    """Every single-CC method writes exactly one ``control_change`` on
    the control channel with the correct CC number."""
    fn = getattr(m.effects, method)
    assert fn(*args) is True

    log = m._midi.get_log()
    assert len(log) == 1
    entry = log[0]
    assert entry["type"] == "control_change"
    assert entry["channel"] == _CTRL_MIDO_CH
    assert entry["control"] == expected_cc
    assert entry["value"] == args[0]


@pytest.mark.parametrize(
    "filter_value,filter_const",
    [
        (0, "FILTER_LPF"),
        (1, "FILTER_HPF"),
        (2, "FILTER_BPF"),
        (3, "FILTER_NOTCH"),
    ],
)
def test_filter_type_enum_values(
    m: MC707, filter_value: int, filter_const: str,
) -> None:
    """The four documented filter-type enum values all dispatch."""
    expected = getattr(EffectsController, filter_const)
    assert filter_value == expected

    assert m.effects.filter_type(filter_value) is True
    log = m._midi.get_log()
    assert log[-1]["control"] == EffectsController.CC_FILTER_TYPE
    assert log[-1]["value"] == filter_value


# ---------------------------------------------------------------------------
# (3) ValueError on out-of-range / wrong-type inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,args",
    [
        ("cutoff",     (-1,)),
        ("cutoff",     (128,)),
        ("resonance",  (-1,)),
        ("resonance",  (128,)),
        ("attack",     (-1,)),
        ("decay",      (128,)),
        ("sustain",    (-1,)),
        ("release",    (128,)),
        ("reverb",     (-1,)),
        ("chorus",     (128,)),
        ("delay",      (-1,)),
        ("distortion", (128,)),
        ("filter_type", (-1,)),
        ("filter_type", (4,)),
        ("filter_type", (99,)),
    ],
)
def test_effects_value_validation(m: MC707, method: str, args: tuple) -> None:
    """Single-CC methods reject out-of-range values with ValueError."""
    fn = getattr(m.effects, method)
    with pytest.raises(ValueError):
        fn(*args)


@pytest.mark.parametrize("bad_type", [True, "64", 1.5, None, [64]])
def test_effects_rejects_non_int(m: MC707, bad_type) -> None:
    """Non-int inputs are rejected with a clear ValueError."""
    with pytest.raises(ValueError):
        m.effects.cutoff(bad_type)
    with pytest.raises(ValueError):
        m.effects.filter_type(bad_type)


# ---------------------------------------------------------------------------
# (4) set_fx — track / slot / param / value validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_track", [0, -1, 9, 99, 1000])
def test_set_fx_track_validation(m: MC707, bad_track: int) -> None:
    """``set_fx`` rejects track outside ``1..8`` with ValueError."""
    with pytest.raises(ValueError, match=r"track must be between 1 and 8"):
        m.effects.set_fx(bad_track, 0, 0, 0)


@pytest.mark.parametrize("bad_slot", [-1, 4, 5, 99])
def test_set_fx_slot_validation(m: MC707, bad_slot: int) -> None:
    """``set_fx`` rejects slot outside ``0..3`` with ValueError."""
    with pytest.raises(ValueError, match=r"slot must be between 0 and 3"):
        m.effects.set_fx(1, bad_slot, 0, 0)


@pytest.mark.parametrize("bad_param,label", [(-1, "param"), (128, "param")])
def test_set_fx_param_validation(m: MC707, bad_param: int, label: str) -> None:
    """``set_fx`` rejects param outside ``0..127`` with ValueError."""
    with pytest.raises(ValueError, match=rf"{label} must be between"):
        m.effects.set_fx(1, 0, bad_param, 0)


@pytest.mark.parametrize("bad_value", [-1, 128])
def test_set_fx_value_validation(m: MC707, bad_value: int) -> None:
    """``set_fx`` rejects value outside ``0..127`` with ValueError."""
    with pytest.raises(ValueError, match=r"value must be between"):
        m.effects.set_fx(1, 0, 0, bad_value)


@pytest.mark.parametrize(
    "bad_type", [True, "1", 1.0, None, [1]],
)
def test_set_fx_rejects_non_int(m: MC707, bad_type) -> None:
    """Non-int inputs to set_fx raise ValueError on the first bad arg."""
    with pytest.raises(ValueError):
        m.effects.set_fx(bad_type, 0, 0, 0)
    with pytest.raises(ValueError):
        m.effects.set_fx(1, bad_type, 0, 0)


@pytest.mark.parametrize(
    "track,slot,expected_cc",
    [
        (1, 0, 20),
        (1, 1, 21),
        (1, 2, 22),
        (1, 3, 23),
        (5, 0, 20),
        (7, 3, 23),
    ],
)
def test_set_fx_cc_formula(
    m: MC707, track: int, slot: int, expected_cc: int,
) -> None:
    """``set_fx(track, slot, ...)`` writes CC ``CC_FX_SLOT_BASE + slot``
    on MIDI channel ``track + TRACK_CHANNEL_OFFSET`` (1-based).

    Note: track=8 maps to MIDI channel 17 which is out of range and is
    tested separately in ``test_set_fx_track_8_silent_clamp``.
    """
    expected_channel_mido = (track + EffectsController.TRACK_CHANNEL_OFFSET) - 1

    assert m.effects.set_fx(track, slot, 0, 100) is True
    log = m._midi.get_log()
    entry = log[-1]
    assert entry["type"] == "control_change"
    assert entry["channel"] == expected_channel_mido
    assert entry["control"] == expected_cc
    assert entry["value"] == 100


def test_set_fx_track_8_silent_clamp(m: MC707) -> None:
    """Track 8 maps via the ``track + 9`` formula to MIDI channel 17,
    which is outside the 1..16 MIDI range. The underlying MIDIIO
    silently clamps this to channel 16 (mido channel 15). This is a
    documented TEMPLATE / known limitation — see the ``set_fx``
    docstring. The test pins the behaviour so future refactors that
    address track 8 properly (e.g. via SysEx) will need to update
    this expectation."""
    assert m.effects.set_fx(8, 0, 0, 64) is True
    log = m._midi.get_log()
    entry = log[-1]
    # 1-based channel 17 → MIDIIO clamps to 16 → mido channel 15.
    assert entry["channel"] == 15
    assert entry["control"] == EffectsController.CC_FX_SLOT_BASE + 0
    assert entry["value"] == 64


def test_set_fx_param_value_passed_through(m: MC707) -> None:
    """``set_fx`` accepts arbitrary param values in 0..127 without
    crashing (param is currently not packed into the wire CC value —
    see the TEMPLATE note in :meth:`EffectsController.set_fx`)."""
    assert m.effects.set_fx(3, 2, 77, 99) is True
    log = m._midi.get_log()
    entry = log[-1]
    assert entry["control"] == EffectsController.CC_FX_SLOT_BASE + 2
    assert entry["value"] == 99  # value lands in the CC value byte


# ---------------------------------------------------------------------------
# (5) CC constant exports
# ---------------------------------------------------------------------------


def test_all_required_cc_constants_exported() -> None:
    """Every CC constant listed in the task spec is defined as a class
    attribute and is an int in the standard 7-bit MIDI range."""
    expected = {
        "CC_CUTOFF": 74,
        "CC_RESONANCE": 71,
        "CC_ATTACK": 73,
        "CC_DECAY": 75,
        "CC_SUSTAIN": 79,
        "CC_RELEASE": 72,
        "CC_REVERB": 91,
        "CC_CHORUS": 93,
        "CC_DELAY": 92,
        "CC_DISTORTION": 94,
        "CC_FILTER_TYPE": 77,
    }
    for name, expected_value in expected.items():
        assert hasattr(EffectsController, name), f"missing constant {name}"
        actual = getattr(EffectsController, name)
        assert isinstance(actual, int), f"{name} is not int: {type(actual)}"
        assert 0 <= actual <= 127, f"{name}={actual} out of CC range"
        assert actual == expected_value, (
            f"{name}: expected {expected_value}, got {actual}"
        )


def test_control_channel_is_ten() -> None:
    """``CONTROL_CHANNEL`` is 10 (matches project convention)."""
    assert EffectsController.CONTROL_CHANNEL == 10


def test_filter_enum_constants() -> None:
    """Filter-type enum values are the four documented integers."""
    assert EffectsController.FILTER_LPF == 0
    assert EffectsController.FILTER_HPF == 1
    assert EffectsController.FILTER_BPF == 2
    assert EffectsController.FILTER_NOTCH == 3