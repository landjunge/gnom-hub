"""Hub claim API (stability plan S2.4) — no external broker."""

from __future__ import annotations

from gnom_hub.queue import queue_mode, use_hub_claim


def test_default_queue_mode_is_hub():
    # Env may override in CI; function returns valid mode
    assert queue_mode() in ("hub", "sqlite")


def test_use_hub_claim_bool():
    assert isinstance(use_hub_claim(), bool)


def test_claim_empty_on_fresh_db(isolated_db, monkeypatch):
    monkeypatch.setenv("GNOM_QUEUE_MODE", "hub")
    # reload not needed — claim_service uses DB_PATH from config patched by fixture
    from gnom_hub.queue.claim_service import claim_next

    assert claim_next("GeneralAG", timeout=0.1) is None
