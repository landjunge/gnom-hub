import os, json
from .db import get_state_value, set_state_value, save_soul_fact, add_chat_message

def load_presets():
    path = os.path.join(os.path.dirname(__file__), "presets.json")
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def get_preset_prompt(preset: str, agent_name: str) -> str:
    try: return load_presets().get("prompts", {}).get(preset, {}).get(agent_name)
    except Exception: return None

def handle_preset_change(preset: str):
    save_soul_fact("active_preset", preset)
    set_state_value("active_preset", preset)
    custom = get_state_value(f"llm_preset_{preset}")
    if isinstance(custom, dict) and custom:
        set_state_value("llm_agents", custom)
    else:
        adb = get_state_value("llm_agents") or {}
        kdb = get_state_value("llm_keys") or {}
        or_valid = any(k.get("provider") == "openrouter" and k.get("valid") for k in (kdb.values() if isinstance(kdb, dict) else kdb))
        targets = {
            "Web Development": ("coderag", "qwen/qwen3-coder:free"),
            "Graphic Design": ("coderag", "meta-llama/llama-3.3-70b-instruct:free"),
            "Marketing & Copy": ("writerag", "meta-llama/llama-3.3-70b-instruct:free"),
            "Research & Analysis": ("researcherag", "meta-llama/llama-3.3-70b-instruct:free"),
        }
        for agent in ["coderag", "researcherag", "writerag", "editorag"]:
            adb[agent] = {"provider": "auto", "model": "stage_2" if agent != "coderag" else "stage_3"}
        if preset in targets:
            agent, model = targets[preset]
            adb[agent] = {"provider": "openrouter", "model": model} if or_valid else {"provider": "auto", "model": "stage_3"}
        set_state_value("llm_agents", adb)
    focus = load_presets().get("focus", {}).get(preset, "Allgemeine Unterstützung des Schwarms.")
    msg = f"Preset gewechselt zu: **{preset}**.\n\nIch habe das Verhalten und die Modelle der Worker-Agenten wie folgt angepasst: *{focus}*"
    add_chat_message("default", "SoulAG", "soulag", "chat", msg)
