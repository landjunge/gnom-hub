from uuid import uuid4

import pytest

from gnom_hub.agents.entities import Agent
from gnom_hub.api.endpoints.llm_keys import auto_assign
from gnom_hub.core.utils.preset_service import handle_preset_change
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.state_repo import SQLiteStateRepository


@pytest.mark.anyio
async def test_auto_assign_saves_to_preset(isolated_db):
    # Setup some test agents in the DB
    agent_repo = SQLiteAgentRepository()
    await agent_repo.save(Agent(name="SoulAG", id=uuid4(), role="soul", status="online"))
    await agent_repo.save(Agent(name="CoderAG", id=uuid4(), role="coder", status="online"))
    await agent_repo.save(Agent(name="WatchdogAG", id=uuid4(), role="security", status="online"))

    # Set active preset to something specific
    state_repo = SQLiteStateRepository()
    state_repo.set_value("active_preset", "Custom Preset")
    state_repo.set_value("llm_keys", {
        "key1": {"provider": "openrouter", "key": "sk-or-test", "valid": True, "caps": ["text"]}
    })

    # Call auto_assign
    res = await auto_assign()
    assert res == {"status": "ok"}

    # Verify that maps were saved to llm_agents
    llm_agents = state_repo.get_value("llm_agents")
    assert llm_agents is not None
    assert "soulag" in llm_agents
    assert "coderag" in llm_agents
    assert "watchdogag" in llm_agents

    # Verify that maps were also saved to the preset specific key
    preset_agents = state_repo.get_value("llm_preset_Custom Preset")
    assert preset_agents == llm_agents


def test_preset_change_restores_all_agents(isolated_db):
    state_repo = SQLiteStateRepository()
    
    # Save a custom LLM assignment for a preset, configuring both worker agents and system/platform agents
    custom_config = {
        "soulag": {"provider": "openai", "model": "gpt-4o-mini"},
        "coderag": {"provider": "lokal", "model": "llama3"},
        "watchdogag": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}
    }
    state_repo.set_value("llm_preset_Special Dev", custom_config)
    
    # Now set active preset to "Special Dev"
    handle_preset_change("Special Dev")
    
    # Verify that the loaded llm_agents in the database contains all the custom assignments
    loaded_agents = state_repo.get_value("llm_agents")
    assert loaded_agents is not None
    assert loaded_agents["soulag"] == {"provider": "openai", "model": "gpt-4o-mini"}
    assert loaded_agents["coderag"] == {"provider": "lokal", "model": "llama3"}
    assert loaded_agents["watchdogag"] == {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}
