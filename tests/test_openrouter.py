from unittest.mock import MagicMock, patch

import pytest

from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.llm.key_verifier import clean_key
from gnom_hub.infrastructure.router.router_stage import SmartRouter


def test_openrouter_key_cleaner():
    """Verify clean_key properly cleans key strings including exports and comments."""
    assert clean_key("sk-or-v1-abc") == "sk-or-v1-abc"
    assert clean_key("export OPENROUTER_API_KEY=sk-or-v1-abc") == "sk-or-v1-abc"
    assert clean_key("OPENROUTER_KEY_FREE_1=sk-or-v1-abc # My key") == "sk-or-v1-abc"
    assert clean_key("OPENROUTER_KEY_FREE_1=sk-or-v1-abc // comment") == "sk-or-v1-abc"
    assert clean_key("- sk-or-v1-abc") == "sk-or-v1-abc"


@pytest.mark.asyncio
async def test_openrouter_model_fetching_and_caching(isolated_db):
    """Verify check_and_update_models fetches and caches free models successfully."""
    from gnom_hub.api.endpoints.llm_models import check_and_update_models
    
    repo = SQLiteStateRepository()
    # Initially none cached
    assert repo.get_value("openrouter_working_models") is None

    mock_models_response = {
        "data": [
            {"id": "meta-llama/llama-3.3-70b-instruct:free"},
            {"id": "qwen/qwen3-coder:free"},
            {"id": "openai/gpt-4o"},  # Not a free model, should be filtered out
        ]
    }

    # Mock the httpx client response
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data

    async def mock_get(url, *args, **kwargs):
        if "models" in url:
            return MockResponse(mock_models_response, 200)
        return MockResponse({}, 404)

    async def mock_post(url, *args, **kwargs):
        return MockResponse({"choices": [{"message": {"content": "OK"}}]}, 200)

    with patch("httpx.AsyncClient.get", side_effect=mock_get), \
         patch("httpx.AsyncClient.post", side_effect=mock_post):
        # Force a valid key in DB to pass verification
        repo.set_value("llm_keys", {
            "k_1": {
                "id": "k_1",
                "key": "sk-or-v1-test",
                "provider": "openrouter",
                "valid": True,
                "label": "OPENROUTER_API_KEY"
            }
        })
        
        working = await check_and_update_models()
        assert "meta-llama/llama-3.3-70b-instruct:free" in working
        assert "qwen/qwen3-coder:free" in working
        assert "openai/gpt-4o" not in working

        # Verify it is stored in DB
        db_working = repo.get_value("openrouter_working_models")
        assert db_working == working


def test_openrouter_routing_fallback(isolated_db):
    """Verify SmartRouter resolves to updated models under fallback conditions."""
    repo = SQLiteStateRepository()
    
    # 1. Fallback to Config.OPENROUTER_FREE_MODELS when openrouter_working_models is empty
    repo.set_value("openrouter_working_models", None)
    kdb = {
        "k_1": {
            "id": "k_1",
            "key": "sk-or-v1-test",
            "provider": "openrouter",
            "valid": True,
            "label": "OPENROUTER_API_KEY"
        }
    }
    
    pvd, mdl = SmartRouter.get_best_specific_assignment("coder", kdb)
    assert pvd == "openrouter"
    # Should use first matching coder model in Config.OPENROUTER_FREE_MODELS
    assert "qwen" in mdl.lower() or "llama-3.3" in mdl.lower() or "instruct" in mdl.lower()

    # 2. SmartRouter resolution with custom cached models
    repo.set_value("openrouter_working_models", ["qwen/qwen3-coder:free"])
    pvd, mdl = SmartRouter.get_best_specific_assignment("coder", kdb)
    assert pvd == "openrouter"
    assert mdl == "qwen/qwen3-coder:free"


@pytest.mark.asyncio
async def test_router_call_retry_on_429():
    """Verify that _call successfully retries on 429 and eventually succeeds or fails."""
    from gnom_hub.infrastructure.router.router_call import _call
    
    mock_responses = [
        MagicMock(status_code=429),
        MagicMock(status_code=200)
    ]
    mock_responses[1].json.return_value = {
        "choices": [{"message": {"content": "Hello after retry"}}]
    }

    with patch("requests.post", side_effect=mock_responses) as mock_post, \
         patch("time.sleep") as mock_sleep:
        ans = _call("openrouter", "meta-llama/llama-3.3-70b-instruct:free", "sk-or-v1-test", [{"role": "user", "content": "hi"}], "Test")
        assert ans == "Hello after retry"
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1.5)


def test_openrouter_candidate_fallbacks():
    """Verify that _resolve appends other working OpenRouter models when provider is openrouter."""
    from gnom_hub.infrastructure.router.router import _resolve
    
    # Mock working models in DB
    kdb = {}
    with patch("gnom_hub.db.state_repo.SQLiteStateRepository.get_value", return_value=["google/gemma-4-31b-it:free", "liquid/lfm-2.5-1.2b-instruct:free"]):
        # Case A: Requested model is not in working models -> should bypass and start with best fallback
        cands = _resolve("openrouter", "qwen/qwen3-coder:free", kdb, "CoderAG")
        assert cands[0] == ("openrouter", "google/gemma-4-31b-it:free")
        assert ("openrouter", "liquid/lfm-2.5-1.2b-instruct:free") in cands
        assert ("openrouter", "qwen/qwen3-coder:free") not in cands
        assert cands[-1] == ("lokal", "llama3")

        # Case B: Requested model is in working models -> should start with it
        cands_ok = _resolve("openrouter", "google/gemma-4-31b-it:free", kdb, "CoderAG")
        assert cands_ok[0] == ("openrouter", "google/gemma-4-31b-it:free")
        assert ("openrouter", "liquid/lfm-2.5-1.2b-instruct:free") in cands_ok
        assert cands_ok[-1] == ("lokal", "llama3")

