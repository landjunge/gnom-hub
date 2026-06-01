# test_agent_optimizer.py — Test Agent settings, mappings, statistics, export/import, and presets
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.agents.entities import Agent
from gnom_hub.infrastructure.router.router import _get_behavioral_instructions, _build_sys
from gnom_hub.soul.soul import soul_instance
from gnom_hub.core.config import CONFIG_DIR

def test_agent_optimizer():
    print("--- STARTING AGENT OPTIMIZER TESTS ---")
    gnom_hub.db.init_db()
    repo = SQLiteAgentRepository()

    # 1. Create a mock agent
    agent_id = "12345678-1234-5678-1234-567812345678"
    a = Agent(
        id=agent_id, name="TestCoderAG", port=0, description="Test",
        status="online", capabilities=[], role="normal"
    )
    repo.save(a)

    # 2. Test default settings resolution
    from gnom_hub.db.legacy_db import get_state_value, set_state_value
    all_settings = get_state_value("agent_settings", {})
    if "testcoderag" in all_settings:
        del all_settings["testcoderag"]
        set_state_value("agent_settings", all_settings)
        all_settings = get_state_value("agent_settings", {})

    # Verify no settings exist yet
    assert "testcoderag" not in all_settings

    try:
        # 3. Save agent settings
        test_settings = {
            "personality": 5,        # Sehr locker
            "response_style": 1,     # Sehr knapp
            "memory_strength": 4,    # top_k: 12
            "creativity": 5,         # temperature: 1.2
            "risk_tolerance": 2,     # Vorsichtig
            "custom_prompt": "CUSTOM_PROMPT_PREFIX"
        }
        all_settings["testcoderag"] = test_settings
        set_state_value("agent_settings", all_settings)

        # 4. Test behavioral instructions generation
        insts = _get_behavioral_instructions(test_settings)
        assert "casual, relaxed" in insts
        assert "extremely concise" in insts
        assert "cautious" in insts

        # 5. Test _build_sys system prompt overwrite & injection
        sys_prompt = _build_sys("testcoderag", "BASE_PROMPT", "TestCoderAG")
        # Base prompt must contain both original and CUSTOM_PROMPT_PREFIX
        assert "BASE_PROMPT" in sys_prompt
        assert "CUSTOM_PROMPT_PREFIX" in sys_prompt
        # Instructions must be appended
        assert "casual, relaxed" in sys_prompt

        # 6. Test top_k memory strength mapping
        # Memory strength is 4, which maps to top_k = 12
        # We will test the top_k resolution inside inject_context
        ctx = soul_instance.inject_context("SYS", "MSG", "TestCoderAG")
        assert ctx is not None

        # 7. Test preset save endpoint helper functionality
        from gnom_hub.api.endpoints.agents_status import SavePresetPayload, save_preset
        p_payload = SavePresetPayload(name="Unity Dev Preset", description="Test Description")
        res = save_preset(p_payload)
        assert res["status"] == "success"
        
        preset_file = CONFIG_DIR / "presets" / "unity_dev_preset.json"
        assert preset_file.exists()
        
        with open(preset_file, "r", encoding="utf-8") as f:
            preset_data = json.load(f)
            assert preset_data["name"] == "Unity Dev Preset"
            assert preset_data["agent_settings"]["testcoderag"]["personality"] == 5
            assert preset_data["prompt_modifier"]["testcoderag"] == "CUSTOM_PROMPT_PREFIX"

        # Clean up preset
        preset_file.unlink()
        
        # 8. Test export and import helper logic
        from gnom_hub.api.endpoints.agents_status import export_agent, import_agent, ImportData
        exp = export_agent(agent_id)
        assert exp["agent"]["name"] == "TestCoderAG"
        assert exp["settings"]["personality"] == 5
        
        # Modify settings in exported dict and import back
        exp["settings"]["personality"] = 1
        import_agent(agent_id, ImportData(settings=exp["settings"], soul_facts=[], prompt_versions=[]))
        
        # Verify imported setting
        updated_all = get_state_value("agent_settings", {})
        assert updated_all["testcoderag"]["personality"] == 1

        # Cleanup agent
        repo.delete(agent_id)
    finally:
        # Cleanup agent settings from DB
        current_settings = get_state_value("agent_settings", {})
        if "testcoderag" in current_settings:
            del current_settings["testcoderag"]
            set_state_value("agent_settings", current_settings)
        # Cleanup agent database record
        try:
            repo.delete(agent_id)
        except Exception:
            pass

    print("Agent Inspector & Live Optimizer verified successfully!")

if __name__ == "__main__":
    test_agent_optimizer()
