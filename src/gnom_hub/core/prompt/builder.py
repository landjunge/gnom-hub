"""core/prompt/builder.py — Single Source of Truth für Agent System-Prompts.

Layout of the assembled prompt:
  1. Identity-Header  (⚠️ DU BIST <name> UND NUR <name>)
  2. Identity-Text    (aus config/agents/<name>.json#identity)
  3. [VERHALTEN]      (slider prompt_blocks)
  4. [TOOLS]          (permissions)
  5. [SICHERHEIT]     (statisch)
  6. [KONTEXT:*]      (runtime-injected, per-agent opt-in via allowed_contexts)
  7. Identity-Closing (⚠️ DU BIST <name> UND NUR <name>)
  8. Post-Processing  (optional, nur wenn runtime_settings übergeben wird)
     - core.prompt.post_processing: Obedience + Behavioral + Custom + Preset
     - core.prompt.context: Context-Fetcher (Evolution-Rules etc.)

Entstehung:
  - Phase 1 (2026-06-24): Plumbing, neue Datei läuft parallel zu core/utils/slider_prompt.py.
  - Phase 2 (2026-06-24): SSOT — agent_base.py:107-150 gelöscht, router._build_sys
    ruft nur noch diese Funktion. Override-Pfad in router.py entfernt.
    Post-Processing aus router.py hier portiert.
  - Phase 3 (2026-06-24): Post-Processing in eigenes Modul extrahiert
    (core.prompt.post_processing). Evolution-Rules als Context-Fetcher
    ausgelagert (core.prompt.context). Die Re-Exporte unten halten die
    Backwards-Kompatibilität für bestehende Tests.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from gnom_hub.core.config import CONFIG_DIR

from .context import get_context_blocks
from .post_processing import (
    _get_behavioral_instructions,
    _get_obedience_instructions,
)
from .post_processing import (
    apply_post_processing as _apply_post_processing,
)

logger = logging.getLogger(__name__)


# Re-Exporte für Backwards-Kompatibilität — tests/ darf weiterhin
# `from gnom_hub.core.prompt.builder import _get_obedience_instructions`
# importieren, obwohl die Definition in post_processing.py lebt.
__all__ = [
    "build_system_prompt",
    "_inject_tkg_recall",
    "_load_agent_config",
    "_apply_post_processing",
    "_get_obedience_instructions",
    "_get_behavioral_instructions",
]


# Reihenfolge wichtig — matcht die alte build_slider_block() Reihenfolge
# in core/utils/slider_prompt.py:11 (LEVELS) / :13 (SLIDER_KEYS)
SLIDER_KEYS_ORDER: tuple[str, ...] = (
    "creativity", "precision", "speed", "critical_thinking", "obedience",
)


def _load_agent_config(agent_name: str) -> dict | None:
    """Load agent JSON config from CONFIG_DIR/agents/<name>.json.

    Returns None wenn Datei fehlt oder invalides JSON.
    """
    path = Path(str(CONFIG_DIR)) / "agents" / f"{agent_name}.json"
    if not path.exists():
        logger.error("agent config not found: %s", path)
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("agent config invalid: %s (%s)", path, e)
        return None


def _build_verhalten_block(cfg: dict) -> str:
    """Baut den [VERHALTEN]-Block aus prompt_blocks (oder sliders als Fallback)."""
    prompt_blocks = cfg.get("prompt_blocks") or {}
    if prompt_blocks:
        # Match alte Reihenfolge: SLIDER_KEYS_ORDER
        lines = [prompt_blocks[k] for k in SLIDER_KEYS_ORDER if k in prompt_blocks]
        if lines:
            return "[VERHALTEN]\n" + "\n".join(lines)
    # Fallback: rohe slider-Werte (sollte nicht passieren wenn prompt_blocks gepflegt)
    sliders = cfg.get("sliders", {})
    if sliders:
        lines = "\n".join(f"  {k}: {v}" for k, v in sliders.items())
        return f"[VERHALTEN]\n{lines}"
    return ""


# ── Public API ─────────────────────────────────────────────────────────────

def _inject_tkg_recall(base: str, agent_name: str, message_text: str) -> str:
    """Inject TKG auto-recall facts for the current user message.

    Wired into the real agent loop (ask_router → build_system_prompt).
    Best-effort: any failure returns ``base`` unchanged. Empty / trivial
    messages skip recall so golden/static prompt tests stay stable.
    """
    msg = (message_text or "").strip()
    if len(msg) < 10:
        return base
    # Avoid treating the old default system string as a query
    if msg in ("Du bist ein Assistent.", "You are an assistant."):
        return base
    try:
        from gnom_hub.core.config import Config
        if not getattr(Config, "TKG_AUTO_RECALL", True):
            return base
    except Exception:
        pass

    try:
        top_k = 6
        try:
            from gnom_hub.core.constants import MEMORY_STRENGTH_MAP
            from gnom_hub.db import get_state_value
            settings = (get_state_value("agent_settings") or {}).get(
                agent_name.lower(), {}
            )
            top_k = MEMORY_STRENGTH_MAP.get(
                int(settings.get("memory_strength", 3)), 6
            )
        except Exception:
            pass

        from gnom_hub.memory_tkg.adapter import retrieve_relevant
        facts = retrieve_relevant(msg, top_k=top_k)
        if not facts:
            return base

        lines: list[str] = []
        for f in facts:
            s = str(f).strip().replace("\n", " ")
            if not s:
                continue
            if len(s) > 400:
                s = s[:400] + "…"
            lines.append(f"- {s}")
        if not lines:
            return base

        block = (
            "[KONTEXT:tkg_recall]\n"
            "=== RELEVANTE ERINNERUNGEN (TKG) ===\n"
            + "\n".join(lines)
        )
        return base + "\n\n" + block
    except Exception as e:
        logger.debug("TKG auto-recall failed for %s: %s", agent_name, e)
        return base


def build_system_prompt(
    agent_name: str,
    message_text: str = "",
    runtime_settings: dict | None = None,
) -> str:
    """Build the complete system prompt for an agent.

    Args:
        agent_name: one of the 8 frozen agent names (e.g. "GeneralAG")
        message_text: current user/queue message — used for TKG auto-recall.
        runtime_settings: optional dict mit Runtime-Settings aus dem
            State-Table. Wenn None, wird Post-Processing übersprungen.
            Typische Keys: obedience, personality, response_style,
            risk_tolerance, custom_prompt, active_preset.

    Returns:
        Der zusammengesetzte System-Prompt als einzelner String.
    """
    cfg = _load_agent_config(agent_name)
    if cfg is None:
        return f"⚠️ FEHLER: Keine Konfiguration gefunden für Agent '{agent_name}'"

    parts: list[str] = []

    # 1. Identity-Header
    parts.append(f"⚠️ DU BIST {agent_name} UND NUR {agent_name}")

    # 2. Identity-Text (Pflicht-Feld in Config)
    identity = cfg.get("identity", "").strip()
    if not identity:
        return f"⚠️ FEHLER: 'identity' Feld fehlt in config für {agent_name}"
    parts.append(identity)

    # 3. Verhalten (slider prompt_blocks)
    if verhalten := _build_verhalten_block(cfg):
        parts.append(verhalten)

    # 4. Tools / Permissions
    perms = cfg.get("permissions", ["read"])
    parts.append(f"[TOOLS]\nErlaubte Aktionen: {', '.join(perms)}")

    # 5. Sicherheit (statisch, kurz — matcht den alten security-Block)
    parts.append(
        "[SICHERHEIT]\n"
        "Systemdateien und gefährliche Patterns sind geblockt. "
        "Shell-Zugriff nur über Whitelist."
    )

    # 6. Runtime Context Blocks (per-agent opt-in, rollengefiltert)
    context_blocks = get_context_blocks(agent_name, cfg)
    if context_blocks:
        parts.extend(context_blocks)

    # 7. Identity-Closing (Verstärkung)
    parts.append(f"⚠️ DU BIST {agent_name} UND NUR {agent_name}")

    base = "\n\n".join(parts)

    # 7b. TKG auto-recall (per-message, all agents)
    base = _inject_tkg_recall(base, agent_name, message_text)

    # 8. Post-Processing (nur wenn runtime_settings übergeben)
    if runtime_settings:
        base = _apply_post_processing(base, agent_name, runtime_settings)

    return base
