# preset_service.py — Preset management loader and trigger actions
import os, json
from gnom_hub.database.legacy_db import get_state_value, set_state_value, save_soul_fact, add_chat_message
from gnom_hub.core.config import CONFIG_DIR
def load_presets():
    path = os.path.join(os.path.dirname(__file__), "presets.json")
    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
    pdir = CONFIG_DIR / "presets"
    if pdir.exists():
        for fn in [f for f in os.listdir(pdir) if f.endswith(".json")]:
            try:
                with open(pdir / fn, "r", encoding="utf-8") as f: c = json.load(f)
                name = c.get("name")
                if name:
                    data.setdefault("prompts", {})[name] = c.get("prompt_modifier", {})
                    data.setdefault("focus", {})[name] = c.get("description", "Custom.")
                    tm, ta = c.get("model", {}).get("primary"), c.get("allowed_tools", [None])[0]
                    if tm and ta: data.setdefault("targets", {})[name] = [ta.lower() + "ag", tm]
            except Exception: pass
    return data
def get_preset_prompt(preset: str, agent_name: str) -> str:
    return load_presets().get("prompts", {}).get(preset, {}).get(agent_name, "")
def handle_preset_change(preset: str):
    save_soul_fact("active_preset", preset); set_state_value("active_preset", preset)
    custom, adb = get_state_value(f"llm_preset_{preset}"), get_state_value("llm_agents") or {}
    w = ["coderag", "researcherag", "writerag", "editorag"]
    if isinstance(custom, dict) and custom:
        for a in w:
            if a in custom: adb[a] = custom[a]
    else:
        kdb = get_state_value("llm_keys") or {}
        or_v = any(k.get("provider") == "openrouter" and k.get("valid") for k in (kdb.values() if isinstance(kdb, dict) else kdb))
        for a in w: adb[a] = {"provider": "auto", "model": "stage_2" if a != "coderag" else "stage_3"}
        t = load_presets().get("targets", {}).get(preset)
        if t and t[0] in w: adb[t[0]] = {"provider": "openrouter", "model": t[1]} if or_v else {"provider": "auto", "model": "stage_3"}
    set_state_value("llm_agents", adb); focus = load_presets().get("focus", {}).get(preset, "Allgemeine Unterstützung.")
    add_chat_message("default", "System", "system", "chat", f"Preset gewechselt zu: **{preset}**.\n\nWorker angepasst: *{focus}*")
