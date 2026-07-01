"""Tests for save_soul_fact_smart — the deduplicating soul-memory writer.

These tests cover the 6 requirements from the spec:
  1. MIN_VALUE_LENGTH rejects short facts (logging + no DB write)
  2. Key normalization (Layer_Disziplin-Regel == layer_disziplin_regel)
  3. Key-prefix dedup (layer_disziplin_v2 → merges into layer_disziplin)
  4. Value-similarity dedup (Jaccard ≥ 0.6 → merges into best-scored slot)
  5. No-similarity → INSERT normal
  6. Cleanup hook triggers when count > MAX_SOUL_FACTS * 1.2
Plus one wrapper test for the preserved permission check.

All tests use the `isolated_db` fixture (autouse) which gives each test
its own temp SQLite DB with a fresh `soul_memory` table. No hub process
needs to be running.
"""

import pytest

from gnom_hub.db.connection import get_db_conn
from gnom_hub.db.soul_repo import (
    _jaccard,
    _normalize_key,
    _strip_version_suffix,
    save_soul_fact,
    save_soul_fact_smart,
)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _count_soul_facts() -> int:
    with get_db_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]


def _get_soul_row(key: str):
    with get_db_conn() as conn:
        return conn.execute(
            "SELECT key, value, priority, agent FROM soul_memory WHERE key = ?",
            (key,),
        ).fetchone()


def _all_soul_keys():
    with get_db_conn() as conn:
        return [r["key"] for r in conn.execute("SELECT key FROM soul_memory").fetchall()]


# ── 1. MIN_VALUE_LENGTH check ──────────────────────────────────────────────
def test_min_value_length_rejects_short(isolated_db):
    """Values shorter than MIN_VALUE_LENGTH (15) must be rejected with no DB write."""
    save_soul_fact_smart(
        "some_key_name", "too short", agent="System", priority="medium"
    )
    assert _count_soul_facts() == 0, "Short fact must not be inserted"


def test_min_value_length_accepts_15_chars(isolated_db):
    """Exactly MIN_VALUE_LENGTH (15 chars after strip) must be accepted."""
    save_soul_fact_smart(
        "fifteen_char_key", "123456789012345", agent="System", priority="medium"
    )
    assert _count_soul_facts() == 1
    row = _get_soul_row("fifteen_char_key")
    assert row["value"] == "123456789012345"


def test_min_value_length_rejects_after_strip(isolated_db):
    """Whitespace must be stripped before length check (so '   x   ' is too short)."""
    save_soul_fact_smart("trimmed_key", "   ab   ", agent="System", priority="medium")
    assert _count_soul_facts() == 0


# ── 2. Key normalization ───────────────────────────────────────────────────
def test_key_normalization_dedup(isolated_db):
    """Two keys that normalize to the same form must merge via exact-match."""
    save_soul_fact_smart(
        "Layer_Disziplin-Regel",
        "Die Layer-Disziplin-Regel sagt: Showbox nutzt L1-L2-L3.",
        agent="SoulAG",
        priority="medium",
    )
    assert _count_soul_facts() == 1
    assert _get_soul_row("layer_disziplin_regel") is not None
    original_value = _get_soul_row("layer_disziplin_regel")["value"]

    # Second write with differently-cased key normalizes to the same slot.
    save_soul_fact_smart(
        "layer_disziplin_regel",
        "Die Layer-Disziplin-Regel sagt: Showbox nutzt L1-L2-L3 plus zusätzliche Erklärung.",
        agent="SoulAG",
        priority="high",
    )
    assert _count_soul_facts() == 1, "Should still be one row (exact-match dedup)"
    row = _get_soul_row("layer_disziplin_regel")
    assert row is not None
    # The longer value wins.
    assert len(row["value"]) >= len(original_value)
    # Priority bumped to high.
    assert row["priority"] == "high"


# ── 3. Key-prefix dedup (version suffix) ───────────────────────────────────
def test_prefix_dedup_merges_versioned(isolated_db):
    """layer_disziplin_v2 must merge into existing layer_disziplin."""
    save_soul_fact_smart(
        "layer_disziplin",
        "Drei Layer: L1=user, L2=logic, L3=data.",
        agent="SoulAG",
        priority="medium",
    )
    assert _count_soul_facts() == 1
    assert _get_soul_row("layer_disziplin") is not None

    save_soul_fact_smart(
        "layer_disziplin_v2",
        "Drei Layer: L1=user, L2=logic, L3=data. Plus Hinweis: KEIN L4.",
        agent="SoulAG",
        priority="medium",
    )
    keys = _all_soul_keys()
    assert "layer_disziplin" in keys
    assert "layer_disziplin_v2" not in keys, "v2 key should be merged into base"
    assert _count_soul_facts() == 1
    # Longer value wins.
    row = _get_soul_row("layer_disziplin")
    assert "KEIN L4" in row["value"]


def test_prefix_dedup_strips_version3_and_p1(isolated_db):
    """_version3, _p1, _part1 suffixes are all recognized as version markers."""
    save_soul_fact_smart("rule_set", "Original rule content.", agent="System", priority="medium")
    save_soul_fact_smart("rule_set_version3", "Newer rule content (longer).", agent="System", priority="medium")
    save_soul_fact_smart("rule_set_p1", "Even newer.", agent="System", priority="medium")
    save_soul_fact_smart("rule_set_part1", "Yet another.", agent="System", priority="medium")
    keys = _all_soul_keys()
    assert keys == ["rule_set"], f"All versioned variants should merge, got {keys}"
    # The last longer value wins (each merge picks the longer of the two).
    assert _get_soul_row("rule_set")["value"] == "Newer rule content (longer)."


def test_prefix_dedup_does_not_strip_non_version(isolated_db):
    """_regel, _blacklist etc. are NOT version suffixes — keep separate keys."""
    save_soul_fact_smart(
        "layer_disziplin_regel", "Regel content describing the layer discipline rules.",
        agent="System", priority="medium",
    )
    save_soul_fact_smart(
        "layer_disziplin_blacklist", "Blacklist of forbidden patterns for the layer discipline.",
        agent="System", priority="medium",
    )
    keys = sorted(_all_soul_keys())
    assert keys == ["layer_disziplin_blacklist", "layer_disziplin_regel"]


# ── 4. Value-similarity dedup (Jaccard ≥ 0.6) ─────────────────────────────
def test_value_similarity_dedup(isolated_db):
    """Two facts with Jaccard similarity ≥ 0.6 must merge into one slot."""
    # First fact — moderate value.
    save_soul_fact_smart(
        "bafin_verb_blacklist",
        "BaFin verbietet CTA Verben wie 'klick hier' und 'jetzt kaufen'.",
        agent="SoulAG",
        priority="medium",
    )
    # Second fact — different key but high token overlap.
    save_soul_fact_smart(
        "bafin_verbotene_woerter",
        "BaFin verbietet CTA Verben wie 'sofort kaufen' und 'jetzt sichern'.",
        agent="SoulAG",
        priority="medium",
    )
    keys = _all_soul_keys()
    assert len(keys) == 1, f"Expected merge, got keys: {keys}"
    # The remaining slot keeps the longer value.
    row = _get_soul_row(keys[0])
    assert len(row["value"]) >= 60


def test_jaccard_helper_computes_correctly():
    """Direct test of the Jaccard helper to lock the semantics."""
    a = {"bafin", "verbietet", "cta", "verben", "wie", "und", "jetzt"}
    b = {"bafin", "verbietet", "cta", "verben", "und", "kaufen"}
    # Intersection: {bafin, verbietet, cta, verben, und} = 5
    # Union: {bafin, verbietet, cta, verben, wie, und, jetzt, kaufen} = 8
    # Jaccard = 5/8 = 0.625
    assert _jaccard(a, b) == pytest.approx(0.625)


# ── 5. No similarity → INSERT normal ───────────────────────────────────────
def test_no_similarity_inserts_separate(isolated_db):
    """Two completely different facts must NOT be merged."""
    save_soul_fact_smart(
        "apples_facts",
        "Apples are red fruits growing on trees in temperate climates.",
        agent="SoulAG",
        priority="medium",
    )
    save_soul_fact_smart(
        "cars_facts",
        "Cars drive on roads using gasoline engines for transportation.",
        agent="SoulAG",
        priority="medium",
    )
    assert _count_soul_facts() == 2
    keys = sorted(_all_soul_keys())
    assert keys == ["apples_facts", "cars_facts"]


def test_similarity_just_below_threshold_inserts_separate(isolated_db):
    """Two facts with Jaccard < 0.6 (but not zero) must also stay separate."""
    save_soul_fact_smart(
        "domain_marketing",
        "Marketing team owns the landing page copy and CTA design.",
        agent="SoulAG",
        priority="medium",
    )
    save_soul_fact_smart(
        "domain_engineering",
        "Engineering team owns the API contracts and the deployment pipeline.",
        agent="SoulAG",
        priority="medium",
    )
    # Tokens share only "team", "owns", "the" — should be well below 0.6.
    assert _count_soul_facts() == 2


# ── 6. Cleanup hook triggered on overflow ──────────────────────────────────
def test_cleanup_triggered_on_overflow(isolated_db, monkeypatch):
    """When count exceeds MAX_SOUL_FACTS * 1.2, _periodic_cleanup must be called."""
    from gnom_hub.core.constants import MAX_SOUL_FACTS

    cleanup_calls = []

    def fake_cleanup():
        cleanup_calls.append(True)

    # Patch _periodic_cleanup on the soul module (lazy import in save_soul_fact_smart).
    import gnom_hub.soul.soul
    monkeypatch.setattr(gnom_hub.soul.soul, "_periodic_cleanup", fake_cleanup)

    threshold = int(MAX_SOUL_FACTS * 1.2)  # 120
    # Insert threshold + 5 facts with fully-disjoint token sets so dedup never
    # collapses multiple inserts into one slot.
    n_inserts = threshold + 5
    for i in range(n_inserts):
        save_soul_fact_smart(
            f"unique_fact_{i:04d}",
            f"alpha{i} bravo{i} charlie{i} delta{i} echo{i} foxtrot{i}",
            agent="System",
            priority="low",
        )

    assert len(cleanup_calls) >= 1, (
        f"Expected _periodic_cleanup to be called when count>{threshold}, "
        f"got {len(cleanup_calls)} calls"
    )


def test_cleanup_not_triggered_under_threshold(isolated_db, monkeypatch):
    """Cleanup must NOT fire when count stays under MAX_SOUL_FACTS * 1.2."""
    cleanup_calls = []

    def fake_cleanup():
        cleanup_calls.append(True)

    import gnom_hub.soul.soul
    monkeypatch.setattr(gnom_hub.soul.soul, "_periodic_cleanup", fake_cleanup)

    # 50 facts is well under 120.
    for i in range(50):
        save_soul_fact_smart(
            f"under_threshold_fact_{i:04d}",
            f"alpha{i} bravo{i} charlie{i} delta{i} echo{i} foxtrot{i}",
            agent="System",
            priority="low",
        )

    assert cleanup_calls == []


# ── 7. Wrapper preserves permission check ──────────────────────────────────
def test_wrapper_blocks_unauthorized_agent_for_restricted_key(isolated_db):
    """The save_soul_fact wrapper must still raise PermissionError for restricted keys."""
    with pytest.raises(PermissionError):
        save_soul_fact(
            "active_preset", "Web Development",
            agent="CoderAG", priority="medium",
        )
    assert _count_soul_facts() == 0


def test_wrapper_allows_authorized_agent(isolated_db):
    """Authorized agents must be able to write restricted keys (with dedup applied)."""
    save_soul_fact(
        "active_preset", "Web Development",
        agent="SoulAG", priority="medium",
    )
    assert _count_soul_facts() == 1
    assert _get_soul_row("active_preset")["value"] == "Web Development"


# ── Direct helper tests (sanity) ───────────────────────────────────────────
def test_normalize_key_helper():
    assert _normalize_key("Layer_Disziplin-Regel") == "layer_disziplin_regel"
    assert _normalize_key("Foo Bar Baz") == "foo_bar_baz"
    assert _normalize_key("  __multi___under___  ") == "multi_under"
    assert _normalize_key("") == ""
    assert _normalize_key("CamelCase") == "camelcase"


def test_strip_version_suffix_helper():
    assert _strip_version_suffix("layer_disziplin_v2") == "layer_disziplin"
    assert _strip_version_suffix("rule_set_version3") == "rule_set"
    assert _strip_version_suffix("rule_set_p1") == "rule_set"
    assert _strip_version_suffix("rule_set_part1") == "rule_set"
    assert _strip_version_suffix("plain_key") == "plain_key"
    assert _strip_version_suffix("blacklist_words") == "blacklist_words"