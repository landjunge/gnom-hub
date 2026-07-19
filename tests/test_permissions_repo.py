"""Tests für security_permissions-Workflow (Phase 2 #4 der Cross-Check-Synthese).

Schließt die Phantom-Tabelle: security_permissions war im Schema definiert aber
hatte keinen Code-Pfad der je hinein schrieb. SecurityAG's Kernrolle
"Verzeichnisse/Dateien freigeben" war damit funktionslos.

Enforcement: path_validator._safe + check_permission (directory Prefix-Match).
"""
import os

import pytest

from gnom_hub.db import (
    check_permission,
    grant_permission,
    list_permissions_for_agent,
    revoke_permission,
)

# ── DB-Layer Tests ──────────────────────────────────────────────────────


class TestPermissionsRepo:
    """Direkter Test der grant/revoke/check/list-Funktionen."""

    def test_grant_then_check_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission(
            resource_type="directory",
            resource_path="/tmp/foo",  # noqa: S108 — Test-Fixture.
            granted_to="CoderAG",
            reason="test",
        )
        assert check_permission("CoderAG", "/tmp/foo") is True  # noqa: S108 — Test-Fixture.

    def test_grant_invalid_type_raises(self):
        with pytest.raises(ValueError, match="resource_type"):
            grant_permission(
                resource_type="invalid",
                resource_path="/tmp/foo",  # noqa: S108 — Test-Fixture.
                granted_to="CoderAG",
            )

    def test_grant_empty_path_raises(self):
        with pytest.raises(ValueError, match="resource_path"):
            grant_permission(
                resource_type="directory",
                resource_path="",
                granted_to="CoderAG",
            )

    def test_grant_idempotent_updates_reason(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission("file", "/x.py", "CoderAG", reason="first")
        grant_permission("file", "/x.py", "CoderAG", reason="second")
        perms = list_permissions_for_agent("CoderAG")
        assert len(perms) == 1
        assert perms[0]["reason"] == "second"

    def test_revoke_marks_inactive(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission("directory", "/y", "WriterAG")
        assert check_permission("WriterAG", "/y") is True
        n = revoke_permission("/y", "WriterAG")
        assert n == 1
        assert check_permission("WriterAG", "/y") is False

    def test_all_wildcard_matches_anyone(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission("directory", "/shared", "all", reason="global")
        assert check_permission("CoderAG", "/shared") is True
        assert check_permission("EditorAG", "/shared") is True

    def test_expired_perm_does_not_match(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        # Setze expires_at in Vergangenheit
        grant_permission(
            "directory", "/old", "CoderAG",
            expires_at="2020-01-01T00:00:00Z",
        )
        assert check_permission("CoderAG", "/old") is False

    def test_directory_grant_matches_child_path(self, tmp_path, monkeypatch):
        """Directory-Grant auf /proj erlaubt /proj/src/foo.py (Prefix-Match)."""
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()
        root = tmp_path / "proj"
        child = root / "src" / "foo.py"
        root.mkdir()
        (root / "src").mkdir()
        child.write_text("x")
        grant_permission("directory", str(root), "CoderAG", reason="prefix-test")
        assert check_permission("CoderAG", str(child)) is True
        assert check_permission("CoderAG", str(root)) is True
        # Sibling außerhalb des Grants
        other = tmp_path / "other" / "x.py"
        other.parent.mkdir()
        other.write_text("y")
        assert check_permission("CoderAG", str(other)) is False


# ── _safe Enforcement ───────────────────────────────────────────────────


class TestSafeGrantEnforcement:
    """path_validator._safe + security_permissions: outside-workspace nur mit Grant/godmode."""

    def test_outside_workspace_blocked_without_grant(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        ws.mkdir()
        outside = tmp_path / "outside" / "secret.py"
        outside.parent.mkdir()
        outside.write_text("nope")

        import gnom_hub.core.config as cfg
        import gnom_hub.core.security.path_validator as pv
        monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)

        # Non-empty write perms — früher truthy-Bug, jetzt blocken
        result = pv._safe(str(ws), str(outside), perms=["read", "write"], agent_name="CoderAG")
        assert result is None

    def test_outside_workspace_allowed_with_grant(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.schema import create_tables
        create_tables()

        ws = tmp_path / "workspace"
        ws.mkdir()
        outside_dir = tmp_path / "allowed"
        outside_dir.mkdir()
        target = outside_dir / "app.py"
        target.write_text("ok")
        grant_permission("directory", str(outside_dir), "CoderAG", reason="enforcement-test")

        import gnom_hub.core.config as cfg
        import gnom_hub.core.security.path_validator as pv
        monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)

        result = pv._safe(str(ws), str(target), perms=["read", "write"], agent_name="CoderAG")
        assert result is not None
        assert os.path.realpath(result) == os.path.realpath(str(target))

    def test_godmode_allows_outside_without_grant(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        ws.mkdir()
        outside = tmp_path / "sec" / "x.py"
        outside.parent.mkdir()
        outside.write_text("sec")

        import gnom_hub.core.config as cfg
        import gnom_hub.core.security.path_validator as pv
        monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)

        result = pv._safe(
            str(ws), str(outside),
            perms=["read", "write", "run", "godmode"],
            agent_name="SecurityAG",
        )
        assert result is not None

    def test_workspace_still_free_without_grant(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        ws.mkdir()
        target = ws / "notes.md"
        target.write_text("ok")

        import gnom_hub.core.config as cfg
        import gnom_hub.core.security.path_validator as pv
        monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)

        result = pv._safe(str(ws), "notes.md", perms=["read", "write"], agent_name="CoderAG")
        assert result is not None


# ── Action-Handler Tests ────────────────────────────────────────────────


class TestGrantPermAction:
    """Integration-Test: [GRANT_PERM:] Tag in Agent-Output."""

    def test_grant_perm_from_securityag_succeeds(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: type=directory agent=CoderAG path=/tmp/test_grant reason=unit-test]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "write", "run", "godmode", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        assert "Permission granted" in result
        assert "CoderAG" in result
        assert "/tmp/test_grant" in result  # noqa: S108 — Test-Fixture.

    def test_grant_perm_from_non_securityag_denied(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: agent=CoderAG path=/tmp/x]"
        agent = {"name": "CoderAG", "role": "coder"}
        perms = ["read", "write", "run"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        assert "keine DB_WRITE-Berechtigung" in result

    def test_grant_perm_missing_args_denied(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: agent=CoderAG]"  # path missing
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        assert "fehlt" in result

    def test_revoke_perm_from_securityag(self):
        from gnom_hub.agents.actions import action_handlers
        # First grant
        ans1 = "[GRANT_PERM: agent=WriterAG path=/tmp/x_revoke]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        action_handlers.process_actions(ans1, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        # Then revoke
        ans2 = "[REVOKE_PERM: agent=WriterAG path=/tmp/x_revoke]"
        result = action_handlers.process_actions(ans2, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        assert "revoked" in result.lower() or "deaktiviert" in result.lower()

    def test_list_perms_returns_empty_or_grants(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[LIST_PERMS: agent=NoSuchAgent]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")  # noqa: S108 — Test-Fixture.
        assert "Permissions for NoSuchAgent" in result
        assert "keine aktiven" in result