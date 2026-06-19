"""
tests/test_workspace_config.py
Gnom-Hub Test-Suite — Unit Tests für die Workspace-Pfad-Konfiguration
(Hot-reload-fähig via state["workspace_dir_override"])

Getestet wird:
  - Config.workspace_dir() löst zur Laufzeit den State-Override auf
  - GET /api/workspace/config liefert aktuellen + Default-Pfad
  - PUT /api/workspace/config validiert (absolut, nicht in /etc /usr /var
    /proc /sys /boot /lib /sbin /bin, beschreibbar)
  - POST /api/workspace/config/reset stellt Default wieder her

Run: pytest tests/test_workspace_config.py -v
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


# ============================================================================
# 1. Config.workspace_dir() — Hot-Reload via State
# ============================================================================

class TestConfigWorkspaceDirHotReload:
    """`Config.workspace_dir()` muss den via State gesetzten Override lesen,
    nicht nur den Modul-Initialwert."""

    def test_default_is_user_home_gnom_workspace(self, monkeypatch):
        """Default ist ~/gnom-Workspace, nicht /workspace/.../gnom_workspace."""
        import importlib
        # Neu laden mit leerem HOME-Override
        monkeypatch.setenv("GNOM_HUB_WORKSPACE", "")
        # Force re-import so default_workspace neu berechnet wird
        import gnom_hub.core.config as cfg_mod
        importlib.reload(cfg_mod)
        from pathlib import Path
        expected_default = str(Path.home() / "gnom-Workspace")
        # Vergleich gegen str(), weil Path == str False ist.
        assert str(cfg_mod.default_workspace) == expected_default

    def test_state_override_is_returned(self):
        """Wenn `state["workspace_dir_override"]` gesetzt ist, gibt
        `Config.workspace_dir()` genau diesen Pfad zurück."""
        from gnom_hub.core.config import Config
        from gnom_hub.db import set_state_value

        custom = tempfile.mkdtemp(prefix="ws-test-")
        set_state_value("workspace_dir_override", custom)
        try:
            assert str(Config.workspace_dir()) == str(Path(custom).resolve())
        finally:
            set_state_value("workspace_dir_override", "")

    def test_state_empty_string_falls_back_to_default(self):
        """Leerer State-Wert (Reset) fällt auf Default zurück.

        Wenn weder State-Override noch Env-Override gesetzt sind UND der
        Modul-Initialwert Path("") ist (durch leeren Env-Var), darf
        workspace_dir() nicht '.' zurückgeben.
        """
        from gnom_hub.core.config import Config, WORKSPACE_DIR
        from gnom_hub.db import set_state_value

        set_state_value("workspace_dir_override", "")
        # Wenn der Modul-Initialwert ungültig ist (z.B. leerer String),
        # fällt der Helper auf HOME/gnom-Workspace zurück.
        if str(WORKSPACE_DIR) == ".":
            expected = str(Path.home() / "gnom-Workspace")
            assert str(Config.workspace_dir()) == expected
        else:
            assert str(Config.workspace_dir()) == str(WORKSPACE_DIR.resolve())

    def test_db_failure_falls_back_to_default(self, monkeypatch):
        """DB-Lookup-Failure darf nicht crashen — Fallback auf Modul-Default."""
        from gnom_hub.core.config import Config, WORKSPACE_DIR
        from gnom_hub.db import state_repo

        def boom(self, key, default=None):
            raise RuntimeError("simulierter DB-Ausfall")

        monkeypatch.setattr(state_repo.SQLiteStateRepository, "get_value", boom)
        # Sollte nicht crashen — Fallback entweder auf WORKSPACE_DIR
        # oder HOME/gnom-Workspace wenn WORKSPACE_DIR ungültig.
        result = Config.workspace_dir()
        assert isinstance(result, Path)
        assert str(result) != "."
        assert result.is_absolute() or str(result).startswith(str(Path.home()))


# ============================================================================
# 2. API-Endpoint GET /api/workspace/config
# ============================================================================

class TestGetWorkspaceConfig:
    """GET liefert aktuellen Pfad + Default + is_default-Flag."""

    def test_returns_current_path_and_default(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        client = TestClient(app)

        r = client.get("/api/workspace/config")
        assert r.status_code == 200
        data = r.json()
        assert "path" in data and "default" in data and "is_default" in data
        assert data["default"] == str(Path.home() / "gnom-Workspace")

    def test_default_flag_true_when_no_override(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        from gnom_hub.db import set_state_value
        client = TestClient(app)

        set_state_value("workspace_dir_override", "")
        r = client.get("/api/workspace/config")
        # is_default hängt vom effektiven Pfad ab — kann True sein wenn
        # Config.workspace_dir() == ~/gnom-Workspace.
        data = r.json()
        expected_default = str(Path.home() / "gnom-Workspace")
        if data["path"] == expected_default:
            assert data["is_default"] is True
        else:
            # Effektiver Pfad weicht ab (z.B. WORKSPACE_DIR Modul-Init)
            assert data["is_default"] is False


# ============================================================================
# 3. API-Endpoint PUT /api/workspace/config
# ============================================================================

class TestPutWorkspaceConfig:
    """PUT setzt den Workspace-Pfad; validiert absolute Pfade außerhalb
    von System-Verzeichnissen."""

    def test_valid_path_returns_200(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        from gnom_hub.db import set_state_value
        client = TestClient(app)

        custom = tempfile.mkdtemp(prefix="ws-ok-")
        try:
            r = client.put("/api/workspace/config", json={"path": custom})
            assert r.status_code == 200, r.text
            assert r.json()["ok"] is True
            assert r.json()["path"] == str(Path(custom).resolve())
        finally:
            set_state_value("workspace_dir_override", "")

    def test_home_relative_path_expanded(self):
        """~/foo wird zu HOME/foo expandiert."""
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        from gnom_hub.db import set_state_value
        client = TestClient(app)

        target = os.path.expanduser("~/gnom-ws-test-home")
        try:
            r = client.put("/api/workspace/config", json={"path": target})
            assert r.status_code == 200, r.text
            assert str(Path(r.json()["path"])) == str(Path(target).resolve())
        finally:
            set_state_value("workspace_dir_override", "")
            if os.path.exists(target):
                os.rmdir(target)

    def test_empty_path_rejected(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        client = TestClient(app)
        r = client.put("/api/workspace/config", json={"path": ""})
        assert r.status_code == 400
        assert "leer" in r.json()["detail"].lower()

    def test_relative_path_rejected(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        client = TestClient(app)
        r = client.put("/api/workspace/config", json={"path": "relative/subdir"})
        assert r.status_code == 400
        assert "absolut" in r.json()["detail"].lower()

    @pytest.mark.parametrize("blocked", [
        "/etc/test",
        "/usr/local/share",
        "/var/log",
        "/proc/1",
        "/sys/kernel",
        "/boot/grub",
        "/lib/modules",
        "/sbin",
        "/bin",
    ])
    def test_system_paths_rejected(self, blocked):
        """Pfade unter /etc, /usr, /var etc. werden abgelehnt."""
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        client = TestClient(app)
        r = client.put("/api/workspace/config", json={"path": blocked})
        assert r.status_code == 400, f"{blocked} sollte abgelehnt werden"
        assert "nicht erlaubt" in r.json()["detail"].lower() or "system-pfad" in r.json()["detail"].lower()

    def test_path_is_actually_created(self):
        """Wenn der Pfad nicht existiert, wird er angelegt."""
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        from gnom_hub.db import set_state_value
        client = TestClient(app)

        parent = tempfile.mkdtemp(prefix="ws-parent-")
        target = os.path.join(parent, "neuer-unterordner")
        try:
            assert not os.path.exists(target)
            r = client.put("/api/workspace/config", json={"path": target})
            assert r.status_code == 200
            assert os.path.isdir(target), "Verzeichnis sollte angelegt worden sein"
        finally:
            set_state_value("workspace_dir_override", "")
            import shutil
            shutil.rmtree(parent, ignore_errors=True)


# ============================================================================
# 4. API-Endpoint POST /api/workspace/config/reset
# ============================================================================

class TestResetWorkspaceConfig:
    """Reset stellt den Default wieder her."""

    def test_reset_clears_override(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        from gnom_hub.db import set_state_value
        client = TestClient(app)

        # Set custom first
        custom = tempfile.mkdtemp(prefix="ws-reset-")
        set_state_value("workspace_dir_override", custom)

        # Reset
        r = client.post("/api/workspace/config/reset")
        assert r.status_code == 200
        # Nach Reset muss der Default zurück sein (HOME/gnom-Workspace)
        expected_default = str(Path.home() / "gnom-Workspace")
        assert r.json()["path"] == expected_default
        assert r.json()["is_default"] is True

        # Cleanup
        os.rmdir(custom)

    def test_reset_is_idempotent(self):
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app
        client = TestClient(app)

        r1 = client.post("/api/workspace/config/reset")
        r2 = client.post("/api/workspace/config/reset")
        assert r1.status_code == r2.status_code == 200


# ============================================================================
# 5. Hot-Reload-Verhalten: Aufrufer sehen den neuen Pfad sofort
# ============================================================================

class TestHotReload:
    """Nach PUT müssen Aufrufer, die Config.workspace_dir() benutzen,
    den neuen Pfad sofort sehen — ohne Neustart."""

    def test_config_workspace_dir_picks_up_change(self):
        from gnom_hub.core.config import Config
        from gnom_hub.db import set_state_value
        from fastapi.testclient import TestClient
        from gnom_hub.api.app import app

        client = TestClient(app)
        custom = tempfile.mkdtemp(prefix="ws-hot-")
        try:
            r = client.put("/api/workspace/config", json={"path": custom})
            assert r.status_code == 200

            # Direkt nach PUT — Config.workspace_dir() zeigt custom
            assert str(Config.workspace_dir()) == str(Path(custom).resolve())
        finally:
            set_state_value("workspace_dir_override", "")
            os.rmdir(custom)