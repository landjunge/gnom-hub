#!/usr/bin/env python3
"""scripts/snapshot_golden_prompts.py — Freeze current prompt output for all 8 agents.

Snapshottet den CURRENT (legacy) Prompt-Stand via core.utils.slider_prompt.build_system_prompt().
Wird für den byte-genauen Diff-Vergleich nach dem Refactor gebraucht.

Usage:
    PYTHONPATH=src python3.10 scripts/snapshot_golden_prompts.py

Output:
    tests/golden/prompts_before.json — dict {agent_name: full_prompt_string}

Wichtig — Coverage-Limitierung:
    Dieses Script snapshottet NUR build_system_prompt() (den inneren Wrap-Block).
    Die volle Pipeline (agent_base.py:107-150 + router.py:88-138 mit Obedience,
    Behavioral, Custom-Prompt, Preset) ist als separater Integration-Test abgedeckt
    (siehe tests/integration/test_prompt_pipeline_golden.py — Phase 1 TODO).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

AGENTS: tuple[str, ...] = (
    "SoulAG", "GeneralAG", "WatchdogAG", "SecurityAG",
    "CoderAG", "WriterAG", "ResearcherAG", "EditorAG",
)

GOLDEN_PATH: Path = ROOT / "tests" / "golden" / "prompts_before.json"


def main() -> int:
    from gnom_hub.core.utils.slider_prompt import build_system_prompt as legacy_build

    golden: dict[str, str] = {}
    for name in AGENTS:
        # Mock-Identity — gleiche Shape wie router.py:115 dem legacy_build() übergibt.
        # Die echte Identity kommt aus agent_definitions.py via get_soul(name)["sys_prompt"].
        # Für Golden-Vergleich zählt nur die Wrap-Struktur (slider/tools/security/closing).
        mock_identity = f"[MOCK IDENTITY for {name}]"
        golden[name] = legacy_build(
            agent_identity_block=mock_identity,
            agent_name=name,
            soul_facts=[],
            agent_tools_block="Perms: read",
            agent_security_block="Systemdateien+Gefährliche Patterns geblockt. Shell via Whitelist.",
        )

    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GOLDEN_PATH, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)

    total_chars = sum(len(v) for v in golden.values())
    print(f"✓ Golden snapshot written: {GOLDEN_PATH}")
    print(f"  Agents: {len(golden)}, total chars: {total_chars}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
