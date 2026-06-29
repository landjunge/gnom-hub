"""core/prompt/post_processing.py — Post-Processing für System-Prompts.

Wird von core.prompt.builder aufgerufen NACHDEM der Basis-Prompt
(Identity + Slider + Tools + Security + Context-Blöcke + Closing)
zusammengebaut ist. Fügt 4 Schichten an:

  1. Obedience-Slider Text (1=blind, 5=hochautonom)
  2. Behavioral-Sliders (personality / response_style / risk_tolerance)
  3. Custom-Prompt Suffix (aus runtime_settings.custom_prompt)
  4. Preset-Prefix (nur Worker, vorgeschoben statt angehängt)

Entstehung:
  - Phase 1 (2026-06-24): Logik lebte verstreut in router.py:124-136.
  - Phase 2 (2026-06-24): in core.prompt.builder._apply_post_processing konsolidiert.
  - Phase 3 (2026-06-24): in dieses eigene Modul extrahiert damit builder.py
    nur den Basis-Prompt baut. Saubere Trennung der Verantwortlichkeiten.

Was NICHT hier lebt (Phase 3 Auslagerung):
  - Evolution-Rules → core/prompt/context.py:_get_evolution_rules
    (sind ein Context-Fetcher, kein Post-Processing, weil sie zur State-Sicht
    des Basis-Prompts gehören)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _get_obedience_instructions(level: int) -> str:
    """Obedience-Slider Text. 1=blind, 5=hochautonom. Default 3=balanced.

    Portiert von router.py:63-86 (1:1, nur Standort verändert).
    """
    instructions = {
        1: ("=== OBEDIENCE: BLINDLY FOLLOWS ===\n"
            "Du folgst Anweisungen strikt und wörtlich. "
            "Hinterfrage nichts, interpretiere nicht um. "
            "Führe aus was verlangt wird, ohne eigene Meinung."),
        2: ("=== OBEDIENCE: STRONGLY FOLLOWS ===\n"
            "Du bist stark an den User gebunden. "
            "Triff kleine Entscheidungen selbst, aber frage bei Unsicherheit nach. "
            "Weiche nur von Anweisungen ab, wenn du einen klaren Fehler erkennst."),
        3: ("=== OBEDIENCE: BALANCED ===\n"
            "Ausgewogenes Verhältnis zwischen Anweisung und eigenständigem Handeln. "
            "Biete Alternativen an wenn du einen besseren Weg siehst, "
            "aber führe die Anweisung aus wenn der User darauf besteht."),
        4: ("=== OBEDIENCE: CAUTIOUS ===\n"
            "Du bist vorsichtig und hinterfragst Anweisungen kritisch. "
            "Schlage aktiv bessere Alternativen vor. "
            "Warne vor Risiken oder Nachteilen. Entscheide selbst wenn du es besser weißt."),
        5: ("=== OBEDIENCE: HIGHLY AUTONOMOUS ===\n"
            "Du handelst hochgradig eigenständig. "
            "Triff Entscheidungen selbst und frage nur bei echten Blockaden. "
            "Du darfst Anweisungen ignorieren wenn du einen fundamental besseren Ansatz siehst.")
    }
    return "\n\n" + instructions.get(level, instructions[3])


def _get_behavioral_instructions(settings: dict) -> str:
    """Personality / Response-Style / Risk-Tolerance → Verhaltens-Text.

    Portiert von router.py:22-54 (1:1, nur Standort verändert).
    Nur Werte 1, 2, 4, 5 haben Einträge — 3 (default) ergibt leeren Block.
    """
    custom_insts: list[str] = []

    p_val = settings.get("personality", 3)
    p_map = {
        1: "Tone instructions: Maintain an extremely formal, professional, and serious tone. Avoid casual language.",
        2: "Tone instructions: Keep a polite, professional, and business-like tone.",
        4: "Tone instructions: Maintain a friendly, warm, and approachable tone.",
        5: "Tone instructions: Be very casual, relaxed, and conversational."
    }
    if p_map.get(p_val):
        custom_insts.append(p_map[p_val])

    r_val = settings.get("response_style", 3)
    r_map = {
        1: "Length instructions: Be extremely concise, direct, and brief. Output only essential information.",
        2: "Length instructions: Keep your responses concise and to the point.",
        4: "Length instructions: Provide detailed, comprehensive explanations and structure your answers thoroughly.",
        5: "Length instructions: Be exceptionally detailed and exhaustive. Elaborate on all details, write step-by-step breakdowns, and provide deep context."
    }
    if r_map.get(r_val):
        custom_insts.append(r_map[r_val])

    k_val = settings.get("risk_tolerance", 3)
    k_map = {
        1: "Safety/Risk instructions: Prioritize safety, robustness, and stability. Avoid speculative changes, check every dependency, and do not make risky optimizations.",
        2: "Safety/Risk instructions: Be cautious and prefer conservative, well-tested approaches.",
        4: "Safety/Risk instructions: Be proactive and suggest innovative, creative solutions or optimizations.",
        5: "Safety/Risk instructions: Be extremely bold and experimental. Propose radical refactorings, cutting-edge APIs, and high-performance optimizations."
    }
    if k_map.get(k_val):
        custom_insts.append(k_map[k_val])

    return "\n\n=== VERHALTENS-INSTRUKTIONEN ===\n" + "\n".join(custom_insts) if custom_insts else ""


def apply_post_processing(prompt: str, agent_name: str, settings: dict) -> str:
    """Reihenfolge: Obedience → Behavioral → Custom → Preset-Prefix (Worker).

    Reihenfolge matcht router.py:124-136 (alt):
      1. Obedience-Suffix
      2. Behavioral-Suffix
      3. Custom-Prompt Suffix
      4. Preset-Prefix (nur Worker, vorgeschoben statt angehängt)

    Args:
        prompt: Der Basis-Prompt (Schritte 1-7 inkl. Context-Blöcke)
        agent_name: z.B. "CoderAG"
        settings: runtime_settings dict, muss "active_preset" enthalten
                  (vom Caller gelesen aus get_state_value("active_preset"))
    """
    prompt += _get_obedience_instructions(settings.get("obedience", 3))

    if bh := _get_behavioral_instructions(settings):
        prompt += bh

    if cp := settings.get("custom_prompt"):
        prompt += "\n\n=== BENUTZERDEFINIERTER SUFFIX ===\n" + cp

    name_lower = agent_name.lower()
    if name_lower in ("coderag", "researcherag", "writerag", "editorag"):
        from gnom_hub.core.utils.preset_service import get_preset_prompt
        active_preset = settings.get("active_preset", "Web Development")
        if prs := get_preset_prompt(active_preset, name_lower):
            prompt = prs + "\n\n" + prompt

    return prompt


__all__ = [
    "apply_post_processing",
    "_get_obedience_instructions",
    "_get_behavioral_instructions",
]
