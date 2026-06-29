"""tests/test_action_write_e2e.py

Reproducer-Tests für den [WRITE:] Action-Tag — End-to-End-Verifikation
dass process_actions() tatsächlich eine Datei schreibt und eine klare
Erfolgsmeldung zurückgibt.

Bug-Hintergrund (gefixt auf experimental/action-handler-fix):

    ``action_write.py:50`` importierte beim Erfolgsfall inline:
        from gnom_hub.soul.zwc_soul import add_agent_metadata

    Da ``gnom_hub/soul/__init__.py`` beim ersten Laden des
    ``gnom_hub.soul``-Pakets transitiv ``SoulAG``
    (sentence_transformers → torch) lädt, hing jeder erfolgreiche
    [WRITE:]-Aufruf 5-30s im Import.

    Symptom aus dem User-Report: "Action-Handler führt [WRITE:] nicht
    aus obwohl im Response" — Datei wurde geschrieben
    (handle_write Z.38-39 laufen VOR dem Import), aber der LLM-Pfad
    sah die Bestätigung erst Sekunden später und das User-Feedback
    "nichts passiert" blieb.

Diese Tests detektieren den Bug DETERMINISTISCH via Sentinelpatch:

    ``gnom_hub.soul.zwc_soul.add_agent_metadata`` wird vor jedem Test
    auf eine Sentinel-Funktion gepatcht, die ``SENTINEL_SOUL_ZWC``
    raised. Wenn die Produktion auf den alten Pfad zurückfällt (also
    ``add_agent_metadata`` aus ``gnom_hub.soul.zwc_soul`` aufruft),
    propagiert die Exception in den response und ein Disk-File entsteht
    zwar (handle_write schreibt VOR dem Import), aber die response
    enthält ``[System-Fehler: ... SENTINEL_SOUL_ZWC ...]``.

    Mit dem Fix wird ``add_agent_metadata`` aus
    ``gnom_hub.core.zwc_codec`` (pure-stdlib) bezogen — der patch auf
    ``gnom_hub.soul.zwc_soul.add_agent_metadata`` wird nie angefasst.

Hinweis: Timing-basierte Assertions sind unzuverlässig, weil
``conftest.isolated_db`` schon ``init_database()`` triggert, was den
SoulAG/torch-Import in der Fixture-Zeit verbraucht. Das Sentinelpatch
ist die verlässliche Methode.
"""

import time
import pytest


SENTINEL_SOUL_ZWC = "SENTINEL_SOUL_ZWC_TOUCHED"


def _explode(*args, **kwargs):
    raise RuntimeError(SENTINEL_SOUL_ZWC)


@pytest.fixture(autouse=True)
def _sentinel_soul_zwc(monkeypatch):
    """Patch every plausible lookup of ``gnom_hub.soul.zwc_soul.add_agent_metadata``
    such that on the UNFIXED code path the call raises. With the FIX,
    the call site doesn't go through soul.zwc_soul at all and the
    patch is never triggered.
    """
    import gnom_hub.soul.zwc_soul as zwc
    monkeypatch.setattr(zwc, "add_agent_metadata", _explode)
    # Also patch the import-binder alias on the parent package, in
    # case ``from gnom_hub.soul import add_agent_metadata`` is used.
    import gnom_hub.soul as soul_pkg
    if hasattr(soul_pkg, "add_agent_metadata"):
        monkeypatch.setattr(soul_pkg, "add_agent_metadata", _explode)
    yield


# ── 4 Required Reproducer Tests ──────────────────────────────────────────

class TestWriteEndToEnd:
    """4 required reproducer tests for [WRITE:] e2e behavior."""

    def test_write_simple_file_creates_file(self, tmp_path):
        """[WRITE:hello.txt]content[/WRITE] + write perm + wd → file exists."""
        from gnom_hub.agents.actions import action_handlers

        ans = "[WRITE:hello.txt]content[/WRITE]"
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        # Bug detector
        assert SENTINEL_SOUL_ZWC not in result, (
            f"Heavy soul.zwc_soul was triggered on write success. "
            f"Result: {result[:400]!r}"
        )
        assert "gespeichert" in result, (
            f"Expected success message, got: {result[:300]!r}"
        )
        fpath = tmp_path / "hello.txt"
        assert fpath.exists(), f"File not created at {fpath}"
        assert fpath.read_text(encoding="utf-8") == "content"

    def test_write_with_path_creates_file(self, tmp_path):
        """Code-fence variant: [WRITE:src/foo.py]```python\\nprint('hi')\\n```[/WRITE]."""
        from gnom_hub.agents.actions import action_handlers

        ans = (
            "[WRITE:src/foo.py]\n```python\nprint(\"hi\")\n```\n[/WRITE]"
        )
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        assert SENTINEL_SOUL_ZWC not in result, (
            f"Heavy soul.zwc_soul triggered on code-fence write. "
            f"Result: {result[:400]!r}"
        )
        assert "gespeichert" in result
        fpath = tmp_path / "src" / "foo.py"
        assert fpath.exists()
        content = fpath.read_text(encoding="utf-8")
        assert "print" in content, f"Code-fence content lost: {content!r}"

    def test_write_relative_path_within_workspace(self, tmp_path):
        """[WRITE:subdir/file.txt]content[/WRITE] — wd contains subdir/."""
        from gnom_hub.agents.actions import action_handlers

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        ans = "[WRITE:subdir/file.txt]inside[/WRITE]"
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        assert SENTINEL_SOUL_ZWC not in result, (
            f"Heavy soul.zwc_soul triggered on relative-path write. "
            f"Result: {result[:400]!r}"
        )
        assert "gespeichert" in result
        fpath = subdir / "file.txt"
        assert fpath.exists()
        assert fpath.read_text(encoding="utf-8") == "inside"

    def test_write_returns_success_message(self, tmp_path):
        """Response contains 'gespeichert' + absolute path, NOT 'blockiert'."""
        from gnom_hub.agents.actions import action_handlers

        ans = "[WRITE:saved.txt]x[/WRITE]"
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        assert SENTINEL_SOUL_ZWC not in result, (
            f"Heavy soul.zwc_soul triggered on success-message path. "
            f"Result: {result[:400]!r}"
        )
        # Bug indicator: success message uses "gespeichert"
        assert "gespeichert" in result, (
            f"Expected 'gespeichert' in result, got: {result[:300]!r}"
        )
        assert str(tmp_path / "saved.txt") in result, (
            f"Expected absolute path in result, got: {result[:300]!r}"
        )
        # Negative check: not a "blockiert" message
        assert "blockiert" not in result.lower(), (
            f"Got blocked-path message on valid write: {result[:300]!r}"
        )


# ── 2 Bonus Reproducer Tests ────────────────────────────────────────────

class TestWriteBugDetection:
    """Strong bug detectors — directly fail on the unfixed code."""

    def test_write_does_not_trigger_soul_zwc_import(self, tmp_path):
        """Source-level guarantee: action_write.py:50 must NOT import
        anything from gnom_hub.soul.zwc_soul (or transitive). This test
        is a belt-and-suspenders: it inspects the source of handle_write
        to ensure the bug class does not regress even if someone changes
        the import location to another soul module.

        On unfixed code, ``add_agent_metadata`` is sourced from
        ``gnom_hub.soul.zwc_soul``; the sentinel fixture above catches
        it. We additionally assert the source itself does not reference
        the broken module path.
        """
        from gnom_hub.agents.actions import action_handlers

        ans = "[WRITE:sentinel_check.txt]x[/WRITE]"
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        # Sentinel catches the unfixed-code execution path
        assert SENTINEL_SOUL_ZWC not in result, (
            f"soul.zwc_soul was reached. Result: {result[:400]!r}"
        )
        # File was actually written
        assert (tmp_path / "sentinel_check.txt").exists()

        # Source-level check: action_write.py must NOT have an actual
        # import of gnom_hub.soul.zwc_soul (comment-mentions are ok).
        # The bug class is: any import that transitively loads SoulAG.
        # We use AST to inspect only ``import X`` / ``from X import Y``
        # statements, ignoring comments and docstrings.
        import ast
        import pathlib
        action_write_path = pathlib.Path(
            __import__(
                "gnom_hub.agents.actions.action_write",
                fromlist=["handle_write"],
            ).__file__
        )
        tree = ast.parse(action_write_path.read_text(encoding="utf-8"))
        bad_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "gnom_hub.soul.zwc_soul" or \
                            alias.name.startswith("gnom_hub.soul.zwc_soul."):
                        bad_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "gnom_hub.soul.zwc_soul" or \
                        (node.module and node.module.startswith("gnom_hub.soul.zwc_soul.")):
                    bad_imports.append(f"from {node.module} import {{...}}")
        assert not bad_imports, (
            f"action_write.py still imports from gnom_hub.soul.zwc_soul "
            f"(triggers SoulAG/torch): {bad_imports}. Use "
            f"gnom_hub.core.zwc_codec instead."
        )

    def test_write_returns_clear_message_on_exception(self, tmp_path):
        """When the target path is impossible (parent is a file), the
        response must NOT silently claim success.
        """
        from gnom_hub.agents.actions import action_handlers

        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file")
        ans = "[WRITE:blocker/inner.txt]x[/WRITE]"
        result = action_handlers.process_actions(
            ans,
            {"name": "CoderAG", "role": "coder"},
            ["write"], bs_mode=False, wd=str(tmp_path),
        )
        # No sentinel trip on the error path (the failure happens
        # BEFORE add_agent_metadata is called)
        is_error = (
            "blockiert" in result.lower()
            or "System-Fehler" in result
            or "nicht gefunden" in result.lower()
        )
        assert is_error, (
            f"Expected error indicator on impossible path, "
            f"got: {result[:300]!r}"
        )
        # Must NOT be a silent "gespeichert" success
        assert "gespeichert" not in result.lower(), (
            f"Impossible write was claimed as success: {result[:300]!r}"
        )
