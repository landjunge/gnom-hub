#!/usr/bin/env python3
"""scripts/migrate_agent_configs.py — Phase-1: 8 Agent-Configs mit identity + allowed_contexts befüllen.

Liest die aktuellen sys_prompt-Strings aus agent_definitions.py und schreibt
config/agents/<name>.json mit allen Feldern die der neue builder braucht:
  - identity (1:1 aus sys_prompt)
  - permissions (aus de/en dict)
  - allowed_contexts (rollenpassend)
  - context_filters (wo nötig)
  - version 5.0

Lässt sliders + prompt_blocks UNVERÄNDERT (kommen aus den existierenden JSONs).

Idempotent: kann mehrfach laufen, ersetzt nur die neuen Felder.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Phase-1-Context-Konfiguration pro Agent (rollenbasiert)
CONTEXT_CONFIG: dict[str, dict] = {
    "SoulAG":     {"allowed_contexts": ["evolution_rules"], "context_filters": {}},
    "GeneralAG":  {
        "allowed_contexts": ["worker_stats", "open_contexts", "workspace_summary", "chat_history_tail", "evolution_rules"],
        "context_filters": {"active_rules": {"enabled": False}},
    },
    "WatchdogAG": {
        "allowed_contexts": ["active_rules", "workspace_summary"],
        "context_filters": {},
    },
    "SecurityAG": {
        "allowed_contexts": ["active_rules", "workspace_summary"],
        "context_filters": {},
    },
    "CoderAG":       {"allowed_contexts": ["workspace_summary", "chat_history_tail"], "context_filters": {}},
    "WriterAG":      {"allowed_contexts": ["workspace_summary", "chat_history_tail"], "context_filters": {}},
    "ResearcherAG":  {"allowed_contexts": ["workspace_summary", "chat_history_tail"], "context_filters": {}},
    "EditorAG":      {"allowed_contexts": ["workspace_summary", "chat_history_tail"], "context_filters": {}},
}

# Notes pro Agent (Erklärung für Rollenwahl)
NOTES: dict[str, str] = {
    "SoulAG":     "SoulAG bekommt KEINE automatischen Worker-Context-Blöcke — Denkprozesse werden asynchron extrahiert (agent_base.py:179-207). Wohl aber evolution_rules (Tribunal-Historie).",
    "GeneralAG":  "GeneralAG bekommt bewusst KEINE active_rules — das wäre ein Rollenbruch. Plus evolution_rules für Worker-Improvements.",
    "WatchdogAG": "Nur path/binary_pattern/command rules (rollengefiltert in context.py:_get_active_rules).",
    "SecurityAG": "Nur permission/whitelist/override rules (rollengefiltert in context.py:_get_active_rules).",
    "CoderAG":    "Worker: minimal — Workspace + Chat-History reichen für Tool-Auswahl.",
    "WriterAG":   "Worker: minimal — Workspace + Chat-History.",
    "ResearcherAG": "Worker: minimal — Workspace + Chat-History.",
    "EditorAG":   "Worker: minimal — Workspace + Chat-History.",
}


def main() -> int:
    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS

    config_dir = ROOT / "config" / "agents"
    config_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for name, defn in AGENT_DEFINITIONS.items():
        path = config_dir / f"{name}.json"
        if not path.exists():
            print(f"⚠ {name}: config fehlt, lege neu an")
            cfg = {"agent": name.title().replace("Ag", "AG") if name.lower() != "soulag" else "SoulAG"}
        else:
            cfg = json.loads(path.read_text(encoding="utf-8"))

        # Neue Felder setzen
        cfg["version"] = "5.0"
        cfg["identity"] = defn["sys_prompt"]
        cfg["permissions"] = defn.get("de", {}).get("permissions", ["read"])
        ctx = CONTEXT_CONFIG.get(defn["name"], {})
        cfg["allowed_contexts"] = ctx.get("allowed_contexts", [])
        if ctx.get("context_filters"):
            cfg["context_filters"] = ctx["context_filters"]
        else:
            cfg.pop("context_filters", None)
        cfg["notes"] = NOTES.get(defn["name"], "")

        path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary.append((defn["name"], len(cfg["identity"]), len(cfg["allowed_contexts"])))

    print(f"\n✓ {len(summary)} Agent-Configs aktualisiert:")
    print(f"  {'Agent':<14} {'Identity-Chars':>15} {'Allowed-Contexts':>17}")
    for name, ic, ac in summary:
        print(f"  {name:<14} {ic:>15} {ac:>17}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
