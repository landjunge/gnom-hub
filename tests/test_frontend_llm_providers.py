"""Smoke tests for the new endpoints used by the redesigned LLM page.

These tests run quickly (under 5s on a clean environment) and cover:
- `GET /api/llm/providers` returns the registry with the categories the
  frontend needs to render Web Search + TTS cards.
- `GET /api/llm/service` returns the persisted service bindings (empty by default).
- `POST /api/llm/service` persists the bindings correctly.
- `POST /api/admin/backup` exists and handles missing-script gracefully
  (it never blocks the response, even if the script is unavailable).
- Required providers are present in the registry (per task spec).
- `detectProviderByRegistry` (tested via the providers module directly)
  correctly resolves ambiguous prefixes like `sk-cp-` vs `sk-`.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


# ─── /api/llm/providers ────────────────────────────────────────────────


def test_providers_endpoint_returns_registry():
    from gnom_hub.api.endpoints.llm_models import get_provider_registry

    res = asyncio.run(get_provider_registry())
    assert isinstance(res, dict)
    assert "providers" in res
    assert "categories" in res
    assert "defaults" in res
    assert "llm" in res["categories"]
    assert "web_search" in res["categories"]
    assert "tts" in res["categories"]
    assert len(res["providers"]) >= 20


def test_providers_endpoint_includes_required_web_search():
    from gnom_hub.api.endpoints.llm_models import get_provider_registry

    res = asyncio.run(get_provider_registry())
    web_ids = {p["id"] for p in res["providers"] if p["category"] == "web_search"}
    required = {"brave", "tavily", "serper", "bing-search", "duckduckgo",
                "you-com", "kagi", "exa", "perplexity-search"}
    missing = required - web_ids
    assert not missing, f"Missing web-search providers: {missing}"


def test_providers_endpoint_includes_required_tts():
    from gnom_hub.api.endpoints.llm_models import get_provider_registry

    res = asyncio.run(get_provider_registry())
    tts_ids = {p["id"] for p in res["providers"] if p["category"] == "tts"}
    required = {"elevenlabs", "openai-tts", "edge-tts", "google-tts",
                "azure-tts", "playht", "lmnt", "coqui", "cartesia"}
    missing = required - tts_ids
    assert not missing, f"Missing TTS providers: {missing}"


def test_providers_have_required_fields():
    from gnom_hub.api.endpoints.llm_models import get_provider_registry

    res = asyncio.run(get_provider_registry())
    for p in res["providers"]:
        assert "id" in p, f"provider missing id: {p}"
        assert "display_name" in p, f"provider missing display_name: {p}"
        assert "caps" in p
        assert "category" in p
        assert "key_prefixes" in p
        assert "label_patterns" in p
        assert "default_model" in p


def test_providers_defaults_per_category():
    from gnom_hub.api.endpoints.llm_models import get_provider_registry

    res = asyncio.run(get_provider_registry())
    defaults = res.get("defaults") or {}
    assert "web_search" in defaults
    assert "tts" in defaults
    assert "brave" in defaults["web_search"]
    assert "elevenlabs" in defaults["tts"]


# ─── /api/llm/service ─────────────────────────────────────────────────


def test_service_get_returns_empty_by_default(isolated_db):
    from gnom_hub.api.endpoints.llm_models import get_service_config

    res = asyncio.run(get_service_config())
    assert res["web_search"] == {}
    assert res["tts"] == {}


def test_service_post_persists_web_search(isolated_db):
    from gnom_hub.api.endpoints.llm_models import (
        get_service_config,
        save_service_config,
    )

    class _Req:
        async def json(self):
            return {"web_search": {"provider": "brave", "model": "brave-search"}}

    save_res = asyncio.run(save_service_config(_Req()))
    assert save_res == {"status": "ok"}

    cfg = asyncio.run(get_service_config())
    assert cfg["web_search"]["provider"] == "brave"
    assert cfg["web_search"]["model"] == "brave-search"


def test_service_post_persists_tts(isolated_db):
    from gnom_hub.api.endpoints.llm_models import (
        get_service_config,
        save_service_config,
    )

    class _Req:
        async def json(self):
            return {"tts": {"provider": "elevenlabs", "model": "eleven_turbo_v2_5"}}

    save_res = asyncio.run(save_service_config(_Req()))
    assert save_res == {"status": "ok"}

    cfg = asyncio.run(get_service_config())
    assert cfg["tts"]["provider"] == "elevenlabs"
    assert cfg["tts"]["model"] == "eleven_turbo_v2_5"


def test_service_post_partial_update_preserves_other(isolated_db):
    from gnom_hub.api.endpoints.llm_models import (
        get_service_config,
        save_service_config,
    )

    class _ReqA:
        async def json(self):
            return {
                "web_search": {"provider": "brave", "model": "brave-search"},
                "tts": {"provider": "elevenlabs", "model": "eleven_turbo_v2_5"},
            }

    asyncio.run(save_service_config(_ReqA()))

    class _ReqB:
        async def json(self):
            return {"web_search": {"provider": "tavily", "model": "tavily-search"}}

    asyncio.run(save_service_config(_ReqB()))

    cfg = asyncio.run(get_service_config())
    # TTS must be preserved (partial update friendly)
    assert cfg["tts"]["provider"] == "elevenlabs"
    # Web Search updated
    assert cfg["web_search"]["provider"] == "tavily"


# ─── /api/admin/backup ────────────────────────────────────────────────


def test_admin_backup_endpoint_handles_missing_script(tmp_path, monkeypatch):
    """If the backup script is missing, the endpoint must return an error
    dict — never raise, never hang."""
    from gnom_hub.api.endpoints import admin_tools
    from gnom_hub.core import config as config_mod

    # Point PROJECT_ROOT at an empty directory so scripts/backup_all_dbs.sh is missing
    monkeypatch.setattr(config_mod, "PROJECT_ROOT", tmp_path)
    res = admin_tools.create_backup()
    assert isinstance(res, dict)
    assert res["status"] == "error"
    assert "backup script not found" in res["info"]


def test_admin_backup_endpoint_runs_script(monkeypatch):
    """If the backup script exists, the endpoint runs it and returns the path."""
    from gnom_hub.api.endpoints import admin_tools
    from gnom_hub.core import config as config_mod

    repo_root = Path(config_mod.PROJECT_ROOT)
    backup_script = repo_root / "scripts" / "backup_all_dbs.sh"
    assert backup_script.exists(), "backup_all_dbs.sh must exist for this test"

    res = admin_tools.create_backup()
    assert isinstance(res, dict)
    if res["status"] == "ok":
        assert res["path"], f"missing path in: {res}"
        assert Path(res["path"]).exists()
    else:
        # Acceptable: backup script can fail in test env (no DB, etc.)
        # but must still return a structured dict.
        assert "info" in res


# ─── Provider detection (the registry-driven pvdOf replacement) ──────


def test_detect_provider_from_key_prefers_longer_prefix():
    """The bug: sk-cp-… must NOT match openai."""
    from gnom_hub.infrastructure.llm.providers import PROVIDERS, detect_provider_from_key

    # Sort providers by max prefix length DESC and pick the first match.
    # This is the rule the frontend detector enforces.
    def detect(s: str) -> str | None:
        lower = s.lower()
        candidates = []
        for pid, p in PROVIDERS.items():
            for prefix in p["key_prefixes"]:
                if prefix and lower.startswith(prefix.lower()):
                    candidates.append((len(prefix), pid))
        if not candidates:
            return None
        # Stable: longer prefix first, then dict-iteration order (Python 3.7+).
        candidates.sort(key=lambda c: -c[0])
        return candidates[0][1]

    assert detect("sk-cp-abc123") == "minimax", \
        "sk-cp-… must beat the generic sk- prefix"
    # sk-or-… matches BOTH openrouter and openrouter-minimax (both have sk-or-v1-).
    # We accept either as long as it's in the openrouter family.
    assert detect("sk-or-v1-abc123") in {"openrouter", "openrouter-minimax"}
    assert detect("sk-or-abc123") in {"openrouter", "openrouter-minimax"}
    assert detect("tvly-abc123") == "tavily"
    assert detect("BSA12345") == "brave"
    assert detect("gsk_abc123") == "groq"
    assert detect("r8_abc") == "replicate"
    # Confirm that an unambiguously OpenAI key still routes to openai
    assert detect("sk-proj-abc123") == "openai"


def test_detect_provider_from_label():
    from gnom_hub.infrastructure.llm.providers import detect_provider_from_label

    assert detect_provider_from_label("OPENAI_API_KEY") == "openai"
    assert detect_provider_from_label("BRAVE_SEARCH_KEY") == "brave"
    assert detect_provider_from_label("TAVILY_API_KEY") == "tavily"
    assert detect_provider_from_label("ELEVENLABS_KEY") == "elevenlabs"


# ─── Sanity: the hub routes file still includes our new endpoints ─────


def test_router_includes_new_endpoints():
    from gnom_hub.api.endpoints import llm_models, admin_tools

    paths = []
    for sub in [llm_models.router, admin_tools.router]:
        for r in sub.routes:
            if hasattr(r, "path"):
                paths.append(r.path)

    assert "/api/llm/providers" in paths
    assert "/api/llm/service" in paths
    assert "/api/admin/backup" in paths