"""core/prompt/context.py — Pure fetcher layer for system-prompt context blocks.

Each fetcher is independent and error-resilient:
  - Returns "" on any failure (logged at WARNING, never raised)
  - No class state, no side effects beyond DB reads
  - Configurable per agent: enabled via allowed_contexts in agent config

Design choice — pure functions instead of a class:
  - Testable in isolation (mock DB, mock fs)
  - Easy to add new fetchers (one function + one entry in the dispatcher)
  - Builder can call them in any order
  - Failure of one block doesn't break the whole prompt

Phase 1 of the prompt-architecture refactor (2026-06-24):
  - All 6 fetchers are extracted 1:1 from agent_base.py:110-150
  - Active-rules filter is moved HERE (was implicit in the old code)
  - "Lieber leerer Block als kaputter Prompt" — every fetcher wraps try/except
"""
from __future__ import annotations

import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)


# ── Public API ─────────────────────────────────────────────────────────────

def get_context_blocks(agent_name: str, config: dict) -> list[str]:
    """Return all context blocks enabled in the agent config.

    Args:
        agent_name: e.g. "GeneralAG" (one of the 8 frozen names)
        config: the agent's JSON config dict (loaded by builder._load_agent_config)

    Returns:
        List of formatted context blocks. Each block is either:
          - "" → filtered out by builder
          - non-empty string with "[KONTEXT:<name>]\\n..." prefix
    """
    allowed: set[str] = set(config.get("allowed_contexts", []))
    filters: dict = config.get("context_filters", {})

    fetchers: dict[str, Callable[[str, dict], str]] = {
        "worker_stats":      _get_worker_stats,
        "open_contexts":     _get_open_contexts,
        "active_rules":      _get_active_rules,
        "workspace_summary": _get_workspace_summary,
        "chat_history_tail": _get_chat_history_tail,
        "soul_facts":        _get_soul_facts,
        "evolution_rules":   _get_evolution_rules,
    }

    blocks: list[str] = []
    for key, fetcher in fetchers.items():
        if key not in allowed:
            continue
        try:
            block = fetcher(agent_name, filters.get(key, {}))
            if block:
                blocks.append(block)
        except Exception as e:
            # Resilience > perfection: empty block, log, continue
            logger.warning("context fetcher '%s' failed for %s: %s", key, agent_name, e)
    return blocks


# ── Private fetchers ───────────────────────────────────────────────────────
# All functions are: (agent_name: str, cfg: dict) -> str
# All return "" on empty/missing data or on error (handled in dispatcher).

def _get_worker_stats(agent_name: str, cfg: dict) -> str:
    """Worker-Erfolgsraten + avg_duration aus CoordinationDB.

    Primär sinnvoll für GeneralAG (vom Prompt verlangt). Andere Agents
    bekommen den Block nur wenn in allowed_contexts gelistet.
    Quelle: agent_base.py:110-118 (alter Code).
    """
    from gnom_hub.soul.memory_layers import get_coordination_db
    summary = get_coordination_db().get_worker_summary()
    if not summary:
        return ""
    return "[KONTEXT:worker_stats]\n=== WORKER STATISTIKEN ===\n" + summary


def _get_open_contexts(agent_name: str, cfg: dict) -> str:
    """Aktive (nicht abgeschlossene) Contexts aus ContextDB.

    Primär sinnvoll für GeneralAG.
    Quelle: agent_base.py:115-118 (alter Code).
    """
    from gnom_hub.soul.memory_layers import get_context_db
    summary = get_context_db().get_summary_for_generalag()
    if not summary:
        return ""
    return "[KONTEXT:open_contexts]\n" + summary


def _get_active_rules(agent_name: str, cfg: dict) -> str:
    """Rules aus RulesDB, gefiltert nach Agent-Rolle.

    Verhalten:
      - WatchdogAG bekommt path/binary_pattern/command rules
      - SecurityAG bekommt permission/whitelist/override rules
      - Alle anderen Agenten bekommen nichts (Filter hier, nicht im Prompt)

    Quelle: agent_base.py:122-131 (alter Code, dort ungefiltert).
    """
    name = agent_name.lower()
    if "watchdog" not in name and "security" not in name:
        return ""

    from gnom_hub.soul.memory_layers import get_rules_db
    rules = get_rules_db().get_rules_for_agent(agent_name)
    if not rules:
        return ""

    if "watchdog" in name:
        keep = ("path", "binary_pattern", "command")
    else:  # security
        keep = ("permission", "whitelist", "override")
    rules = [r for r in rules if r.get("rule_type") in keep]
    if not rules:
        return ""

    lines = [f"  [{r['rule_type']}] {r['pattern']} — {r['reason']}" for r in rules[:15]]
    return "[KONTEXT:active_rules]\n=== AKTUELLE REGELN ===\n" + "\n".join(lines)


def _get_workspace_summary(agent_name: str, cfg: dict) -> str:
    """Workspace-Pfad + erste 30 Top-Level-Files.

    Quelle: agent_base.py:133-136 (alter Code).
    """
    from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
    wd = get_workspace_dir()
    if not os.path.exists(wd):
        return ""
    files = ", ".join(os.listdir(wd)[:30])
    return f"[KONTEXT:workspace_summary]\n[WORKSPACE: {wd} | Dateien: {files}]"


def _get_chat_history_tail(agent_name: str, cfg: dict) -> str:
    """Letzte 20 Chat-Nachrichten (sender + content[:200]).

    Quelle: agent_base.py:139-150 (alter Code).
    """
    from gnom_hub.db import get_chat_history
    history = get_chat_history(limit=20)
    if not history:
        return ""
    lines = [f"[{h.get('sender','?')}]: {h.get('content','')[:200]}" for h in reversed(history)]
    return "[KONTEXT:chat_history_tail]\n=== CHAT-VERLAUF (letzte 20) ===\n" + "\n".join(lines)


def _get_soul_facts(agent_name: str, cfg: dict) -> str:
    """Soul-Memory Fakten. Default: leer.

    Im aktuellen Code wird soul_facts in router.py:112 als leerer list[]
    übergeben. Diese Funktion ist ein Platzhalter für zukünftige Erweiterung
    (z.B. wenn SoulAG Fakten aus Denkprozessen vorab in den Prompt injizieren
    soll — derzeit passiert das asynchron nach der Antwort, agent_base.py:179-191).
    """
    return ""


# ── Selbstverbesserte Regeln (Evolution-Rules) ─────────────────────────────
def _get_evolution_rules(agent_name: str, cfg: dict) -> str:
    """Holt selbstverbesserte Regeln aus soul_memory.

    Quelle: war router.py:140-149 (portiert in Phase 2 als Teil von
    _apply_post_processing, in Phase 3 hierher als Context-Fetcher ausgelagert).

    Primär sinnvoll für:
      - SoulAG: kennt die Tribunal-Historie und ihre eigenen Decisions
      - GeneralAG: trackt Worker-Improvements über die Zeit

    Reihenfolge der Auflösung (Priorität von oben nach unten):
      1. get_active_version(agent_name).modifications  (in-memory cache)
      2. Direkter soul_memory-Query (key LIKE 'evolution_<name>_%')
      3. Leerer String (kein Fehler, einfach nichts da)

    Resilient: jeder Fehler wird geloggt + leerer String.
    """
    try:
        from gnom_hub.core.utils.evolution_v2 import get_active_version
        from gnom_hub.db.connection import get_db_conn
        av = get_active_version(agent_name)
        rules = av.modifications if av else None
        if not rules:
            with get_db_conn() as conn:
                rules = [row["value"] for row in conn.execute(
                    "SELECT value FROM soul_memory WHERE key LIKE ?",
                    (f"evolution_{agent_name}_%",)
                ).fetchall()]
        if not rules:
            return ""
        return "[KONTEXT:evolution_rules]\n=== SELBSTVERBESSERTE REGELN ===\n" + \
               "\n".join(f"- {x}" for x in rules)
    except Exception as e:
        logger.debug("evolution rules load failed for %s: %s", agent_name, e)
        return ""


__all__ = ["get_context_blocks"]
