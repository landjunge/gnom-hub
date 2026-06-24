"""tests/integration/test_prompt_pipeline_golden.py

Golden-Prompt-Vergleich für die Phase-1-Migration des Prompt-Architektur-Refactors.

Repliziert die alte Pipeline (agent_base.py:107-152 + router.py:88-138) und vergleicht
mit der neuen build_system_prompt() aus core.prompt.builder.

Phase-1-Constraint: byte-genaue Kompatibilität. Bekannte strukturbedingte Unterschiede
werden dokumentiert, der Test schlägt fehl wenn:
  - Identity-Text von AGENT_DEFINITIONS nicht 1:1 in config/agents/<name>.json#identity steht
  - Kernsections ([VERHALTEN], [TOOLS], [SICHERHEIT], ⚠️ Identity-Header) fehlen
  - Context-Dispatcher ignoriert allowed_contexts

Run:
    PYTHONPATH=src python3.10 -m pytest tests/integration/test_prompt_pipeline_golden.py -v -s
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
from gnom_hub.core.utils.slider_prompt import build_system_prompt as old_build
from gnom_hub.core.prompt.builder import build_system_prompt as new_build, _apply_post_processing

ALL_AGENTS: tuple[str, ...] = (
    "SoulAG", "GeneralAG", "WatchdogAG", "SecurityAG",
    "CoderAG", "WriterAG", "ResearcherAG", "EditorAG",
)

GOLDEN_DIR: Path = Path(__file__).parent.parent / "golden"
CONFIG_DIR: Path = Path(__file__).parent.parent.parent / "config" / "agents"


# ── Hilfsfunktionen ────────────────────────────────────────────────────────

def _build_old_prompt(agent_name: str) -> str:
    """Repliziert die VOLLE alte Pipeline: agent_base.py:107-152 + router.py:88-149.

    Phase-2-Update: inkludiert jetzt auch Post-Processing (Obedience, Behavioral,
    Custom, Preset, Evolution) — aufgerufen via _apply_post_processing aus dem
    neuen builder (1:1 portiert von router.py).
    """
    defn = AGENT_DEFINITIONS[agent_name.lower()]
    sys_p = defn["sys_prompt"]
    perms = defn.get("de", {}).get("permissions", ["read"])

    base = old_build(
        agent_identity_block=sys_p,
        agent_name=agent_name,
        soul_facts=[],
        agent_tools_block=f"Perms: {', '.join(perms)}",
        agent_security_block="Systemdateien+Gefährliche Patterns geblockt. Shell via Whitelist.",
    )

    # Post-Processing (gleiche Defaults wie im Test-Setup)
    return _apply_post_processing(
        base, agent_name,
        settings={
            "obedience": 3, "personality": 3, "response_style": 3, "risk_tolerance": 3,
            "active_preset": "",
        },
    )


# Default-Runtime-Settings für den Test (simuliert die Test-Umgebung).
# active_preset="" damit kein Preset-Prefix geladen wird — der Test prüft
# strukturelle Äquivalenz, nicht das Preset-Verhalten. Phase 3 kann das ändern.
DEFAULT_RUNTIME = {
    "obedience": 3,
    "personality": 3,
    "response_style": 3,
    "risk_tolerance": 3,
    "active_preset": "",
}


def _mock_all_fetchers():
    """Mockt alle 7 Fetcher — gibt deterministische Strings zurück."""
    from gnom_hub.core.prompt import context as ctx
    return patch.multiple(
        ctx,
        _get_worker_stats=lambda a, c: f"[KONTEXT:worker_stats]\nMOCK {a}",
        _get_open_contexts=lambda a, c: f"[KONTEXT:open_contexts]\nMOCK {a}",
        _get_active_rules=lambda a, c: f"[KONTEXT:active_rules]\nMOCK {a}",
        _get_workspace_summary=lambda a, c: f"[KONTEXT:workspace_summary]\nMOCK {a}",
        _get_chat_history_tail=lambda a, c: f"[KONTEXT:chat_history_tail]\nMOCK {a}",
        _get_soul_facts=lambda a, c: f"[KONTEXT:soul_facts]\nMOCK {a}",
        _get_evolution_rules=lambda a, c: f"[KONTEXT:evolution_rules]\nMOCK {a}",
    )


def _load_new_identity(agent_name: str) -> str:
    """Lädt identity aus config/agents/<name>.json."""
    path = CONFIG_DIR / f"{agent_name}.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    return cfg["identity"]


# ── Tests ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("agent_name", ALL_AGENTS)
def test_identity_text_preserved(agent_name: str) -> None:
    """Phase-1-Constraint: identity in JSON == sys_prompt in agent_definitions.py.

    Schlägt fehl wenn jemand den identity-Text im JSON anders geschrieben hat
    als das Original — das wäre ein Behavior-Change in Phase 1.
    """
    old_identity = AGENT_DEFINITIONS[agent_name.lower()]["sys_prompt"]
    new_identity = _load_new_identity(agent_name)
    assert old_identity.strip() == new_identity.strip(), (
        f"{agent_name}: identity-Text weicht ab zwischen AGENT_DEFINITIONS und config/agents/{agent_name}.json. "
        f"Phase-1-Constraint verletzt. Diff manuell prüfen."
    )


@pytest.mark.parametrize("agent_name", ALL_AGENTS)
def test_prompt_structure(agent_name: str) -> None:
    """Beide Builder müssen die gleichen Struktur-Sections haben."""
    with _mock_all_fetchers():
        old_prompt = _build_old_prompt(agent_name)
        new_prompt = new_build(agent_name, message_text="", runtime_settings=DEFAULT_RUNTIME)

    # Identity-Header (Anfang) und Identity-Closing (im Body — Post-Processing
    # hängt danach an, also nicht mehr am Ende)
    assert old_prompt.startswith(f"⚠️ DU BIST {agent_name}"), f"{agent_name}: alter Prompt ohne Header"
    assert new_prompt.startswith(f"⚠️ DU BIST {agent_name}"), f"{agent_name}: neuer Prompt ohne Header"
    assert f"⚠️ DU BIST {agent_name} UND NUR {agent_name}" in old_prompt, \
        f"{agent_name}: alter Prompt ohne Identity-Closing"
    assert f"⚠️ DU BIST {agent_name} UND NUR {agent_name}" in new_prompt, \
        f"{agent_name}: neuer Prompt ohne Identity-Closing"

    # Kernsections
    for section in ["[VERHALTEN]", "[TOOLS]", "[SICHERHEIT]"]:
        assert section in old_prompt, f"{agent_name}: alter Prompt ohne {section}"
        assert section in new_prompt, f"{agent_name}: neuer Prompt ohne {section}"

    # Post-Processing Output (sollte in beiden vorhanden sein)
    assert "=== OBEDIENCE: BALANCED ===" in old_prompt, f"{agent_name}: alter Prompt ohne Obedience"
    assert "=== OBEDIENCE: BALANCED ===" in new_prompt, f"{agent_name}: neuer Prompt ohne Obedience"


@pytest.mark.parametrize("agent_name", ALL_AGENTS)
def test_allowed_contexts_respected(agent_name: str) -> None:
    """Context-Dispatcher darf nur Blöcke liefern die in allowed_contexts stehen."""
    cfg = json.loads((CONFIG_DIR / f"{agent_name}.json").read_text(encoding="utf-8"))
    allowed = set(cfg.get("allowed_contexts", []))

    with _mock_all_fetchers():
        prompt = new_build(agent_name, message_text="", runtime_settings=DEFAULT_RUNTIME)

    # Jeder [KONTEXT:*] Block im Prompt muss in allowed_contexts sein
    import re
    found_blocks = set(re.findall(r"\[KONTEXT:(\w+)\]", prompt))

    # Erlaubte Blöcke die im Prompt vorkommen sollten: alle aus allowed
    expected = allowed & {"worker_stats", "open_contexts", "active_rules", "workspace_summary", "chat_history_tail", "soul_facts", "evolution_rules"}
    # _get_active_rules self-filtert nach Rolle (Watchdog/Security only),
    # also darf ein in allowed_listings stehender Block leer sein wenn Rolle nicht passt
    if "active_rules" in expected and not any(x in agent_name.lower() for x in ("watchdog", "security")):
        expected.discard("active_rules")

    assert found_blocks == expected, (
        f"{agent_name}: Context-Blocks im Prompt ({found_blocks}) weichen ab von "
        f"allowed_contexts ({allowed}). Erwartet: {expected}."
    )


@pytest.mark.parametrize("agent_name", ALL_AGENTS)
def test_save_golden_diff(agent_name: str) -> None:
    """Speichert beide Prompts als Golden-Files für visuellen Diff."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    with _mock_all_fetchers():
        old_prompt = _build_old_prompt(agent_name)
        new_prompt = new_build(agent_name, message_text="", runtime_settings=DEFAULT_RUNTIME)

    out = {
        "agent": agent_name,
        "old_chars": len(old_prompt),
        "new_chars": len(new_prompt),
        "diff_chars": len(new_prompt) - len(old_prompt),
        "old": old_prompt,
        "new": new_prompt,
    }
    (GOLDEN_DIR / f"diff_{agent_name}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_summary_report(capsys) -> None:
    """Generiert einen Zusammenfassungs-Report für alle 8 Agents."""
    rows = []
    with _mock_all_fetchers():
        for name in ALL_AGENTS:
            old = _build_old_prompt(name)
            new = new_build(name, message_text="", runtime_settings=DEFAULT_RUNTIME)
            rows.append((name, len(old), len(new), len(new) - len(old)))

    out_lines = ["\n=== Golden Diff Summary ==="]
    out_lines.append(f"  {'Agent':<14} {'Old':>7} {'New':>7} {'Diff':>7}")
    for name, o, n, d in rows:
        out_lines.append(f"  {name:<14} {o:>7} {n:>7} {d:>+7}")
    out_lines.append("")
    print("\n".join(out_lines))


def test_generalag_has_no_active_rules() -> None:
    """Spezialtest: GeneralAG darf KEINE active_rules bekommen (Rollenbruch)."""
    with _mock_all_fetchers():
        prompt = new_build("GeneralAG", message_text="", runtime_settings=DEFAULT_RUNTIME)
    assert "[KONTEXT:active_rules]" not in prompt, (
        "GeneralAG hat active_rules im Prompt — das widerspricht dem statischen "
        "Prompt ('weiß nichts von System-Agents') und ist ein Rollenbruch."
    )


def test_watchdog_has_active_rules() -> None:
    """Spezialtest: WatchdogAG bekommt active_rules (rollengefiltert)."""
    with patch(
        "gnom_hub.core.prompt.context._get_active_rules",
        return_value="[KONTEXT:active_rules]\nMOCK path rule",
    ):
        prompt = new_build("WatchdogAG", message_text="", runtime_settings=DEFAULT_RUNTIME)
    assert "[KONTEXT:active_rules]" in prompt
