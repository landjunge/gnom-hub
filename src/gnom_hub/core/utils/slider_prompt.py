"""
slider_prompt.py
Baut den System-Prompt eines Agenten aus festen Blöcken + Slider-Konfiguration zusammen.
Reihenfolge ist die Sicherheitslinie — Slider können nie Identität oder Security überschreiben.
"""

import json
import os

LEVELS = ["low", "medium", "high"]

SLIDER_KEYS = ["verbosity", "autonomy", "rückfrage", "ton", "fokus"]


def load_slider_config(agent_name: str) -> dict:
    """Lädt die Slider-Konfiguration für einen Agenten aus der JSON-Datei."""
    from gnom_hub.core.config import CONFIG_DIR as AGENTS_BASE
    path = os.path.join(str(AGENTS_BASE), "agents", f"{agent_name}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_slider_block(config: dict) -> str:
    """
    Erstellt den dynamischen Slider-Block aus der Konfiguration.
    Gibt einen einzelnen zusammengesetzten String zurück.
    """
    if not config or "sliders" not in config or "prompt_blocks" not in config:
        return ""

    sliders = config["sliders"]
    blocks = config["prompt_blocks"]
    lines = []

    for key in SLIDER_KEYS:
        if key in blocks:
            lines.append(blocks[key])

    return "\n".join(lines)


def build_system_prompt(
    agent_identity_block: str,
    agent_name: str,
    soul_facts: list[str],
    agent_tools_block: str,
    agent_security_block: str,
) -> str:
    """
    Baut den vollständigen System-Prompt in sicherer Reihenfolge:

    1. IDENTITÄT     — fest, unberührbar, Injection-geschützt
    2. SLIDER-BLOCK  — dynamisch aus Slider-Konfiguration
    3. TOOLS         — fest pro Agent
    4. SOUL-FAKTEN   — dynamisch aus SoulAG
    5. SECURITY      — fest, immer letzter Block
    6. IDENTITÄT     — Wiederholung als Injection-Schutz am Ende

    Slider können NIEMALS Identität oder Security überschreiben.
    """
    parts = []

    # 1. Identität — Anfang
    identity_header = f"⚠️ DU BIST {agent_name} UND NUR {agent_name}\n\n{agent_identity_block}"
    parts.append(identity_header)

    # 2. Dynamischer Slider-Block
    config = load_slider_config(agent_name)
    slider_block = build_slider_block(config)
    if slider_block:
        parts.append(f"[VERHALTEN]\n{slider_block}")

    # 3. Tools & Fähigkeiten
    if agent_tools_block:
        parts.append(f"[TOOLS]\n{agent_tools_block}")

    # 4. Soul-Fakten
    if soul_facts:
        facts_text = "\n".join(f"- {f}" for f in soul_facts)
        parts.append(f"[KONTEXT]\n{facts_text}")

    # 5. Security — immer vorletzter Block
    if agent_security_block:
        parts.append(f"[SICHERHEIT]\n{agent_security_block}")

    # 6. Identität — Ende (Injection-Schutz)
    parts.append(f"⚠️ DU BIST {agent_name} UND NUR {agent_name}")

    return "\n\n".join(parts)


def update_slider(agent_name: str, key: str, value: int) -> bool:
    """
    Aktualisiert einen einzelnen Slider-Wert in der Konfigurationsdatei.
    Gibt True zurück wenn erfolgreich.
    """
    if key not in SLIDER_KEYS:
        return False
    if value not in (0, 1, 2):
        return False

    config = load_slider_config(agent_name)
    if not config:
        return False

    # Slider-Wert aktualisieren
    config["sliders"][key] = value

    # Prompt-Block aktualisieren basierend auf neuem Level
    level = LEVEL_MAP[value]
    config["prompt_blocks"][key] = _get_default_block(key, level)

    from gnom_hub.core.config import CONFIG_DIR as AGENTS_BASE
    path = os.path.join(str(AGENTS_BASE), "agents", f"{agent_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return True


def _get_default_block(key: str, level: str) -> str:
    """Fallback-Blöcke wenn kein Custom-Text gesetzt ist."""
    defaults = {
        "verbosity": {
            "low":    "Antworte in max. 3 Sätzen. Nur das Ergebnis.",
            "medium": "Antworte präzise mit kurzem Kontext.",
            "high":   "Erkläre deine Vorgehensweise vollständig und zeige Alternativen auf.",
        },
        "autonomy": {
            "low":    "Bei jeder Unklarheit sofort stoppen und nachfragen.",
            "medium": "Kleine Entscheidungen selbst treffen, große bestätigen.",
            "high":   "Handle vollständig selbst. Frage nur bei echten Blockaden.",
        },
        "rückfrage": {
            "low":    "Niemals unterbrechen. Interpretiere selbst und mache weiter.",
            "medium": "Bei mittlerer Unsicherheit stoppen und kurz nachfragen.",
            "high":   "Bei jeder Ambiguität sofort nachfragen.",
        },
        "ton": {
            "low":    "Antworte technisch und trocken. Keine Floskeln.",
            "medium": "Klar und neutral formulieren.",
            "high":   "Fließend, natürlich und menschenlesbar schreiben.",
        },
        "fokus": {
            "low":    "Exakt beim Task bleiben. Keine verwandten Ideen.",
            "medium": "Hauptsächlich beim Task, gelegentlich Verwandtes einbringen.",
            "high":   "Assoziativ denken und Ideen verknüpfen.",
        },
    }
    return defaults.get(key, {}).get(level, "")
