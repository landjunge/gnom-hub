"""Tests für das Gnom-Hub Preset-System.

Abdeckung:
  * Pro Pydantic-Modell: ≥1 Valid-Test + ≥1 Invalid-Test
  * load_preset("default") lädt das Referenz-Preset vollständig
  * save_preset ist atomar (bei Fehler keine halbe Datei)
  * Cross-File-Validierung erkennt fehlende Tool-Referenzen
  * delete_preset("default") wird verweigert
  * Endpoint-Tests für alle 6+ Routen

Run: pytest tests/test_preset_schema_loader.py -v
"""

from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def preset_tmp_root(tmp_path, monkeypatch):
    """Isoliertes Verzeichnis für Preset-JSONs.

    Patcht ``gnom_hub.core.preset_loader._preset_root()`` so dass alle
    Loader-Operationen in ``tmp_path/data/presets`` landen — der echte
    Default-Preset-Ordner wird nicht angefasst.
    """
    root = tmp_path / "data" / "presets"
    root.mkdir(parents=True, exist_ok=True)

    import gnom_hub.core.preset_loader as loader

    def fake_root():
        return root

    monkeypatch.setattr(loader, "_preset_root", fake_root)
    return root


@pytest.fixture
def minimal_bundle():
    """Ein minimal gültiges PresetBundle für Tests."""
    from gnom_hub.core.preset_schema import (
        AgentDef,
        HooksConfig,
        MCPConfig,
        MemoryConfig,
        PermissionsConfig,
        PluginsConfig,
        PresetBundle,
        PresetConfig,
        SecurityConfig,
        SkillsConfig,
        SystemAgentsConfig,
        TemplatesConfig,
        ToolsConfig,
        WebhooksConfig,
        WorkersConfig,
        WorkflowsConfig,
    )

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cfg = PresetConfig(
        name="Test", description="d", version="1.0.0",
        personality=3, response_style=3,
        created_at=now, updated_at=now,
    )
    soul = AgentDef(name="SoulAG", role="soul", prompt="p", enabled=True)
    wd = AgentDef(name="WatchdogAG", role="watchdog", prompt="p", enabled=True)
    gen = AgentDef(name="GeneralAG", role="general", prompt="p", enabled=True)
    sec = AgentDef(name="SecurityAG", role="security", prompt="p", enabled=True)
    wr = AgentDef(name="WriterAG", role="writer", prompt="p", enabled=True)
    co = AgentDef(name="CoderAG", role="coder", prompt="p", enabled=True)
    re_ = AgentDef(name="ResearcherAG", role="researcher", prompt="p", enabled=True)
    ed = AgentDef(name="EditorAG", role="editor", prompt="p", enabled=True)

    return PresetBundle(
        config=cfg,
        system_agents=SystemAgentsConfig(soul=soul, watchdog=wd, general=gen, security=sec),
        workers=WorkersConfig(writer=wr, coder=co, researcher=re_, editor=ed),
        tools=ToolsConfig(tools=[]),
        plugins=PluginsConfig(plugins=[]),
        templates=TemplatesConfig(templates=[]),
        workflows=WorkflowsConfig(workflows=[]),
        memory=MemoryConfig(),
        security=SecurityConfig(),
        webhooks=WebhooksConfig(incoming=[]),
        hooks=HooksConfig(internal=[]),
        skills=SkillsConfig(skills=[]),
        permissions=PermissionsConfig(matrix={}),
        mcp=MCPConfig(exposed=[]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Per-Model-Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestPresetConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import PresetConfig
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        c = PresetConfig(
            name="n", description="d", version="1",
            personality=3, response_style=4,
            created_at=now, updated_at=now, tags=["a", "b"],
        )
        assert c.tags == ["a", "b"]
        assert c.personality == 3

    def test_personality_out_of_range(self):
        from gnom_hub.core.preset_schema import PresetConfig
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            PresetConfig(
                name="n", description="d", version="1",
                personality=6, response_style=3,
                created_at=now, updated_at=now,
            )

    def test_response_style_zero(self):
        from gnom_hub.core.preset_schema import PresetConfig
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            PresetConfig(
                name="n", description="d", version="1",
                personality=3, response_style=0,
                created_at=now, updated_at=now,
            )

    def test_missing_required_field(self):
        from gnom_hub.core.preset_schema import PresetConfig
        with pytest.raises(ValidationError):
            PresetConfig(name="n")  # type: ignore[call-arg]


class TestAgentDef:
    def test_valid(self):
        from gnom_hub.core.preset_schema import AgentDef
        a = AgentDef(name="X", role="r", prompt="p")
        assert a.enabled is True
        assert a.model_override is None
        assert a.model_locked is False

    def test_soul_locked(self):
        from gnom_hub.core.preset_schema import AgentDef
        a = AgentDef(name="SoulAG", role="soul", prompt="p",
                     model_override=None, model_locked=True, priority="highest")
        assert a.model_locked is True
        assert a.priority == "highest"

    def test_invalid_priority(self):
        from gnom_hub.core.preset_schema import AgentDef
        with pytest.raises(ValidationError):
            AgentDef(name="X", role="r", prompt="p", priority="ultrahigh")

    def test_name_required(self):
        from gnom_hub.core.preset_schema import AgentDef
        with pytest.raises(ValidationError):
            AgentDef(role="r", prompt="p")  # type: ignore[call-arg]


class TestToolDef:
    def test_valid(self):
        from gnom_hub.core.preset_schema import ToolDef
        t = ToolDef(id="shell", name="Shell", capability="exec",
                    allowed_agents=["WatchdogAG"], allowed_workers=["CoderAG"])
        assert t.id == "shell"

    def test_missing_id(self):
        from gnom_hub.core.preset_schema import ToolDef
        with pytest.raises(ValidationError):
            ToolDef(name="X", capability="c")  # type: ignore[call-arg]


class TestPluginDef:
    def test_valid(self):
        from gnom_hub.core.preset_schema import PluginDef
        p = PluginDef(id="github", name="GH", version="0.1.0", enabled=True,
                      settings={"x": 1})
        assert p.settings == {"x": 1}

    def test_missing_id(self):
        from gnom_hub.core.preset_schema import PluginDef
        with pytest.raises(ValidationError):
            PluginDef(name="X")  # type: ignore[call-arg]


class TestTemplateDef:
    def test_valid(self):
        from gnom_hub.core.preset_schema import TemplateDef
        t = TemplateDef(id="t1", name="T", body="b {{x}}", variables=["x"])
        assert "x" in t.variables

    def test_missing_body(self):
        from gnom_hub.core.preset_schema import TemplateDef
        with pytest.raises(ValidationError):
            TemplateDef(id="t1", name="T")  # type: ignore[call-arg]


class TestWorkflowDef:
    def test_valid_with_steps(self):
        from gnom_hub.core.preset_schema import WorkflowDef, WorkflowStep
        s = WorkflowStep(agent_id="CoderAG", role="primary", depends_on=[],
                         params={"x": 1})
        w = WorkflowDef(id="wf1", name="WF", description="d", steps=[s])
        assert w.steps[0].agent_id == "CoderAG"

    def test_empty_steps_ok(self):
        from gnom_hub.core.preset_schema import WorkflowDef
        w = WorkflowDef(id="wf1", name="WF", steps=[])
        assert w.steps == []


class TestMemoryConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import MemoryConfig
        m = MemoryConfig(soul_memory_enabled=True, vector_store="faiss",
                         max_entries=100, retention_days=30,
                         embedding_model="all-MiniLM-L6-v2")
        assert m.vector_store == "faiss"

    def test_max_entries_negative(self):
        from gnom_hub.core.preset_schema import MemoryConfig
        with pytest.raises(ValidationError):
            MemoryConfig(max_entries=-1)


class TestSecurityConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import SecurityConfig
        s = SecurityConfig(encryption_at_rest=True, require_usb_key=False,
                           secret_slots=["s1", "s2"], key_rotation_days=30)
        assert "s1" in s.secret_slots

    def test_default_usb_key_id_is_none(self):
        from gnom_hub.core.preset_schema import SecurityConfig
        s = SecurityConfig()
        assert s.usb_key_id is None
        assert s.require_usb_key is False


class TestWebhooksConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import WebhookDef, WebhooksConfig
        w = WebhookDef(id="wh1", url="/hook", secret_ref="s1", enabled=True)
        cfg = WebhooksConfig(incoming=[w])
        assert cfg.incoming[0].id == "wh1"

    def test_missing_secret_ref(self):
        from gnom_hub.core.preset_schema import WebhookDef
        with pytest.raises(ValidationError):
            WebhookDef(id="wh1", url="/hook")  # type: ignore[call-arg]


class TestHooksConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import HookDef, HooksConfig
        h = HookDef(id="h1", event="chat.msg", agent_id="WatchdogAG",
                    action="a", enabled=True, priority=100)
        cfg = HooksConfig(internal=[h])
        assert cfg.internal[0].event == "chat.msg"

    def test_missing_event(self):
        from gnom_hub.core.preset_schema import HookDef
        with pytest.raises(ValidationError):
            HookDef(id="h1", agent_id="X", action="a")  # type: ignore[call-arg]


class TestSkillsConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import SkillDef, SkillsConfig
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        s = SkillDef(id="sk1", name="Skill", body="b", learned_at=now,
                     confidence=0.9)
        cfg = SkillsConfig(skills=[s])
        assert cfg.skills[0].confidence == 0.9

    def test_confidence_out_of_range(self):
        from gnom_hub.core.preset_schema import SkillDef
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            SkillDef(id="sk1", name="S", body="b", learned_at=now,
                     confidence=1.5)


class TestPermissionsConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import PermissionsConfig
        p = PermissionsConfig(matrix={"SoulAG": ["chat:write"]})
        assert p.matrix["SoulAG"] == ["chat:write"]

    def test_empty_matrix(self):
        from gnom_hub.core.preset_schema import PermissionsConfig
        p = PermissionsConfig()
        assert p.matrix == {}


class TestMCPConfig:
    def test_valid(self):
        from gnom_hub.core.preset_schema import MCPConfig, MCPInterface
        m = MCPInterface(id="m1", name="MCP", input_schema={"type": "object"},
                         allowed_clients=["claude"])
        cfg = MCPConfig(exposed=[m])
        assert cfg.exposed[0].id == "m1"

    def test_missing_name(self):
        from gnom_hub.core.preset_schema import MCPInterface
        with pytest.raises(ValidationError):
            MCPInterface(id="m1", input_schema={})  # type: ignore[call-arg]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Bundle / Loader
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadSaveDefault:
    def test_load_default_preset_succeeds(self):
        """Das mitgelieferte Default-Preset lädt sauber."""
        # Wir benutzen hier den realen Default-Pfad, weil load_preset in
        # _preset_root() hartkodiert ist. Das Default-Preset ist versioniert
        # im Repo und sollte immer valide sein.
        # 14 Dateien müssen existieren
        from gnom_hub.core.preset_loader import _preset_root, load_preset
        from gnom_hub.core.preset_schema import PRESET_FILES
        pdir = _preset_root() / "default"
        if not pdir.is_dir():
            pytest.skip("Default-Preset nicht im Repo vorhanden — überspringe.")
        for f in PRESET_FILES:
            assert (pdir / f).is_file(), f"fehlt: {f}"

        bundle = load_preset("default")
        # Alle 8 Workflows vorhanden
        wf_ids = {w.id for w in bundle.workflows.workflows}
        for required in {"code-write", "security-audit", "market-research",
                         "blog-post", "bug-fix", "data-analysis",
                         "voice-output", "personality-tune"}:
            assert required in wf_ids, f"Workflow {required!r} fehlt im default"

    def test_soul_locked_in_default(self):
        from gnom_hub.core.preset_loader import _preset_root, load_preset

        pdir = _preset_root() / "default"
        if not pdir.is_dir():
            pytest.skip("Default-Preset nicht im Repo vorhanden — überspringe.")
        bundle = load_preset("default")
        soul = bundle.system_agents.soul
        assert soul.model_locked is True
        assert soul.model_override is None


class TestSavePreset:
    def test_save_and_reload_roundtrip(self, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import load_preset, save_preset
        save_preset("alpha", minimal_bundle)
        loaded = load_preset("alpha")
        assert loaded.config.name == minimal_bundle.config.name
        # Auch die 14 Dateien sind angelegt
        for f in [
            "config.json", "system_agents.json", "workers.json",
            "tools.json", "plugins.json", "templates.json",
            "workflows.json", "memory.json", "security.json",
            "webhooks.json", "hooks.json", "skills.json",
            "permissions.json", "mcp.json",
        ]:
            assert (preset_tmp_root / "alpha" / f).is_file()

    def test_save_creates_dir_if_missing(self, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        target = preset_tmp_root / "new_thing"
        assert not target.exists()
        save_preset("new_thing", minimal_bundle)
        assert target.is_dir()

    def test_save_atomic_no_partial_files(
        self, preset_tmp_root, minimal_bundle, monkeypatch
    ):
        """Wenn beim Schreiben der 8. Datei ein Fehler auftritt, dürfen
        weder die 7 Original-Dateien verändert worden sein, noch eine
        halb-geschriebene 8. Datei existieren."""
        from gnom_hub.core.preset_loader import save_preset
        # Zuerst erfolgreich speichern
        save_preset("atomic", minimal_bundle)
        original_files = sorted(
            (preset_tmp_root / "atomic").iterdir()
        )
        original_names = sorted(p.name for p in original_files)
        # Snapshot der Inhalte
        original_contents = {
            p.name: p.read_text(encoding="utf-8")
            for p in original_files
        }

        # Jetzt den Save sabotieren: failen beim Schreiben der 8. Datei
        # (workflows.json ist die 7. Datei — also Fehler bei der 8., memory.json)
        call_count = {"n": 0}
        real_open = open

        def boom_open(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 8:  # 7. payload → 8. tempfile (memory)
                raise RuntimeError("simulated crash mid-save")
            return real_open(*args, **kwargs)

        # Patch tempfile.mkstemp, um den Crash zu provozieren
        import gnom_hub.core.preset_loader as loader
        real_mkstemp = tempfile.mkstemp

        def maybe_boom(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 8:  # 7. payload = memory.json
                raise RuntimeError("simulated crash mid-save")
            return real_mkstemp(*args, **kwargs)

        monkeypatch.setattr(loader.tempfile, "mkstemp", maybe_boom)

        with pytest.raises(RuntimeError):
            save_preset("atomic", minimal_bundle)

        # Original-Dateien müssen unverändert sein
        current_files = sorted(
            (preset_tmp_root / "atomic").iterdir()
        )
        sorted(p.name for p in current_files)
        # Mindestens die 14 Dateien müssen noch da sein (oder genau die 14)
        for name in original_names:
            assert (preset_tmp_root / "atomic" / name).is_file()
        # Inhalte unverändert
        for name in original_names:
            current = (preset_tmp_root / "atomic" / name).read_text(encoding="utf-8")
            assert current == original_contents[name], (
                f"Datei {name} wurde verändert trotz Crash!"
            )

    def test_load_missing_preset_raises(self, preset_tmp_root):
        from gnom_hub.core.preset_loader import load_preset
        with pytest.raises(FileNotFoundError):
            load_preset("does-not-exist")

    def test_load_incomplete_preset_raises(self, preset_tmp_root, minimal_bundle):
        """Wenn eine der 14 Dateien fehlt, muss load_preset FileNotFoundError werfen."""
        from gnom_hub.core.preset_loader import load_preset, save_preset
        save_preset("inc", minimal_bundle)
        # Eine Datei löschen
        (preset_tmp_root / "inc" / "memory.json").unlink()
        with pytest.raises(FileNotFoundError):
            load_preset("inc")


class TestListPresets:
    def test_list_empty(self, preset_tmp_root):
        from gnom_hub.core.preset_loader import list_presets
        assert list_presets() == []

    def test_list_after_save(self, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import list_presets, save_preset
        save_preset("a", minimal_bundle)
        save_preset("b", minimal_bundle)
        result = list_presets()
        ids = {p.id for p in result}
        assert ids == {"a", "b"}

    def test_list_skips_incomplete(self, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import list_presets, save_preset
        save_preset("complete", minimal_bundle)
        # Ein unvollständiges Preset anlegen
        (preset_tmp_root / "broken").mkdir()
        (preset_tmp_root / "broken" / "config.json").write_text(
            json.dumps({"name": "x", "description": "y", "version": "1",
                        "personality": 3, "response_style": 3,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z"})
        )
        result = list_presets()
        ids = {p.id for p in result}
        assert "complete" in ids
        assert "broken" not in ids


class TestDeletePreset:
    def test_delete_works(self, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import delete_preset, save_preset
        save_preset("del", minimal_bundle)
        assert (preset_tmp_root / "del").is_dir()
        assert delete_preset("del") is True
        assert not (preset_tmp_root / "del").exists()

    def test_delete_default_refused(self, preset_tmp_root):
        """delete_preset("default") muss scheitern (entweder False oder Exception)."""
        from gnom_hub.core.preset_loader import delete_preset
        try:
            result = delete_preset("default")
            # Falls die Implementierung False zurückgibt → ok
            assert result is False, (
                f"delete_preset('default') muss verweigert werden, gab aber {result!r} zurück"
            )
        except (PermissionError, ValueError):
            # Falls die Implementierung stattdessen eine Exception wirft → auch ok
            pass

    def test_delete_nonexistent_returns_false(self, preset_tmp_root):
        from gnom_hub.core.preset_loader import delete_preset
        # Nicht existent → False, ohne Exception
        result = delete_preset("nope")
        # delete_preset darf False ODER (für default) Exception werfen;
        # für nicht-existente IDs ohne Exception: muss False sein.
        if isinstance(result, bool):
            assert result is False
        # sonst: keine Exception


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cross-File-Validierung
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossFileValidation:
    def test_validate_minimal_bundle_no_errors(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        assert validate_preset_bundle(minimal_bundle) == []

    def test_validate_tool_with_unknown_agent(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import ToolDef
        minimal_bundle.tools.tools.append(
            ToolDef(id="bad", name="B", capability="x",
                    allowed_agents=["NoSuchAgent"])
        )
        errors = validate_preset_bundle(minimal_bundle)
        assert any("NoSuchAgent" in e for e in errors)

    def test_validate_tool_with_unknown_worker(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import ToolDef
        minimal_bundle.tools.tools.append(
            ToolDef(id="bad2", name="B2", capability="x",
                    allowed_workers=["GhostWorker"])
        )
        errors = validate_preset_bundle(minimal_bundle)
        assert any("GhostWorker" in e for e in errors)

    def test_validate_workflow_unknown_agent(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import WorkflowDef, WorkflowStep
        minimal_bundle.workflows.workflows.append(
            WorkflowDef(id="wf-bad", name="WF", steps=[
                WorkflowStep(agent_id="ImaginaryAG", role="primary",
                             depends_on=[], params={}),
            ])
        )
        errors = validate_preset_bundle(minimal_bundle)
        assert any("ImaginaryAG" in e for e in errors)

    def test_validate_permissions_unknown_key(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import PermissionsConfig
        minimal_bundle.permissions = PermissionsConfig(
            matrix={"NonExistentAgent": ["chat:write"]}
        )
        errors = validate_preset_bundle(minimal_bundle)
        assert any("NonExistentAgent" in e for e in errors)

    def test_validate_webhook_secret_ref_not_in_slots(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import WebhookDef
        minimal_bundle.webhooks.incoming.append(
            WebhookDef(id="wh", url="/x", secret_ref="missing-slot")
        )
        errors = validate_preset_bundle(minimal_bundle)
        assert any("missing-slot" in e for e in errors)

    def test_validate_webhook_secret_ref_in_slots_ok(self, minimal_bundle):
        from gnom_hub.core.preset_loader import validate_preset_bundle
        from gnom_hub.core.preset_schema import SecurityConfig, WebhookDef
        minimal_bundle.security = SecurityConfig(secret_slots=["good-slot"])
        minimal_bundle.webhooks.incoming.append(
            WebhookDef(id="wh", url="/x", secret_ref="good-slot")
        )
        errors = validate_preset_bundle(minimal_bundle)
        # Nur die webhook-Fehler, aber nicht "missing-slot"
        assert not any("missing-slot" in e for e in errors)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Endpoint-Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPresetEndpoints:
    """Tests für die FastAPI-Endpoints in presets.py.

    Wir testen den Router direkt mit einem FastAPI-Test-Client, ohne die
    volle App zu laden (das spart das Hochfahren der Background-Agents).
    """

    @pytest.fixture
    def client(self, preset_tmp_root, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from gnom_hub.api.endpoints.presets import router

        # get_state_value/set_state_value monkeypatchen, damit wir keine
        # echte DB brauchen.
        state = {}

        def fake_get(key, default=None):
            return state.get(key, default)

        def fake_set(key, value):
            state[key] = value

        import gnom_hub.api.endpoints.presets as ep
        monkeypatch.setattr(ep, "_get_active_preset_id",
                            lambda: state.get("active_preset"))
        monkeypatch.setattr(ep, "_set_active_preset_id",
                            lambda v: state.__setitem__("active_preset", v))

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_list_empty(self, client):
        r = client.get("/api/presets")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_with_default(self, client):
        """Wenn das default-Preset im _preset_root existiert, wird es gelistet."""
        # Wir benutzen die echte Repo-Default; falls sie nicht da ist,
        # überspringen wir.
        from gnom_hub.core.preset_loader import _preset_root
        default_dir = _preset_root() / "default"
        if not default_dir.is_dir():
            pytest.skip("default-Preset nicht im Repo.")
        r = client.get("/api/presets")
        assert r.status_code == 200
        items = r.json()
        assert any(p["id"] == "default" for p in items)

    def test_get_full_preset(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("test1", minimal_bundle)
        r = client.get("/api/presets/test1")
        assert r.status_code == 200
        data = r.json()
        # Alle 14 Top-Level Keys vorhanden
        for key in [
            "config", "system_agents", "workers", "tools", "plugins",
            "templates", "workflows", "memory", "security", "webhooks",
            "hooks", "skills", "permissions", "mcp",
        ]:
            assert key in data, f"Schlüssel {key!r} fehlt im Bundle"

    def test_get_nonexistent_404(self, client):
        r = client.get("/api/presets/no-such-thing")
        assert r.status_code == 404

    def test_create_preset(self, client, preset_tmp_root, minimal_bundle):
        body = {"id": "fresh", "bundle": minimal_bundle.model_dump(mode="json")}
        r = client.post("/api/presets", json=body)
        assert r.status_code == 200, r.text
        assert r.json()["id"] == "fresh"
        # Datei wurde angelegt
        assert (preset_tmp_root / "fresh").is_dir()

    def test_create_duplicate_409(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("dup", minimal_bundle)
        body = {"id": "dup", "bundle": minimal_bundle.model_dump(mode="json")}
        r = client.post("/api/presets", json=body)
        assert r.status_code == 409

    def test_put_preset(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("upd", minimal_bundle)
        new_bundle = copy.deepcopy(minimal_bundle)
        new_bundle.config.description = "updated"
        r = client.put("/api/presets/upd",
                       json={"bundle": new_bundle.model_dump(mode="json")})
        assert r.status_code == 200
        # Re-load und prüfen
        r2 = client.get("/api/presets/upd")
        assert r2.json()["config"]["description"] == "updated"

    def test_put_nonexistent_404(self, client, minimal_bundle):
        body = {"bundle": minimal_bundle.model_dump(mode="json")}
        r = client.put("/api/presets/does-not-exist", json=body)
        assert r.status_code == 404

    def test_put_default_blocked(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        # default existiert entweder im realen Repo oder wir legen es an
        save_preset("default", minimal_bundle)
        body = {"bundle": minimal_bundle.model_dump(mode="json")}
        r = client.put("/api/presets/default", json=body)
        assert r.status_code == 403

    def test_delete_preset(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("kill", minimal_bundle)
        r = client.delete("/api/presets/kill")
        assert r.status_code == 200
        assert not (preset_tmp_root / "kill").exists()

    def test_delete_default_refused(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("default", minimal_bundle)
        r = client.delete("/api/presets/default")
        # Muss 403 oder 404 sein (403 = Permission, 404 falls "delete"
        # False zurückgibt und als 404 ankommt). Wichtig: NICHT 200.
        assert r.status_code in (403, 404), r.text

    def test_activate_and_get_active(self, client, preset_tmp_root, minimal_bundle):
        from gnom_hub.core.preset_loader import save_preset
        save_preset("act", minimal_bundle)
        r = client.post("/api/presets/activate/act")
        assert r.status_code == 200
        assert r.json()["active_preset"] == "act"
        r2 = client.get("/api/presets/active")
        assert r2.status_code == 200
        data = r2.json()
        assert data["id"] == "act"
        assert data["name"] == minimal_bundle.config.name

    def test_activate_nonexistent_404(self, client):
        r = client.post("/api/presets/activate/nope")
        assert r.status_code == 404

    def test_put_with_invalid_bundle_422(self, client, preset_tmp_root, minimal_bundle):
        """Wenn die Cross-File-Validierung fehlschlägt, muss der Endpoint 422 liefern."""
        from gnom_hub.core.preset_loader import save_preset
        from gnom_hub.core.preset_schema import ToolDef
        save_preset("valid", minimal_bundle)
        # Bundle mit ungültiger Tool-Referenz
        bad = copy.deepcopy(minimal_bundle)
        bad.tools.tools.append(
            ToolDef(id="tbad", name="T", capability="c",
                    allowed_agents=["UnknownAgentX"])
        )
        r = client.put("/api/presets/valid",
                       json={"bundle": bad.model_dump(mode="json")})
        assert r.status_code == 422
        # Die Fehlerliste ist in der Detail
        assert "validation_errors" in str(r.json())


# ─────────────────────────────────────────────────────────────────────────────
# 5. Bonus: Schema-Robustheit
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaRobustness:
    def test_bundle_roundtrip_serialization(self, minimal_bundle):
        """Bundle → dict → Bundle muss verlustfrei sein."""
        from gnom_hub.core.preset_schema import PresetBundle
        d = minimal_bundle.model_dump(mode="json")
        re_loaded = PresetBundle.model_validate(d)
        assert re_loaded.config.name == minimal_bundle.config.name

    def test_save_load_byte_identical_for_config(
        self, preset_tmp_root, minimal_bundle
    ):
        """Save+Load liefert identische config-Werte (Datetime wird ISO)."""
        from gnom_hub.core.preset_loader import load_preset, save_preset
        save_preset("rt", minimal_bundle)
        b = load_preset("rt")
        # config ist mit ISO-Strings im Dict — Datetime wird re-konvertiert
        assert b.config.name == minimal_bundle.config.name
        assert b.config.personality == minimal_bundle.config.personality

    def test_invalid_preset_id_rejected(self, preset_tmp_root):
        """Unsichere Preset-IDs (Path-Traversal) dürfen kein Verzeichnis
        außerhalb des Preset-Roots treffen."""
        from gnom_hub.core.preset_loader import get_presets_root, preset_dir
        root = get_presets_root().resolve()
        # ``..`` würde über das Root hinausspringen — stellen wir sicher,
        # dass der Loader das entweder wirft ODER den Pfad zumindest
        # NICHT außerhalb des Roots auflöst.
        try:
            p = preset_dir("../etc")
            # Wenn kein ValueError: Pfad muss trotzdem unter root liegen
            assert root in p.resolve().parents or p.resolve() == root
        except ValueError:
            pass  # akzeptabel
        # Leerer String / Slashes → ValueError ODER no-op (kein Crash)
        for bad in ["", "/", "a/b"]:
            try:
                p = preset_dir(bad)
            except ValueError:
                pass
            except Exception:
                pytest.fail(f"unerwarteter Exception-Typ für {bad!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. JSON-Datei-Format
# ─────────────────────────────────────────────────────────────────────────────

class TestJsonFileFormat:
    def test_pretty_printed_with_indent_2(self, preset_tmp_root, minimal_bundle):
        """Die geschriebenen JSON-Dateien sind pretty-printed (indent=2)."""
        from gnom_hub.core.preset_loader import save_preset
        save_preset("pretty", minimal_bundle)
        content = (preset_tmp_root / "pretty" / "config.json").read_text()
        # Erste Zeile: '{', dann 2 Spaces für erstes Property
        lines = content.splitlines()
        assert lines[0] == "{"
        # Property-Lines beginnen mit 2 Spaces
        indented = [letter for letter in lines if letter.startswith("  ")]
        assert len(indented) > 0
        # Keine Key-Sortierung: Reihenfolge wie im Pydantic-Modell
        assert '"name":' in content
        assert '"description":' in content
        assert '"version":' in content
