"""Tests für security_permissions-Workflow (Phase 2 #4 der Cross-Check-Synthese).

Schließt die Phantom-Tabelle: security_permissions war im Schema definiert aber
hatte keinen Code-Pfad der je hinein schrieb. SecurityAG's Kernrolle
"Verzeichnisse/Dateien freigeben" war damit funktionslos.
"""
import pytest
from gnom_hub.db import (
    grant_permission, revoke_permission, check_permission,
    list_permissions_for_agent, VALID_RESOURCE_TYPES,
)


# ── DB-Layer Tests ──────────────────────────────────────────────────────


class TestPermissionsRepo:
    """Direkter Test der grant/revoke/check/list-Funktionen."""

    def test_grant_then_check_returns_true(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.connection import get_db_conn
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission(
            resource_type="directory",
            resource_path="/tmp/foo",
            granted_to="CoderAG",
            reason="test",
        )
        assert check_permission("CoderAG", "/tmp/foo") is True

    def test_grant_invalid_type_raises(self):
        with pytest.raises(ValueError, match="resource_type"):
            grant_permission(
                resource_type="invalid",
                resource_path="/tmp/foo",
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
        from gnom_hub.db.connection import get_db_conn
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
        from gnom_hub.db.connection import get_db_conn
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
        from gnom_hub.db.connection import get_db_conn
        from gnom_hub.db.schema import create_tables
        create_tables()
        grant_permission("directory", "/shared", "all", reason="global")
        assert check_permission("CoderAG", "/shared") is True
        assert check_permission("EditorAG", "/shared") is True

    def test_expired_perm_does_not_match(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "test.db"))
        from gnom_hub.core.config import Config
        Config.DB_PATH = str(tmp_path / "test.db")
        from gnom_hub.db.connection import get_db_conn
        from gnom_hub.db.schema import create_tables
        create_tables()
        # Setze expires_at in Vergangenheit
        grant_permission(
            "directory", "/old", "CoderAG",
            expires_at="2020-01-01T00:00:00Z",
        )
        assert check_permission("CoderAG", "/old") is False


# ── Action-Handler Tests ────────────────────────────────────────────────


class TestGrantPermAction:
    """Integration-Test: [GRANT_PERM:] Tag in Agent-Output."""

    def test_grant_perm_from_securityag_succeeds(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: type=directory agent=CoderAG path=/tmp/test_grant reason=unit-test]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "write", "run", "godmode", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")
        assert "Permission granted" in result
        assert "CoderAG" in result
        assert "/tmp/test_grant" in result

    def test_grant_perm_from_non_securityag_denied(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: agent=CoderAG path=/tmp/x]"
        agent = {"name": "CoderAG", "role": "coder"}
        perms = ["read", "write", "run"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")
        assert "keine DB_WRITE-Berechtigung" in result

    def test_grant_perm_missing_args_denied(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[GRANT_PERM: agent=CoderAG]"  # path missing
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")
        assert "fehlt" in result

    def test_revoke_perm_from_securityag(self):
        from gnom_hub.agents.actions import action_handlers
        # First grant
        ans1 = "[GRANT_PERM: agent=WriterAG path=/tmp/x_revoke]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        action_handlers.process_actions(ans1, agent, perms, bs_mode=False, wd="/tmp")
        # Then revoke
        ans2 = "[REVOKE_PERM: agent=WriterAG path=/tmp/x_revoke]"
        result = action_handlers.process_actions(ans2, agent, perms, bs_mode=False, wd="/tmp")
        assert "revoked" in result.lower() or "deaktiviert" in result.lower()

    def test_list_perms_returns_empty_or_grants(self):
        from gnom_hub.agents.actions import action_handlers
        ans = "[LIST_PERMS: agent=NoSuchAgent]"
        agent = {"name": "SecurityAG", "role": "security"}
        perms = ["read", "db_write"]
        result = action_handlers.process_actions(ans, agent, perms, bs_mode=False, wd="/tmp")
        assert "Permissions for NoSuchAgent" in result
        assert "keine aktiven" in result