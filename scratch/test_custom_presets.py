# test_custom_presets.py — Test custom presets loading and merging
import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
from gnom_hub.core.config import CONFIG_DIR
from gnom_hub.core.utils.preset_service import load_presets, handle_preset_change

def test_custom_presets():
    print("--- STARTING CUSTOM PRESETS UNIT TESTS ---")
    gnom_hub.db.init_db()

    # Create config/presets directory
    pdir = CONFIG_DIR / "presets"
    pdir.mkdir(parents=True, exist_ok=True)

    # Write custom test preset
    test_preset_data = {
        "name": "Unity Game Dev",
        "description": "Unity game programming helper.",
        "model": {
            "primary": "qwen/qwen3-coder:free"
        },
        "prompt_modifier": {
            "coderag": "SYSTEM-ROLLE: UNITY GAME DEV. Use C# scripting principles."
        },
        "allowed_tools": ["CODER"]
    }
    
    preset_file = pdir / "unity_game_dev.json"
    with open(preset_file, "w", encoding="utf-8") as f:
        json.dump(test_preset_data, f)

    try:
        # 1. Test load_presets loads custom preset
        presets = load_presets()
        assert "Unity Game Dev" in presets.get("prompts", {})
        assert presets["prompts"]["Unity Game Dev"]["coderag"] == "SYSTEM-ROLLE: UNITY GAME DEV. Use C# scripting principles."
        assert presets["focus"]["Unity Game Dev"] == "Unity game programming helper."
        assert presets["targets"]["Unity Game Dev"] == ["coderag", "qwen/qwen3-coder:free"]

        # 2. Test handle_preset_change works on custom preset
        handle_preset_change("Unity Game Dev")
        assert gnom_hub.db.get_state_value("active_preset") == "Unity Game Dev"

    finally:
        # Clean up
        if preset_file.exists():
            preset_file.unlink()

    print("Custom presets system verified successfully!")

if __name__ == "__main__":
    test_custom_presets()
