"""Tests for the MC-707 Sound system.

Covers the four new modules added in Track 1 of the sound-system work:

  * :mod:`mc707.models.sound`
    — Pydantic Sound + per-section sub-models + param-dict round-trip
  * :mod:`mc707.control.sound_editor`
    — Live DT1 dispatch + cache + apply / apply_partial / capture
  * :mod:`mc707.registry.sound_registry`
    — In-memory named cache
  * :mod:`mc707.persistence.sound_store`
    — JSON persistence on disk

All tests run in mock mode — no MC-707 hardware required.

VERIFY HOOK
-----------
The :class:`SoundEditor` tests assert that ``set_param`` actually
dispatches a DT1 frame to the MIDI log (rather than silently
no-op'ing). This is the dispatch-path regression guard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mc707 import (
    MC707,
    PARAM_ADDRESSES,
    Sound,
    SoundEditor,
    SoundRegistry,
    SoundStore,
)
from mc707.models.sound import (
    AmpEnvelope,
    FilterEnvelope,
    FilterParams,
    LFOParams,
    OscillatorParams,
    _WAVE_TO_ID,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def m() -> MC707:
    """Fresh MC707 instance in mock mode (no hardware)."""
    return MC707()


@pytest.fixture
def tmp_store(tmp_path: Path) -> SoundStore:
    """SoundStore rooted under pytest's tmp_path (auto-cleaned)."""
    return SoundStore(tmp_path / "sounds")


# ===========================================================================
# 1. Sound model — defaults, validation, sub-model ranges
# ===========================================================================


def test_sound_defaults_to_safe_init() -> None:
    """Sound() with no args yields a valid Init patch with sensible defaults."""
    s = Sound()
    assert s.name == "Init"
    assert s.oscillator.wave == "saw"
    assert s.filter.cutoff == 64
    assert s.amp_envelope.sustain == 96
    assert s.filter_envelope.amount == 32
    assert s.lfo.target == "pitch"


def test_sound_rejects_extra_fields() -> None:
    """``extra='forbid'`` — unknown top-level keys raise ValidationError."""
    with pytest.raises(Exception):
        Sound.model_validate({"name": "X", "unknown_field": 42})


def test_sound_submodel_rejects_extra_fields() -> None:
    """Each sub-model also forbids extra keys."""
    with pytest.raises(Exception):
        OscillatorParams(wave="sine", mystery=42)  # type: ignore[call-arg]


def test_sound_validates_param_ranges() -> None:
    """Out-of-range values raise ValidationError on the relevant sub-model."""
    with pytest.raises(Exception):
        Sound(filter=FilterParams(cutoff=200))
    with pytest.raises(Exception):
        Sound(amp_envelope=AmpEnvelope(attack=-1))
    with pytest.raises(Exception):
        Sound(filter_envelope=FilterEnvelope(amount=200))
    with pytest.raises(Exception):
        Sound(lfo=LFOParams(rate=200))


def test_sound_name_length_bounds() -> None:
    """``name`` is constrained to 1..32 characters."""
    with pytest.raises(Exception):
        Sound(name="")
    with pytest.raises(Exception):
        Sound(name="x" * 33)
    # 32 chars is exactly OK
    Sound(name="x" * 32)


def test_sound_pitch_signed_range() -> None:
    """``oscillator.pitch`` accepts the full signed semitone range."""
    Sound(oscillator=OscillatorParams(pitch=-24))
    Sound(oscillator=OscillatorParams(pitch=24))
    with pytest.raises(Exception):
        Sound(oscillator=OscillatorParams(pitch=-25))
    with pytest.raises(Exception):
        Sound(oscillator=OscillatorParams(pitch=25))


# ===========================================================================
# 2. Sound → param-dict projection (used by SoundEditor)
# ===========================================================================


def test_to_param_dict_emits_all_19_keys() -> None:
    """to_param_dict emits one entry per parameter across all 5 sections."""
    s = Sound()
    params = s.to_param_dict()
    # 3 OSC + 4 Filter + 4 Amp + 5 FilterEnv + 3 LFO = 19
    assert len(params) == 19
    assert "osc_wave" in params
    assert "filter_cutoff" in params
    assert "amp_attack" in params
    assert "filter_env_amount_total" in params
    assert "lfo_rate" in params


def test_to_param_dict_signed_fields_shift_to_unsigned() -> None:
    """Signed fields (pitch, env_amount) are shifted +64 into 7-bit unsigned."""
    s = Sound(
        oscillator=OscillatorParams(pitch=12),
        filter=FilterParams(env_amount=-32),
        filter_envelope=FilterEnvelope(amount=-10),
    )
    p = s.to_param_dict()
    assert p["osc_pitch"] == 12 + 64
    assert p["filter_env_amount"] == -32 + 64
    assert p["filter_env_amount_total"] == -10 + 64


def test_to_param_dict_maps_enums_to_ids() -> None:
    """Enum fields (wave, filter type, lfo target) are mapped to integer IDs."""
    s = Sound(
        oscillator=OscillatorParams(wave="square"),
        filter=FilterParams(type="hpf"),
        lfo=LFOParams(target="cutoff"),
    )
    p = s.to_param_dict()
    assert p["osc_wave"] == _WAVE_TO_ID["square"]
    assert p["filter_type"] == 1  # hpf
    assert p["lfo_target"] == 1  # cutoff


def test_param_dict_round_trip_preserves_values() -> None:
    """``Sound → to_param_dict → from_param_dict`` reproduces the same dict."""
    original = Sound(
        name="Round-trip",
        category="bass",
        oscillator=OscillatorParams(wave="square", pitch=-12, level=80),
        filter=FilterParams(type="hpf", cutoff=100, resonance=20, env_amount=-10),
        amp_envelope=AmpEnvelope(attack=10, decay=50, sustain=70, release=40),
        filter_envelope=FilterEnvelope(
            attack=5, decay=30, sustain=50, release=20, amount=40
        ),
        lfo=LFOParams(rate=60, depth=20, target="cutoff"),
    )
    rebuilt = Sound.from_param_dict(original.to_param_dict())
    assert rebuilt.to_param_dict() == original.to_param_dict()


def test_from_param_dict_ignores_unknown_keys() -> None:
    """Unknown param names are silently skipped (forward-compat for chart fills)."""
    sound = Sound.from_param_dict(
        {"osc_wave": _WAVE_TO_ID["square"], "mystery_param": 99}
    )
    assert sound.oscillator.wave == "square"


def test_from_param_dict_clamps_out_of_range() -> None:
    """Out-of-range wire values are clamped into the sub-model's allowed range."""
    # osc_pitch=200 → pitch = 200 - 64 = 136, clamped to +24
    over = Sound.from_param_dict({"osc_pitch": 200})
    assert over.oscillator.pitch == 24
    # osc_pitch=0 → pitch = 0 - 64 = -64, clamped to -24
    under = Sound.from_param_dict({"osc_pitch": 0})
    assert under.oscillator.pitch == -24


def test_from_param_dict_missing_keys_use_defaults() -> None:
    """An empty dict produces a Sound with default values."""
    sound = Sound.from_param_dict({})
    defaults = Sound()
    assert sound.to_param_dict() == defaults.to_param_dict()


# ===========================================================================
# 3. SoundEditor — live dispatch (the verify hook)
# ===========================================================================


def test_editor_set_param_dispatches_dt1_frame(m: MC707) -> None:
    """set_param produces exactly one DT1 SysEx frame in the log."""
    m._midi.clear_log()
    ok = m.sound_editor.set_param("filter_cutoff", 100)
    assert ok is True
    log = m._midi.get_log()
    assert len(log) == 1
    msg = log[-1]
    # Standard DT1 frame shape: F0 + header(6) + 0x12 + addr(2) + payload(2) + cs + F7
    assert len(msg) == 14
    assert msg[0] == 0xF0
    assert msg[-1] == 0xF7
    assert msg[7] == 0x12  # DT1 command
    # Address bytes match the registry
    addr_hi, addr_lo, _param_offset = PARAM_ADDRESSES["filter_cutoff"]
    assert msg[8] == addr_hi
    assert msg[9] == addr_lo
    # Payload: value byte + zero pad
    assert msg[10] == 100
    assert msg[11] == 0


def test_editor_set_param_rejects_unknown_name(m: MC707) -> None:
    """Unknown param name raises ValueError and does not touch the log."""
    m._midi.clear_log()
    with pytest.raises(ValueError, match=r"Unknown parameter"):
        m.sound_editor.set_param("totally_made_up", 42)
    assert m._midi.get_log() == []


def test_editor_set_param_validates_value_range(m: MC707) -> None:
    """Out-of-range value raises ValueError; type errors are also rejected."""
    with pytest.raises(ValueError, match=r"0\.\.127"):
        m.sound_editor.set_param("filter_cutoff", 200)
    with pytest.raises(ValueError, match=r"0\.\.127"):
        m.sound_editor.set_param("filter_cutoff", -1)
    with pytest.raises(ValueError, match=r"int"):
        m.sound_editor.set_param("filter_cutoff", "100")  # type: ignore[arg-type]


def test_editor_get_param_returns_cached_value(m: MC707) -> None:
    """get_param returns None before any set, and the last-written value after."""
    assert m.sound_editor.get_param("amp_attack") is None
    m.sound_editor.set_param("amp_attack", 42)
    assert m.sound_editor.get_param("amp_attack") == 42
    # Other params remain unset
    assert m.sound_editor.get_param("filter_cutoff") is None


def test_editor_apply_pushes_every_param(m: MC707) -> None:
    """apply(sound) dispatches one DT1 frame per param, in canonical order."""
    m._midi.clear_log()
    sound = Sound(
        oscillator=OscillatorParams(wave="square", pitch=0, level=100),
        filter=FilterParams(cutoff=80, resonance=10),
        amp_envelope=AmpEnvelope(attack=20),
    )
    ok = m.sound_editor.apply(sound)
    assert ok is True
    log = m._midi.get_log()
    assert len(log) == 19  # one frame per param
    # Cache reflects the writes
    assert m.sound_editor.get_param("filter_cutoff") == 80
    assert m.sound_editor.get_param("amp_attack") == 20


def test_editor_apply_partial_only_named_params(m: MC707) -> None:
    """apply_partial dispatches only the listed params, preserving order."""
    m._midi.clear_log()
    sound = Sound(filter=FilterParams(cutoff=99, resonance=33))
    ok = m.sound_editor.apply_partial(sound, ["filter_cutoff"])
    assert ok is True
    log = m._midi.get_log()
    assert len(log) == 1
    assert log[-1][10] == 99
    # Cache only has the partial write
    assert m.sound_editor.get_param("filter_cutoff") == 99
    assert m.sound_editor.get_param("filter_resonance") is None


def test_editor_apply_partial_rejects_unknown_param(m: MC707) -> None:
    """apply_partial with a param not present in the Sound raises ValueError."""
    sound = Sound()
    with pytest.raises(ValueError, match=r"not in Sound"):
        m.sound_editor.apply_partial(sound, ["nonexistent_param"])


def test_editor_capture_reconstructs_from_cache(m: MC707) -> None:
    """capture() returns a Sound reflecting only the cached writes."""
    m.sound_editor.set_param("filter_cutoff", 77)
    m.sound_editor.set_param("lfo_rate", 50)
    captured = m.sound_editor.capture()
    assert captured.filter.cutoff == 77
    assert captured.lfo.rate == 50
    # Unset fields fall back to defaults
    assert captured.amp_envelope.sustain == 96


def test_editor_capture_preserves_template_metadata(m: MC707) -> None:
    """capture(template) keeps the template's name + category but overlays cached params."""
    m.sound_editor.set_param("filter_cutoff", 88)
    template = Sound(name="MyLead", category="lead")
    captured = m.sound_editor.capture(template)
    assert captured.name == "MyLead"
    assert captured.category == "lead"
    assert captured.filter.cutoff == 88
    # Other params come from defaults (cache miss)
    assert captured.amp_envelope.sustain == 96


def test_editor_apply_capture_round_trip(m: MC707) -> None:
    """``apply(sound); capture()`` round-trips within a single session."""
    original = Sound(
        name="RT",
        oscillator=OscillatorParams(wave="triangle", pitch=12),
        filter=FilterParams(cutoff=42, resonance=15, env_amount=-20),
        amp_envelope=AmpEnvelope(attack=5, decay=30, sustain=80, release=40),
    )
    assert m.sound_editor.apply(original) is True
    captured = m.sound_editor.capture()
    assert captured.to_param_dict() == original.to_param_dict()


def test_editor_clear_cache_resets_get(m: MC707) -> None:
    """clear_cache wipes the cache; subsequent get_param returns None."""
    m.sound_editor.set_param("amp_attack", 10)
    assert m.sound_editor.get_param("amp_attack") == 10
    m.sound_editor.clear_cache()
    assert m.sound_editor.get_param("amp_attack") is None


def test_editor_known_params_covers_all_sections() -> None:
    """known_params() includes at least one param from each of the 5 sections."""
    params = SoundEditor.known_params()
    assert any(p.startswith("osc_") for p in params)
    assert any(p.startswith("filter_") for p in params)
    assert any(p.startswith("amp_") for p in params)
    assert any(p.startswith("filter_env_") for p in params)
    assert any(p.startswith("lfo_") for p in params)


def test_editor_address_of_returns_tuple() -> None:
    """address_of returns the registered address tuple."""
    assert SoundEditor.address_of("filter_cutoff") == (0x18, 0x10, 0x01)
    with pytest.raises(ValueError, match=r"Unknown parameter"):
        SoundEditor.address_of("nope")


# ===========================================================================
# 4. SoundRegistry — in-memory named cache
# ===========================================================================


def test_registry_register_get_list_remove() -> None:
    """register / get / list / remove behave as documented."""
    reg = SoundRegistry()
    reg.register(Sound(name="A"))
    reg.register(Sound(name="B"))
    assert reg.get("A") is not None
    assert reg.get("A").name == "A"
    assert reg.list() == ["A", "B"]  # sorted
    assert reg.remove("A") is True
    assert reg.get("A") is None
    assert reg.remove("missing") is False


def test_registry_require_raises_on_missing() -> None:
    """require raises KeyError when the name is unknown."""
    reg = SoundRegistry()
    with pytest.raises(KeyError, match=r"not in registry"):
        reg.require("nope")


def test_registry_overwrites_on_duplicate_register() -> None:
    """Registering the same name twice keeps the latest entry."""
    reg = SoundRegistry()
    reg.register(Sound(name="X", category="lead"))
    reg.register(Sound(name="X", category="bass"))
    assert reg.get("X").category == "bass"
    assert len(reg) == 1


def test_registry_len_contains_iter() -> None:
    """len / ``in`` / iter work as expected."""
    reg = SoundRegistry()
    reg.register(Sound(name="Z"))
    assert len(reg) == 1
    assert "Z" in reg
    assert "missing" not in reg
    assert list(reg) == ["Z"]
    assert reg.all()[0].name == "Z"


def test_registry_clear() -> None:
    """clear() drops all entries."""
    reg = SoundRegistry()
    reg.register(Sound(name="A"))
    reg.register(Sound(name="B"))
    reg.clear()
    assert len(reg) == 0
    assert reg.list() == []


# ===========================================================================
# 5. SoundStore — JSON persistence
# ===========================================================================


def test_store_save_and_load_round_trip(tmp_store: SoundStore) -> None:
    """save() writes JSON; load() returns an equal Sound."""
    original = Sound(name="Bass-01", category="bass", filter=FilterParams(cutoff=99))
    path = tmp_store.save(original)
    assert path.exists()
    loaded = tmp_store.load("Bass-01")
    assert loaded.to_param_dict() == original.to_param_dict()
    assert loaded.category == "bass"


def test_store_save_uses_alternate_name(tmp_store: SoundStore) -> None:
    """save(sound, name='X') stores under X regardless of sound.name."""
    tmp_store.save(Sound(name="Original"), name="Alias")
    assert "alias" in tmp_store.list()
    assert "original" not in tmp_store.list()
    # Loadable under the alias
    loaded = tmp_store.load("Alias")
    assert loaded.name == "Original"


def test_store_load_missing_raises(tmp_store: SoundStore) -> None:
    """load() raises FileNotFoundError for unknown names."""
    with pytest.raises(FileNotFoundError, match=r"No sound named"):
        tmp_store.load("ghost")


def test_store_delete(tmp_store: SoundStore) -> None:
    """delete() returns True on success, False when the file is absent."""
    tmp_store.save(Sound(name="Doomed"))
    assert tmp_store.delete("Doomed") is True
    assert tmp_store.delete("Doomed") is False
    assert "doomed" not in tmp_store.list()


def test_store_list_empty_when_dir_missing(tmp_store: SoundStore) -> None:
    """list() returns [] when the base dir doesn't exist yet."""
    assert tmp_store.list() == []


def test_store_list_sorted(tmp_store: SoundStore) -> None:
    """list() returns names in alphabetical order."""
    tmp_store.save(Sound(name="Charlie"))
    tmp_store.save(Sound(name="Alpha"))
    tmp_store.save(Sound(name="Bravo"))
    assert tmp_store.list() == ["alpha", "bravo", "charlie"]


def test_store_slugify_handles_special_characters(tmp_store: SoundStore) -> None:
    """Names with spaces / punctuation become filesystem-safe slugs."""
    path = tmp_store.save(Sound(name="My Bass #1!"))
    assert path.exists()
    assert path.stem  # non-empty
    # Loadable via the original name
    loaded = tmp_store.load("My Bass #1!")
    assert loaded.name == "My Bass #1!"


def test_store_save_avoids_overwrite(tmp_store: SoundStore) -> None:
    """Two saves of the same name produce two distinct files."""
    p1 = tmp_store.save(Sound(name="Same"))
    p2 = tmp_store.save(Sound(name="Same"))
    assert p1 != p2
    assert p1.exists() and p2.exists()
    assert len(tmp_store.list()) == 2


def test_store_creates_base_dir(tmp_path: Path) -> None:
    """save() creates the base directory if it doesn't exist."""
    nested = tmp_path / "deeply" / "nested" / "dir"
    store = SoundStore(nested)
    assert not store.base_dir.exists()
    store.save(Sound(name="Auto"))
    assert store.base_dir.exists()
    assert (store.base_dir / "auto.json").exists()


def test_store_json_is_human_readable(tmp_store: SoundStore) -> None:
    """The on-disk format is a JSON document (not a Pydantic pickle)."""
    tmp_store.save(Sound(name="Readable", filter=FilterParams(cutoff=33)))
    raw = json.loads((tmp_store.base_dir / "readable.json").read_text())
    assert raw["name"] == "Readable"
    assert raw["filter"]["cutoff"] == 33


def test_store_exists(tmp_store: SoundStore) -> None:
    """exists() reflects whether a sound is on disk."""
    assert tmp_store.exists("Nothing") is False
    tmp_store.save(Sound(name="There"))
    assert tmp_store.exists("There") is True


# ===========================================================================
# 6. MC707 façade wiring
# ===========================================================================


def test_facade_exposes_all_sound_components() -> None:
    """MC707() in mock mode exposes sound_editor, sound_registry, sound_store."""
    m = MC707()
    assert isinstance(m.sound_editor, SoundEditor)
    assert isinstance(m.sound_registry, SoundRegistry)
    assert isinstance(m.sound_store, SoundStore)


def test_facade_default_sound_dir_is_home() -> None:
    """Default sound_dir is ~/.mc707/sounds when no override is given."""
    m = MC707()
    assert ".mc707" in str(m.sound_store.base_dir)
    assert m.sound_store.base_dir.name == "sounds"


def test_facade_custom_sound_dir(tmp_path: Path) -> None:
    """sound_dir constructor arg overrides the default location."""
    target = tmp_path / "my_sounds"
    m = MC707(sound_dir=target)
    assert m.sound_store.base_dir == target


def test_facade_sound_components_are_connected(m: MC707) -> None:
    """End-to-end: sound_editor dispatches, sound_store writes, sound_registry caches."""
    sound = Sound(name="Lead", filter=FilterParams(cutoff=64))
    # Editor dispatches DT1
    assert m.sound_editor.apply(sound) is True
    assert m.sound_editor.get_param("filter_cutoff") == 64
    # Store writes JSON
    path = m.sound_store.save(sound)
    assert path.exists()
    # Registry caches in memory
    m.sound_registry.register(sound)
    assert "Lead" in m.sound_registry