"""Tests für die Vollständigkeit des Default-Presets.

Prüft:
- Alle 14 Sub-Modelle sind nicht leer.
- SoulAG hat `model_locked == true`, `model_override is None`,
  `priority == "highest"`, und einen 4-Absatz-Prompt.
- Mindestens 8 Workflows sind definiert.
- Die Permissions-Matrix deckt alle 8 Agenten ab.
- Alle Tool-Referenzen in tools.json sind auflösbar (jede referenzierte
  Agent-/Worker-ID existiert in system_agents oder workers).
- Cross-File-Validierung läuft fehlerfrei durch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo-Root auf den Pfad setzen, damit `gnom_hub.core.*` importierbar ist
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gnom_hub.core.preset_loader import (  # noqa: E402
    load_preset,
    list_presets,
    validate_preset_bundle,
)
from gnom_hub.core.preset_schema import PRESET_FILES  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def default_bundle():
    """Lade das Default-Bundle einmal pro Modul."""
    return load_preset("default")


@pytest.fixture(scope="module")
def default_validation_errors(default_bundle):
    """Validierungs-Errors des Default-Bundles."""
    return validate_preset_bundle(default_bundle)


# ---------------------------------------------------------------------------
# 1) Datei-Vollständigkeit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", PRESET_FILES)
def test_default_preset_has_all_14_files(tmp_path, filename):
    """Alle 14 JSON-Dateien existieren unter data/presets/default/."""
    preset_dir = _REPO_ROOT / "data" / "presets" / "default"
    assert preset_dir.is_dir(), f"Preset-Ordner fehlt: {preset_dir}"
    assert (preset_dir / filename).is_file(), f"Datei fehlt: {filename}"


def test_all_14_sub_models_load(default_bundle):
    """Alle 14 Sub-Modelle des Bundles sind nicht leer."""
    bundle = default_bundle

    # config.json
    assert bundle.config.name.strip()
    assert bundle.config.description.strip()
    assert bundle.config.version.strip()
    assert 1 <= bundle.config.personality <= 5
    assert 1 <= bundle.config.response_style <= 5

    # system_agents.json
    assert bundle.system_agents.soul.name == "SoulAG"
    assert bundle.system_agents.watchdog.name == "WatchdogAG"
    assert bundle.system_agents.general.name == "GeneralAG"
    assert bundle.system_agents.security.name == "SecurityAG"
    for sa in (
        bundle.system_agents.soul,
        bundle.system_agents.watchdog,
        bundle.system_agents.general,
        bundle.system_agents.security,
    ):
        assert sa.prompt.strip(), f"{sa.name} hat leeren Prompt"
        assert sa.role.strip(), f"{sa.name} hat leere Rolle"

    # workers.json
    assert bundle.workers.writer.name == "WriterAG"
    assert bundle.workers.coder.name == "CoderAG"
    assert bundle.workers.researcher.name == "ResearcherAG"
    assert bundle.workers.editor.name == "EditorAG"
    for w in (
        bundle.workers.writer,
        bundle.workers.coder,
        bundle.workers.researcher,
        bundle.workers.editor,
    ):
        assert w.prompt.strip(), f"{w.name} hat leeren Prompt"

    # tools.json
    assert len(bundle.tools.tools) >= 8, (
        f"Erwartet ≥8 Tools, gefunden {len(bundle.tools.tools)}"
    )

    # plugins.json
    assert len(bundle.plugins.plugins) >= 4

    # templates.json
    assert len(bundle.templates.templates) >= 6

    # workflows.json
    assert len(bundle.workflows.workflows) == 8

    # memory.json
    assert bundle.memory.vector_store == "faiss"
    assert bundle.memory.embedding_model == "all-MiniLM-L6-v2"
    assert bundle.memory.max_entries >= 1000
    assert bundle.memory.retention_days >= 1
    assert bundle.memory.soul_memory_enabled is True

    # security.json
    assert bundle.security.encryption_at_rest is True
    assert isinstance(bundle.security.allowed_api_origins, list)

    # webhooks.json
    assert len(bundle.webhooks.incoming) >= 1

    # hooks.json
    assert len(bundle.hooks.internal) >= 3

    # skills.json
    assert len(bundle.skills.skills) >= 4

    # permissions.json
    assert len(bundle.permissions.matrix) == 8

    # mcp.json
    assert len(bundle.mcp.exposed) >= 1


# ---------------------------------------------------------------------------
# 2) SoulAG Binding
# ---------------------------------------------------------------------------


def test_soulag_is_model_locked(default_bundle):
    """SoulAG hat model_locked=true (UI darf nicht überschreiben)."""
    soul = default_bundle.system_agents.soul
    assert soul.model_locked is True


def test_soulag_has_null_model_override(default_bundle):
    """SoulAG hat model_override=null (Router entscheidet anhand Stage-5)."""
    soul = default_bundle.system_agents.soul
    assert soul.model_override is None


def test_soulag_has_highest_priority(default_bundle):
    """SoulAG hat priority='highest' (Router sortiert SoulAG über alle anderen)."""
    soul = default_bundle.system_agents.soul
    assert soul.priority == "highest"


def test_soulag_prompt_has_four_paragraphs(default_bundle):
    """SoulAG-Prompt deckt 4 Absätze: Identität, Persönlichkeit, Memory, Stage-5."""
    prompt = default_bundle.system_agents.soul.prompt
    paragraphs = [p.strip() for p in prompt.split("\n\n") if p.strip()]
    assert len(paragraphs) >= 4, (
        f"Erwartet ≥4 Absätze für SoulAG-Prompt, gefunden {len(paragraphs)}"
    )
    joined = " ".join(paragraphs).lower()
    # Identität
    assert "soulag" in joined
    # Persönlichkeit
    assert "persönlichkeit" in joined or "personlichkeit" in joined
    # Memory-Hoheit
    assert "memory" in joined
    # Stage-5-Bindung
    assert "stage" in joined and "5" in joined
    # Stärkster Agent
    assert "stärkste" in joined or "staerkste" in joined or "stärkste agent" in joined
    # Endgültige Entscheidungen
    assert (
        "endgültige" in joined
        or "endgueltige" in joined
        or "endgültige persönlichkeits" in joined
    )


def test_other_system_agents_have_two_paragraphs(default_bundle):
    """WatchdogAG, GeneralAG, SecurityAG haben 2-Absatz-Prompts."""
    for agent in (
        default_bundle.system_agents.watchdog,
        default_bundle.system_agents.general,
        default_bundle.system_agents.security,
    ):
        paragraphs = [p for p in agent.prompt.split("\n\n") if p.strip()]
        assert len(paragraphs) >= 2, (
            f"{agent.name} hat nur {len(paragraphs)} Absätze, erwartet ≥2"
        )


# ---------------------------------------------------------------------------
# 3) Workflows
# ---------------------------------------------------------------------------


def test_workflows_count_is_eight(default_bundle):
    """Genau 8 Workflows im Default-Preset."""
    assert len(default_bundle.workflows.workflows) == 8


def test_workflows_have_required_scenarios(default_bundle):
    """Die 8 Pflicht-Szenarien sind enthalten."""
    wf_ids = {w.id for w in default_bundle.workflows.workflows}
    required = {
        "code-write",
        "security-audit",
        "market-research",
        "blog-post",
        "bug-fix",
        "data-analysis",
        "voice-output",
        "personality-tune",
    }
    missing = required - wf_ids
    assert not missing, f"Fehlende Workflows: {sorted(missing)}"


def test_workflows_reference_existing_agents(default_bundle, default_validation_errors):
    """Jeder Workflow-Step zeigt auf einen existierenden Agent."""
    bundle = default_bundle
    agent_names = set(bundle.all_agent_ids)
    for wf in bundle.workflows.workflows:
        assert wf.id
        assert wf.name
        for step in wf.steps:
            assert step.agent_id in agent_names, (
                f"workflow '{wf.id}' step agent_id='{step.agent_id}' unbekannt"
            )
    assert not default_validation_errors, (
        f"validate_preset_bundle liefert Fehler: {default_validation_errors}"
    )


# ---------------------------------------------------------------------------
# 4) Permissions-Matrix
# ---------------------------------------------------------------------------


def test_permissions_matrix_covers_all_eight_agents(default_bundle):
    """Permissions-Matrix enthält Einträge für alle 8 Agenten."""
    expected = {
        "SoulAG",
        "WatchdogAG",
        "GeneralAG",
        "SecurityAG",
        "WriterAG",
        "CoderAG",
        "ResearcherAG",
        "EditorAG",
    }
    actual = set(default_bundle.permissions.matrix.keys())
    assert expected == actual, (
        f"Erwartet genau diese Agenten in Matrix: {sorted(expected)}, "
        f"gefunden: {sorted(actual)}"
    )


def test_permissions_matrix_values_are_capability_lists(default_bundle):
    """Jeder Eintrag ist eine nicht-leere Liste von Capabilities."""
    for agent_id, caps in default_bundle.permissions.matrix.items():
        assert isinstance(caps, list), f"{agent_id} Caps sind keine Liste"
        assert caps, f"{agent_id} hat leere Caps-Liste"
        for c in caps:
            assert isinstance(c, str) and c, f"{agent_id} hat ungültige Cap: {c!r}"


# ---------------------------------------------------------------------------
# 5) Tool-Referenzen auflösbar
# ---------------------------------------------------------------------------


def test_tool_references_resolvable(default_bundle):
    """Alle in tools.json referenzierten Agent-/Worker-IDs existieren."""
    bundle = default_bundle
    agent_names = set(bundle.all_agent_ids)
    for tool in bundle.tools.tools:
        for ref in tool.allowed_agents + tool.allowed_workers:
            assert ref in agent_names, (
                f"tool '{tool.id}' referenziert unbekannten agent/worker '{ref}'"
            )


def test_tool_count_meets_spec(default_bundle):
    """Tools-Anzahl liegt im spezifizierten Bereich 8-12."""
    n = len(default_bundle.tools.tools)
    assert 8 <= n <= 12, f"Tools-Anzahl {n} außerhalb 8-12"


# ---------------------------------------------------------------------------
# 6) Cross-File-Validierung
# ---------------------------------------------------------------------------


def test_cross_file_validation_passes(default_validation_errors):
    """validate_preset_bundle liefert keine Fehler."""
    assert default_validation_errors == [], (
        f"Cross-File-Validierung liefert Fehler: {default_validation_errors}"
    )


# ---------------------------------------------------------------------------
# 7) Preset-Listing
# ---------------------------------------------------------------------------


def test_default_preset_is_listed():
    """list_presets() enthält den Default-Preset."""
    summaries = list_presets()
    ids = {s.id for s in summaries}
    assert "default" in ids, f"default nicht in list_presets(): {ids}"


# ---------------------------------------------------------------------------
# 8) Worker model_family_preference
# ---------------------------------------------------------------------------


def test_coder_has_qwen_or_deepseek_coder_preference(default_bundle):
    """CoderAG bevorzugt Qwen-/DeepSeek-Coder-Familien."""
    coder = default_bundle.workers.coder
    dumped = coder.model_dump()
    pref = dumped.get("model_family_preference") or []
    assert isinstance(pref, list) and pref, "CoderAG hat keine model_family_preference"
    keywords = {"qwen", "deepseek-coder", "deepseek_coder", "codestral"}
    assert any(any(k in p.lower() for k in keywords) for p in pref), (
        f"CoderAG model_family_preference={pref} enthält keine Code-Familien"
    )


def test_all_workers_have_model_family_preference(default_bundle):
    """Alle 4 Worker haben model_family_preference gesetzt."""
    for name, w in (
        ("writer", default_bundle.workers.writer),
        ("coder", default_bundle.workers.coder),
        ("researcher", default_bundle.workers.researcher),
        ("editor", default_bundle.workers.editor),
    ):
        pref = w.model_dump().get("model_family_preference")
        assert isinstance(pref, list) and pref, (
            f"{name} hat keine model_family_preference: {pref!r}"
        )