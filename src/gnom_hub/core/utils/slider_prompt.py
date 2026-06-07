"""
slider_prompt.py — Claude 5-Level Slider System
Baut den System-Prompt aus Blöcken + Slider-Konfiguration zusammen.
5 Stufen pro Slider (0–4): minimal, low, medium, high, maximum
"""

import json
import os
from typing import List

LEVELS = ["minimal", "low", "medium", "high", "maximum"]

SLIDER_KEYS = ["creativity", "precision", "speed", "critical_thinking", "obedience"]

VALID_VALUES = (0, 1, 2, 3, 4)


def load_slider_config(agent_name: str) -> dict:
    from gnom_hub.core.config import CONFIG_DIR as AGENTS_BASE
    path = os.path.join(str(AGENTS_BASE), "agents", f"{agent_name}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_slider_block(config: dict) -> str:
    if not config or "sliders" not in config or "prompt_blocks" not in config:
        return ""
    blocks = config["prompt_blocks"]
    lines = []
    for key in SLIDER_KEYS:
        if key in blocks:
            lines.append(blocks[key])
    return "\n".join(lines)


def build_system_prompt(
    agent_identity_block: str,
    agent_name: str,
    soul_facts: List[str],
    agent_tools_block: str,
    agent_security_block: str,
) -> str:
    parts = []
    identity_header = f"⚠️ DU BIST {agent_name} UND NUR {agent_name}\n\n{agent_identity_block}"
    parts.append(identity_header)

    config = load_slider_config(agent_name)
    slider_block = build_slider_block(config)
    if slider_block:
        parts.append(f"[VERHALTEN]\n{slider_block}")

    if agent_tools_block:
        parts.append(f"[TOOLS]\n{agent_tools_block}")

    if soul_facts:
        facts_text = "\n".join(f"- {f}" for f in soul_facts)
        parts.append(f"[KONTEXT]\n{facts_text}")

    if agent_security_block:
        parts.append(f"[SICHERHEIT]\n{agent_security_block}")

    parts.append(f"⚠️ DU BIST {agent_name} UND NUR {agent_name}")
    return "\n\n".join(parts)


def update_slider(agent_name: str, key: str, value: int) -> bool:
    if key not in SLIDER_KEYS:
        return False
    if value not in VALID_VALUES:
        return False

    config = load_slider_config(agent_name)
    if not config:
        return False

    config["sliders"][key] = value
    level = LEVELS[value]
    config["prompt_blocks"][key] = _get_default_block(key, level)

    from gnom_hub.core.config import CONFIG_DIR as AGENTS_BASE
    path = os.path.join(str(AGENTS_BASE), "agents", f"{agent_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return True


def _get_default_block(key: str, level: str) -> str:
    defaults = {
        "creativity": {
            "minimal": "No creativity. Use only established, standard patterns. Zero experimentation.",
            "low":     "Prefer proven patterns. Minimal variation allowed.",
            "medium":  "Balance standard approaches with occasional creative solutions.",
            "high":    "Propose novel solutions regularly. Break conventions when beneficial.",
            "maximum": "Free innovation. Wild ideas welcome. Reinvent if needed.",
        },
        "precision": {
            "minimal": "Approximations fine. Speed over accuracy.",
            "low":     "Low precision. Verify only critical paths.",
            "medium":  "Balanced accuracy. Verify main outputs.",
            "high":    "Detailed verification. Edge cases must be considered.",
            "maximum": "Flawless precision. Double-check everything. Zero tolerance for errors.",
        },
        "speed": {
            "minimal": "No rush. Maximum quality. Take as long as needed.",
            "low":     "Slow pace. Prioritize thoroughness over velocity.",
            "medium":  "Steady pace. Deliver when ready.",
            "high":    "Deliver quickly. First viable version fast.",
            "maximum": "Instant delivery. Speed over everything.",
        },
        "critical_thinking": {
            "minimal": "No questioning. Execute literally. No analysis.",
            "low":     "Minimal analysis. Flag only critical blocking issues.",
            "medium":  "Think about the task. Suggest obvious improvements.",
            "high":    "Challenge assumptions actively. Propose fundamental changes.",
            "maximum": "Deep skepticism. Question everything. Identify root systemic issues.",
        },
        "obedience": {
            "minimal": "Blindly follow instructions. Execute literally. No deviation.",
            "low":     "Close adherence. Minimal interpretation. Limited autonomy.",
            "medium":  "Follow instructions with reasonable interpretation. Small adjustments OK.",
            "high":    "High autonomy. Instructions are loose guidelines. Choose better path.",
            "maximum": "Complete autonomy. Instructions are suggestions. Always choose best path.",
        },
    }
    return defaults.get(key, {}).get(level, "")
