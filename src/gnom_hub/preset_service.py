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
    adb = get_state_value("llm_agents") or {}
    workers = ["coderag", "researcherag", "writerag", "editorag"]
    if isinstance(custom, dict) and custom:
        for a in workers:
            if a in custom: adb[a] = custom[a]
    else:
        kdb = get_state_value("llm_keys") or {}
        or_valid = any(k.get("provider") == "openrouter" and k.get("valid") for k in (kdb.values() if isinstance(kdb, dict) else kdb))
        for a in workers:
            adb[a] = {"provider": "auto", "model": "stage_2" if a != "coderag" else "stage_3"}
        t = load_presets().get("targets", {}).get(preset)
        if t and t[0] in workers:
            adb[t[0]] = {"provider": "openrouter", "model": t[1]} if or_valid else {"provider": "auto", "model": "stage_3"}
    set_state_value("llm_agents", adb)
    focus = load_presets().get("focus", {}).get(preset, "Allgemeine Unterstützung.")
    add_chat_message("default", "System", "system", "chat", f"Preset gewechselt zu: **{preset}**.\n\nWorker angepasst: *{focus}*")
