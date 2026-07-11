"""Tests for path_validator.py — Security-Boundary-Checks.

Abdeckung für die 3 Fixes vom Permissions-Audit:
  #1 `_safe()` off-by-one: Sibling-Dir-Escape (`<ws>-evil`) wird geblockt
  #2 `SYSTEM_PATHS` + workspace-interne Pfade: src/gnom_hub, config, scripts,
     run.sh, index.html, .env werden geblockt
  #3 `_is_high_risk_exec`: rm -rf auf workspace-interne Pfade wird high-risk
"""

from __future__ import annotations

import os

import pytest

# ─── Helpers ────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_workspace(tmp_path, monkeypatch):
    """Setzt WORKSPACE_DIR auf ein tmp-Verzeichnis mit canonical test-Layout.

    Layout:
        <ws>/
            src/gnom_hub/   (sollte geblockt werden — System-Pfad)
            config/         (sollte geblockt werden — System-Pfad)
            scripts/        (sollte geblockt werden — System-Pfad)
            run.sh          (sollte geblockt werden — System-Pfad)
            index.html      (sollte geblockt werden — System-Pfad)
            .env            (sollte geblockt werden — System-Pfad)
            notes.md        (sollte erlaubt sein — User-Workspace)

    Wichtig: pytest's tmp_path liegt auf macOS unter
    `/private/var/folders/...` → matcht SYSTEM_PATHS["/private/var"].
    Wir monkey-patchen SYSTEM_PATHS deshalb auf eine Minimal-Liste,
    damit die Tests portabel sind und nur die workspace-internen Pfade
    geprüft werden.
    """
    ws = tmp_path / "workspace"
    (ws / "src" / "gnom_hub").mkdir(parents=True)
    (ws / "config").mkdir()
    (ws / "scripts").mkdir()
    (ws / "run.sh").write_text("#!/bin/bash\n")
    (ws / "index.html").write_text("<html></html>")
    (ws / ".env").write_text("SECRET=x")
    (ws / "notes.md").write_text("ok")

    # WORKSPACE_DIR Modul-Attribut patchen BEVOR path_validator es zieht
    import gnom_hub.core.config as cfg
    monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
    # path_validator hat `from gnom_hub.core.config import WORKSPACE_DIR`
    # → das ist ein Modul-Level-Binding, also auch dort patchen.
    import gnom_hub.core.security.path_validator as pv
    monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)
    # SYSTEM_PATHS komplett leeren — sonst matcht jeder macOS-tmp_path
    # unter /private/var → /var (realpath), und /var ist in SYSTEM_PATHS.
    # Wir testen hier nur die workspace-internen Pfade aus
    # `_workspace_system_paths()`, die hardcoded OS-Pfade sind in
    # `test_real_os_system_paths_still_blocked` separat abgedeckt.
    monkeypatch.setattr(pv, "SYSTEM_PATHS", [])

    return ws


# ─── Fix #1: _safe() off-by-one ─────────────────────────────────────────────

class TestSafeOffByOne:
    """Sibling-Directory-Escape (`<workspace>-evil/...`) muss geblockt werden."""

    def test_blocks_sibling_directory_with_same_prefix(self, tmp_path, monkeypatch):
        """Pfad `/.../workspace-evil/foo` darf NICHT als im-Workspace gelten."""
        # Workspace = /tmp/.../workspace
        ws = tmp_path / "workspace"
        ws.mkdir()
        # Sibling mit gleichem Prefix:
        sibling = tmp_path / "workspace-evil"
        sibling.mkdir()
        target = sibling / "secret.txt"

        import gnom_hub.core.config as cfg
        import gnom_hub.core.security.path_validator as pv
        monkeypatch.setattr(cfg, "WORKSPACE_DIR", ws)
        monkeypatch.setattr(pv, "WORKSPACE_DIR", ws)

        result = pv._safe(str(ws), str(target), perms=False)
        assert result is None, (
            f"Sibling-Dir escape should be blocked, got {result!r} "
            f"(workspace={ws}, target={target})"
        )

    def test_allows_actual_workspace_file(self, fake_workspace):
        """Pfad innerhalb des Workspace wird durchgelassen."""
        target = fake_workspace / "notes.md"
        import gnom_hub.core.security.path_validator as pv
        result = pv._safe(str(fake_workspace), str(target), perms=False)
        assert result is not None
        assert os.path.realpath(result) == os.path.realpath(str(target))

    def test_blocks_parent_directory_traversal(self, fake_workspace):
        """`../etc/passwd` darf nicht in den Workspace aufgelöst werden."""
        import gnom_hub.core.security.path_validator as pv
        # Würde ohne off-by-one-Fix zu /tmp/.../etc/passwd werden → nicht in ws
        result = pv._safe(str(fake_workspace), "../../etc/passwd", perms=False)
        # Result ist None wenn NICHT im Workspace — das ist gewollt
        # (Pfad ist außerhalb, würde aber von `is_system_path` zusätzlich
        # gefangen wenn er nach /etc auflöst)
        if result is not None:
            real = os.path.realpath(result)
            assert real.startswith(str(fake_workspace) + os.sep) or real == str(fake_workspace), \
                f"Parent traversal should resolve outside workspace, got {real}"


# ─── Fix #2: SYSTEM_PATHS + workspace-interne Pfade ────────────────────────

class TestSystemPaths:
    """OS-level System-Pfade sind geschützt. Workspace-interne Substrings
    ('src/gnom_hub', 'config', 'scripts', 'run.sh', 'index.html', '.env')
    sind NICHT geschützt — die sind user-eigenes Territory (User-Mandat
    2026-07-02 13:42 'Workspace-frei'). Bug-Fix 2026-07-11."""

    @pytest.mark.parametrize("subpath", [
        "src/gnom_hub",
        "config",
        "scripts",
        "run.sh",
        "index.html",
        ".env",
    ])
    def test_workspace_internal_path_NOT_blocked(self, fake_workspace, subpath):
        """Workspace-interne Substrings ('src/gnom_hub', 'config', 'scripts', ...)
        sind user-eigenes Territory. WatchdogAG-Prompt (v9.0): 'KEIN Blocken
        von scripts/, tests/, normalen Workspace-Pfaden'. Fix 2026-07-11: die
        _workspace_system_paths()-Funktion gibt jetzt eine leere Liste zurück,
        damit Worker-Writes im User-Workspace nicht fälschlich blockiert werden.
        """
        import gnom_hub.core.security.path_validator as pv
        target = str(fake_workspace / subpath)
        assert pv.is_system_path(target) is False, (
            f"{subpath!r} should NOT be blocked — it's user workspace (WatchdogAG-Vertrag v9.0)"
        )

    def test_user_workspace_file_allowed(self, fake_workspace):
        import gnom_hub.core.security.path_validator as pv
        assert pv.is_system_path(str(fake_workspace / "notes.md")) is False
        assert pv.is_system_path(str(fake_workspace / "notes.md" / "sub")) is False

    def test_real_os_system_paths_still_blocked(self, monkeypatch):
        """Bestehende /etc, /usr, /var etc. müssen weiterhin funktionieren.

        Hier testen wir die ECHTE SYSTEM_PATHS-Liste (nicht das Fixture,
        weil das SYSTEM_PATGS für Portabilität monkey-patched).
        """
        import gnom_hub.core.security.path_validator as pv
        for sp in ["/etc", "/usr", "/var", "/private/etc", "/private/var"]:
            assert pv.is_system_path(sp) is True, f"{sp} should be blocked"

    def test_subpath_under_workspace_internal_NOT_blocked(self, fake_workspace):
        """Subpfade UNTER workspace-internen Verzeichnissen ('src/gnom_hub',
        'config', etc.) sind NICHT mehr blockiert — das war der Bug.
        User-Report 2026-07-11 'er blockt alles' — Fix: nur OS-level Pfade
        blockieren, nicht User-Workspace.
        """
        import gnom_hub.core.security.path_validator as pv
        target = str(fake_workspace / "src" / "gnom_hub" / "core" / "x.py")
        assert pv.is_system_path(target) is False, (
            f"{target} should NOT be blocked — User-Workspace, not OS-system"
        )

    def test_nonexistent_path_in_workspace_NOT_blocked(self, fake_workspace):
        """Auch nicht-existierende Pfade im User-Workspace werden NICHT blockiert.
        War vorher falsch als 'blocked' getestet — Bug-Fix 2026-07-11.
        """
        import gnom_hub.core.security.path_validator as pv
        target = str(fake_workspace / "config" / "future-file.yml")
        assert pv.is_system_path(target) is False, (
            f"{target} should NOT be blocked — User-Workspace, even if non-existent"
        )


# ─── Fix #3: _is_high_risk_exec rm -rf ─────────────────────────────────────

class TestHighRiskExecPaths:
    """rm -rf auf workspace-interne Pfade muss high-risk flag setzen."""

    def test_rm_rf_on_config_dir_is_high_risk(self, fake_workspace):
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        config_path = str(fake_workspace / "config" / "routing.txt")
        # `rm -rf <config-path>` → Args haben rm, -rf, dann der Pfad
        args = ["rm", "-rf", config_path]
        assert _is_high_risk_exec("rm", args) is True, (
            "rm -rf on config/ should be high-risk, got False"
        )

    def test_rm_rf_on_scripts_is_high_risk(self, fake_workspace):
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        scripts_path = str(fake_workspace / "scripts")
        args = ["rm", "-rf", scripts_path]
        assert _is_high_risk_exec("rm", args) is True

    def test_rm_rf_on_index_html_is_high_risk(self, fake_workspace):
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        target = str(fake_workspace / "index.html")
        args = ["rm", "-rf", target]
        assert _is_high_risk_exec("rm", args) is True

    def test_rm_rf_on_normal_workspace_file_not_flagged(self, monkeypatch):
        """rm -rf auf Files UNTER `/var/...` IST per Definition high-risk
        (siehe `_is_high_risk_exec` Zeile 337: `startswith('/var')`).

        Daher können wir auf macOS (wo pytest's tmp_path unter /private/var
        liegt) NICHT testen dass `rm -rf <tmp>/notes.md` safe ist — der
        resolved Path matcht /var.

        Statt dessen: monkey-patched HOME-Pfad zeigt dass der Check
        pfad-basiert arbeitet — wenn der Pfad NICHT in der protected-List
        steht UND NICHT unter /etc/usr/var, dann ist es NICHT high-risk.
        """
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        # Pfad unter /Users/... (macOS-User-Workspace, nicht /var)
        args = ["rm", "-rf", "/Users/landjunge/some_safe_file.txt"]
        assert _is_high_risk_exec("rm", args) is False

    def test_rm_rf_on_src_gnom_hub_still_blocked(self, fake_workspace):
        """Bestehende 'src/gnom_hub' Coverage muss erhalten bleiben."""
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        target = str(fake_workspace / "src" / "gnom_hub" / "x.py")
        args = ["rm", "-rf", target]
        assert _is_high_risk_exec("rm", args) is True

    def test_mkfs_is_high_risk(self):
        from gnom_hub.core.security.gatekeeper import _is_high_risk_exec
        assert _is_high_risk_exec("mkfs", ["/dev/sda"]) is True
        assert _is_high_risk_exec("reboot", []) is True
