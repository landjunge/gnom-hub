"""Tests for the extended provider registry + router fixes.

Covers:
- Provider registry shape, capability filtering, auto-detection.
- SmartRouter.get_best_model across all stages and edge cases.
- SmartRouter.get_best_openrouter_model role matching (no dead keywords).
- router_call._try_keys key rotation on 429 / 401 / 200.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
import requests


# ─── Provider Registry: shape & invariants ────────────────────────────────

class TestProviderRegistryShape:
    """Every provider in the registry must follow the documented schema."""

    REQUIRED_FIELDS = {
        "name", "display_name", "api_key_prefixes",
        "key_validation_endpoint", "model_discovery_endpoint",
        "capabilities", "free_tier_supported", "notes",
    }

    def test_registry_is_non_empty(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        assert len(PROVIDERS) >= 30

    def test_every_entry_has_required_fields(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        for name, info in PROVIDERS.items():
            missing = self.REQUIRED_FIELDS - set(info.keys())
            assert not missing, f"{name} missing fields: {missing}"

    def test_every_entry_field_types(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        for name, info in PROVIDERS.items():
            assert isinstance(info["name"], str), name
            assert isinstance(info["display_name"], str), name
            assert isinstance(info["api_key_prefixes"], list), name
            assert isinstance(info["key_validation_endpoint"], str), name
            assert isinstance(info["model_discovery_endpoint"], str), name
            assert isinstance(info["capabilities"], list), name
            assert isinstance(info["free_tier_supported"], bool), name
            assert isinstance(info["notes"], str), name

    def test_provider_names_are_snake_case(self):
        import re
        from gnom_hub.core.provider_registry import PROVIDERS
        pat = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
        for name in PROVIDERS:
            assert pat.match(name), f"non-snake_case provider name: {name}"

    def test_provider_names_are_unique(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        assert len(PROVIDERS) == len(set(PROVIDERS.keys()))

    def test_capabilities_are_known_strings(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        valid = {"chat", "web_search", "tts", "image", "embedding", "audio",
                 "vision", "tools", "code", "web", "video", "music"}
        for name, info in PROVIDERS.items():
            for cap in info["capabilities"]:
                assert cap in valid, f"{name} has unknown capability {cap!r}"


# ─── Provider Registry: per-provider registration ───────────────────────────

class TestSpecificProviders:
    """Spot-check that the major new providers are wired correctly."""

    def _check_prefix(self, name, prefix):
        from gnom_hub.core.provider_registry import PROVIDERS
        assert name in PROVIDERS, f"missing provider {name}"
        prefixes = PROVIDERS[name]["api_key_prefixes"]
        if prefix:
            assert prefix in prefixes, (
                f"{name} should declare prefix {prefix!r}, got {prefixes}"
            )

    @pytest.mark.parametrize("name,prefix", [
        ("openai", "sk-"),
        ("anthropic", "sk-ant-"),
        ("gemini", "AIza"),
        ("deepseek", "sk-"),
        ("openrouter", "sk-or-"),
        ("groq", "gsk_"),
        ("cohere", "co-"),
        ("together", "together-"),
        ("fireworks", "fw-"),
        ("perplexity", "pplx-"),
        ("xai", "xai-"),
        ("replicate", "r8_"),
        ("huggingface", "hf_"),
    ])
    def test_major_llm_prefixes(self, name, prefix):
        self._check_prefix(name, prefix)

    @pytest.mark.parametrize("name,prefix", [
        ("ollama", ""),       # local, no key needed
        ("llamacpp", ""),
        ("opencode", "sk-ec"),
        ("ai21", "ai21-"),
        ("mistral-codestral", "sk-"),
        ("deepseek-coder", "sk-"),
        ("google-ai-studio", "AIza"),
        ("kimi", "sk-"),
    ])
    def test_extended_llm_prefixes(self, name, prefix):
        self._check_prefix(name, prefix)

    @pytest.mark.parametrize("name,prefix", [
        ("elevenlabs", "sk_"),
        ("brave", "BSA"),
        ("tavily", "tvly-"),
        ("serper", "serper-"),
        ("bing-search", ""),
        ("duckduckgo", ""),
        ("you-com", "you-"),
        ("kagi", "kagi-"),
        ("exa", "exa-"),
        ("openai-tts", "sk-"),
        ("edge-tts", ""),
        ("google-tts", "AIza"),
        ("azure-tts", ""),
        ("playht", "play-"),
        ("lmnt", "lmnt-"),
        ("cartesia", "cartesia-"),
    ])
    def test_search_and_tts_prefixes(self, name, prefix):
        self._check_prefix(name, prefix)

    def test_provider_counts(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        names = set(PROVIDERS.keys())
        assert "openai" in names
        assert "anthropic" in names
        assert "gemini" in names
        assert "deepseek" in names
        assert "mistral" in names
        assert "ollama" in names
        assert "elevenlabs" in names
        assert "brave" in names
        assert "tavily" in names
        assert "github" in names
        assert "xai" in names
        assert "groq" in names
        assert "cohere" in names
        assert "exa" in names
        assert "edge-tts" in names
        assert "cartesia" in names


# ─── Provider Registry: URL validity ───────────────────────────────────────

class TestProviderUrls:
    """All public HTTP endpoints must be well-formed URLs."""

    def test_all_key_validation_urls_are_valid(self):
        import re
        from gnom_hub.core.provider_registry import PROVIDERS
        # Matches http(s)://host with optional path
        url_re = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
        for name, info in PROVIDERS.items():
            url = info["key_validation_endpoint"]
            if not url:
                continue  # Local/no-key providers may have empty URL
            assert url_re.match(url), f"{name}: malformed URL {url!r}"

    def test_all_model_discovery_urls_are_valid(self):
        import re
        from gnom_hub.core.provider_registry import PROVIDERS
        url_re = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
        for name, info in PROVIDERS.items():
            url = info["model_discovery_endpoint"]
            if not url:
                continue
            assert url_re.match(url), f"{name}: malformed URL {url!r}"

    def test_every_url_has_a_host(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        for name, info in PROVIDERS.items():
            for key in ("key_validation_endpoint", "model_discovery_endpoint"):
                url = info[key]
                if not url:
                    continue
                scheme, _, rest = url.partition("://")
                assert scheme in ("http", "https"), f"{name}: bad scheme {url!r}"
                host = rest.split("/", 1)[0]
                assert host, f"{name}: empty host in {url!r}"


# ─── Provider Registry: capability filtering ──────────────────────────────

class TestCapabilityFiltering:

    def test_chat_capability_includes_major_providers(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        chat = {p["name"] for p in get_providers_by_capability("chat")}
        for must in {"openai", "anthropic", "gemini", "deepseek", "groq", "ollama"}:
            assert must in chat

    def test_web_search_capability(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        web = {p["name"] for p in get_providers_by_capability("web_search")}
        assert "brave" in web
        assert "tavily" in web
        assert "exa" in web
        assert "kagi" in web
        assert "duckduckgo" in web

    def test_tts_capability(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        tts = {p["name"] for p in get_providers_by_capability("tts")}
        assert "elevenlabs" in tts
        assert "openai-tts" in tts
        assert "edge-tts" in tts
        assert "cartesia" in tts

    def test_image_capability(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        img = {p["name"] for p in get_providers_by_capability("image")}
        assert "openai" in img
        assert "replicate" in img

    def test_embedding_capability(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        emb = {p["name"] for p in get_providers_by_capability("embedding")}
        assert "openai" in emb
        assert "cohere" in emb

    def test_unknown_capability_returns_empty(self):
        from gnom_hub.core.provider_registry import get_providers_by_capability
        assert get_providers_by_capability("not-a-real-capability") == []

    def test_free_tier_providers_include_known_free(self):
        from gnom_hub.core.provider_registry import PROVIDERS
        free = {n for n, p in PROVIDERS.items() if p["free_tier_supported"]}
        # Local providers should always be free
        assert "ollama" in free
        assert "llamacpp" in free
        # Known generous free tiers
        assert "groq" in free
        assert "gemini" in free
        assert "tavily" in free
        assert "edge-tts" in free

    def test_get_provider_returns_copy(self):
        from gnom_hub.core.provider_registry import get_provider
        p = get_provider("openai")
        assert p is not None
        p["display_name"] = "MUTATED"
        from gnom_hub.core.provider_registry import PROVIDERS
        # Mutating the returned dict should not affect the registry
        assert PROVIDERS["openai"]["display_name"] != "MUTATED"


# ─── Provider Registry: auto-detection ─────────────────────────────────────

class TestAutoDetection:

    def test_sk_or_detected_as_openrouter(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("sk-or-v1-abc123") == "openrouter"
        assert detect_provider_from_key("sk-or-abc") == "openrouter"

    def test_sk_ant_detected_as_anthropic(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("sk-ant-api03-xyz") == "anthropic"

    def test_hf_detected_as_huggingface(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("hf_abc123") == "huggingface"

    def test_gsk_detected_as_groq(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("gsk_xyz") == "groq"

    def test_xai_detected(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("xai-abc") == "xai"

    def test_minimax_prefix_detected(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("sk-cp-xyz") == "minimax"

    def test_r8_detected_as_replicate(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("r8_xyz") == "replicate"

    def test_pplx_detected_as_perplexity(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("pplx-xyz") == "perplexity"

    def test_AIza_detected_as_gemini(self):
        from gnom_hub.core.provider_registry import detect_provider_from_key
        assert detect_provider_from_key("AIzaSy1234") == "gemini"

    def test_label_detection_openai(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("OPENAI_API_KEY") == "openai"

    def test_label_detection_anthropic(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("ANTHROPIC_API_KEY") == "anthropic"

    def test_label_detection_brave(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("BRAVE_SEARCH_API_KEY") == "brave"

    def test_label_detection_github(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("GITHUB_TOKEN") == "github"

    def test_label_detection_minimax(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("MINIMAX_API_KEY") == "minimax"

    def test_label_detection_unknown(self):
        from gnom_hub.core.provider_registry import detect_provider_from_label
        assert detect_provider_from_label("MY_RANDOM_VAR") is None


# ─── SmartRouter.get_best_model ─────────────────────────────────────────────

class TestGetBestModel:
    """Cover all 4 stages + edge cases (empty, full, no match)."""

    def test_stage_1_ollama_fallback_when_empty(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        # No models available at all — must still return a sensible default
        result = SmartRouter.get_best_model("stage_1", [])
        assert result == "qwen2.5-coder:7b"

    def test_stage_4_picks_claude_when_available(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["claude-3-5-sonnet-latest", "gpt-4o-mini"]
        assert SmartRouter.get_best_model("stage_4", avail) == "claude-3-5-sonnet-latest"

    def test_stage_4_picks_gpt4o_when_no_claude(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["gpt-4o", "gemini-1.5-flash"]
        assert SmartRouter.get_best_model("stage_4", avail) == "gpt-4o"

    def test_stage_3_picks_deepseek_when_available(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["deepseek-chat", "gpt-4o-mini"]
        assert SmartRouter.get_best_model("stage_3", avail) == "deepseek-chat"

    def test_stage_2_picks_qwen_coder_when_available(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-coder:free",
            "google/gemma-3-27b-it:free",
        ]
        assert SmartRouter.get_best_model("stage_2", avail) == "qwen/qwen3-coder:free"

    def test_stage_2_falls_back_to_first_available(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["some/random:free"]
        assert SmartRouter.get_best_model("stage_2", avail) == "some/random:free"

    def test_unknown_stage_uses_ollama_fallback(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        # An invalid stage key should default to the conservative tier.
        result = SmartRouter.get_best_model("stage_99", [])
        assert result == "qwen2.5-coder:7b"

    def test_substring_matching_handles_versions(self):
        """`gpt-4o` should match `gpt-4o-2024-08-06` via substring."""
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["gpt-4o-2024-08-06", "gpt-3.5-turbo"]
        # `gpt-4o` is in the preferred list, substring match wins.
        assert SmartRouter.get_best_model("stage_4", avail) == "gpt-4o-2024-08-06"

    def test_stage_3_prefers_4o_mini_when_no_deepseek(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        avail = ["gpt-4o-mini", "mistral-large-latest"]
        assert SmartRouter.get_best_model("stage_3", avail) == "gpt-4o-mini"

    def test_get_best_openrouter_model_no_dead_keywords(self):
        """Regression test: poolside/laguna/nemotron must not be required matches."""
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        # A working-model list that does NOT contain any of the old dead
        # names should still yield a sensible model for every role.
        working = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-coder:free",
            "arcee-ai/trinity-large-thinking:free",
            "google/gemma-3-27b-it:free",
        ]
        with patch("gnom_hub.db.state_repo.SQLiteStateRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_value.return_value = working
            assert SmartRouter.get_best_openrouter_model("coder") == "qwen/qwen3-coder:free"
            assert SmartRouter.get_best_openrouter_model("researcher") == "arcee-ai/trinity-large-thinking:free"
            # writer/editor no longer requires poolside
            assert SmartRouter.get_best_openrouter_model("writer") == "meta-llama/llama-3.3-70b-instruct:free"
            assert SmartRouter.get_best_openrouter_model("editor") == "meta-llama/llama-3.3-70b-instruct:free"
            assert SmartRouter.get_best_openrouter_model("normal") == "meta-llama/llama-3.3-70b-instruct:free"

    def test_get_best_openrouter_model_unknown_role_falls_back(self):
        from gnom_hub.infrastructure.router.router_stage import SmartRouter
        with patch("gnom_hub.db.state_repo.SQLiteStateRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_value.return_value = ["meta-llama/llama-3.3-70b-instruct:free"]
            assert SmartRouter.get_best_openrouter_model("spaceship-pilot") == "meta-llama/llama-3.3-70b-instruct:free"


# ─── router_call._try_keys: key rotation on HTTP errors ─────────────────────

class TestTryKeys:
    """Verify _try_keys rotates to the next key when a 429 (or 401) comes back."""

    def _mock_response(self, status_code, payload=None):
        r = MagicMock()
        r.status_code = status_code
        r.text = "{}"
        r.json.return_value = payload or {}
        return r

    def test_returns_first_successful_answer(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys, _call

        with patch("gnom_hub.infrastructure.router.router_call._call") as mc, \
             patch("gnom_hub.infrastructure.router.router_call.get_keys") as gk:
            gk.return_value = ["k1"]
            mc.side_effect = ["first answer"]
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans == "first answer"
        assert mc.call_count == 1

    def test_rotates_on_429(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys

        with patch("gnom_hub.infrastructure.router.router_call._call") as mc, \
             patch("gnom_hub.infrastructure.router.router_call.get_keys") as gk:
            gk.return_value = ["key1", "key2", "key3"]
            # First key: 429 → RetryableCallError. Second key: success.
            from gnom_hub.infrastructure.router.router_call import _RetryableCallError
            mc.side_effect = [
                _RetryableCallError(429, "openai"),
                "second key answer",
            ]
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans == "second key answer"
        assert mc.call_count == 2

    def test_rotates_on_401(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call._call") as mc, \
             patch("gnom_hub.infrastructure.router.router_call.get_keys") as gk:
            gk.return_value = ["bad-key", "good-key"]
            mc.side_effect = [
                _RetryableCallError(401, "openai"),
                "answer from second key",
            ]
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans == "answer from second key"

    def test_rotates_on_500(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call._call") as mc, \
             patch("gnom_hub.infrastructure.router.router_call.get_keys") as gk:
            gk.return_value = ["k1", "k2", "k3"]
            mc.side_effect = [
                _RetryableCallError(500, "openai"),
                _RetryableCallError(502, "openai"),
                "ok",
            ]
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans == "ok"
        assert mc.call_count == 3

    def test_returns_none_when_all_keys_exhausted(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call._call") as mc, \
             patch("gnom_hub.infrastructure.router.router_call.get_keys") as gk:
            gk.return_value = ["k1", "k2"]
            mc.side_effect = [
                _RetryableCallError(429, "openai"),
                _RetryableCallError(429, "openai"),
            ]
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans is None

    def test_no_keys_returns_none(self):
        from gnom_hub.infrastructure.router.router_call import _try_keys
        with patch("gnom_hub.infrastructure.router.router_call.get_keys", return_value=[]):
            ans = _try_keys("openai", "gpt-4o", {}, [{"role": "user", "content": "hi"}], "agent")
        assert ans is None


# ─── router_call._call: integration with mocked requests ────────────────────

class TestCallHTTPBehaviour:
    """Make sure _call raises _RetryableCallError for retryable HTTP statuses."""

    def test_429_raises_retryable_error(self):
        from gnom_hub.infrastructure.router.router_call import _call, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call.requests.post") as mp:
            mp.return_value = self._mock_response(429)
            with pytest.raises(_RetryableCallError):
                _call("openai", "gpt-4o", "key", [{"role": "user", "content": "hi"}], "agent")

    def test_500_raises_retryable_error(self):
        from gnom_hub.infrastructure.router.router_call import _call, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call.requests.post") as mp:
            mp.return_value = self._mock_response(500)
            with pytest.raises(_RetryableCallError):
                _call("openai", "gpt-4o", "key", [{"role": "user", "content": "hi"}], "agent")

    def test_400_raises_retryable_error(self):
        """Even non-transient errors should rotate keys, not stall."""
        from gnom_hub.infrastructure.router.router_call import _call, _RetryableCallError

        with patch("gnom_hub.infrastructure.router.router_call.requests.post") as mp:
            mp.return_value = self._mock_response(400)
            with pytest.raises(_RetryableCallError):
                _call("openai", "gpt-4o", "key", [{"role": "user", "content": "hi"}], "agent")

    def test_200_returns_content(self):
        from gnom_hub.infrastructure.router.router_call import _call

        payload = {"choices": [{"message": {"content": "Hello, world!"}}]}
        with patch("gnom_hub.infrastructure.router.router_call.requests.post") as mp, \
             patch("gnom_hub.infrastructure.router.router_call.track_tokens"):
            mp.return_value = self._mock_response(200, payload)
            ans = _call("openai", "gpt-4o", "key", [{"role": "user", "content": "hi"}], "agent")
        assert ans == "Hello, world!"

    def test_200_includes_reasoning_block(self):
        from gnom_hub.infrastructure.router.router_call import _call

        payload = {
            "choices": [
                {"message": {
                    "content": "Final.",
                    "reasoning_content": "Because…",
                }}
            ]
        }
        with patch("gnom_hub.infrastructure.router.router_call.requests.post") as mp, \
             patch("gnom_hub.infrastructure.router.router_call.track_tokens"):
            mp.return_value = self._mock_response(200, payload)
            ans = _call("deepseek", "deepseek-reasoner", "key",
                        [{"role": "user", "content": "hi"}], "agent")
        assert "Final." in ans
        assert "Because" in ans

    @staticmethod
    def _mock_response(status_code, payload=None):
        r = MagicMock()
        r.status_code = status_code
        r.text = "{}"
        r.json.return_value = payload or {}
        return r
