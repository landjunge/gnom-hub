"""LLM free-model probe: repair dead primaries + status snapshot."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from gnom_hub.api.endpoints.llm_models import (
    _repair_dead_agent_primaries,
    _summarize_agent_llms,
    get_active_llm_status,
)


def test_summarize_agent_llms_groups():
    s = _summarize_agent_llms(
        {
            "generalag": {"provider": "openrouter", "model": "openrouter/free"},
            "coderag": {"provider": "openrouter", "model": "openrouter/free"},
            "writerag": {"provider": "openrouter", "model": "tencent/hy3:free"},
        }
    )
    assert "openrouter/free ×2" in s
    assert "tencent/hy3:free" in s


def test_repair_dead_agent_primaries():
    repo = MagicMock()
    repo.get_value.return_value = {
        "generalag": {
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct:free",
        },
        "coderag": {"provider": "openrouter", "model": "openrouter/free"},
        "writerag": {"provider": "openai", "model": "gpt-4o-mini"},
    }
    repaired = _repair_dead_agent_primaries(repo, ["openrouter/free", "tencent/hy3:free"])
    assert "generalag" in repaired
    assert "coderag" not in repaired
    assert "writerag" not in repaired
    saved = repo.set_value.call_args[0]
    assert saved[0] == "llm_agents"
    assert saved[1]["generalag"]["model"] == "openrouter/free"
    assert saved[1]["coderag"]["model"] == "openrouter/free"
    assert saved[1]["writerag"]["provider"] == "openai"


def test_get_active_llm_status_shape():
    fake_agents = {
        "generalag": {"provider": "openrouter", "model": "openrouter/free"},
    }
    with patch("gnom_hub.api.endpoints.llm_models.SQLiteStateRepository") as MockRepo:
        inst = MockRepo.return_value
        inst.get_value.side_effect = lambda k, default=None: {
            "llm_agents": fake_agents,
            "llm_probe_status": {"ts": 1, "working": ["openrouter/free"]},
            "openrouter_working_models": ["openrouter/free"],
        }.get(k, default)
        st = get_active_llm_status()
    assert st["summary"]
    assert "generalag" in st["agents"]
    assert st["agents"]["generalag"]["model"] == "openrouter/free"
