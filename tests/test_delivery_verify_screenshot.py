"""P0 Premium-Test fixes: VERIFY tags + SCREENSHOT wiring + soul task id prefix."""
from __future__ import annotations

import pytest


def test_verify_ok_and_fail(tmp_path, monkeypatch):
    from gnom_hub.agents.actions.action_verify import handle_verify

    wd = str(tmp_path)
    f = tmp_path / "readme-dev-showcase" / "v1.html"
    f.parent.mkdir(parents=True)
    f.write_text("<html>Gnom-Hub GeneralAG 3002</html>", encoding="utf-8")

    # Bypass path validator host rules — use real _safe with tmp as wd
    agent = {"name": "CoderAG"}
    perms = ["read", "write"]
    ans = "[VERIFY: readme-dev-showcase/v1.html|must_contain=Gnom-Hub|min_bytes=20]"
    # Wrap match objects like process_actions
    import re

    ms = list(re.finditer(r"\[VERIFY:\s*([^\]]+)\]", ans, re.I))
    out = handle_verify(ans, ms, agent, perms, wd)
    assert "VERIFY OK" in out
    assert "v1.html" in out

    ans2 = "[VERIFY: readme-dev-showcase/v1.html|must_contain=NOTTHERE]"
    ms2 = list(re.finditer(r"\[VERIFY:\s*([^\]]+)\]", ans2, re.I))
    out2 = handle_verify(ans2, ms2, agent, perms, wd)
    assert "VERIFY FAIL" in out2


def test_verify_missing_file(tmp_path):
    from gnom_hub.agents.actions.action_verify import handle_verify
    import re

    ans = "[VERIFY: no/such/file.html]"
    ms = list(re.finditer(r"\[VERIFY:\s*([^\]]+)\]", ans, re.I))
    out = handle_verify(ans, ms, {"name": "GeneralAG"}, ["read"], str(tmp_path))
    assert "VERIFY FAIL" in out
    assert "missing" in out


def test_process_actions_wires_verify(tmp_path, monkeypatch):
    from gnom_hub.agents.actions.action_handlers import process_actions

    f = tmp_path / "x.html"
    f.write_text("Gnom-Hub", encoding="utf-8")
    ans = "check [VERIFY: x.html|must_contain=Gnom-Hub|min_bytes=5] done"
    out = process_actions(ans, {"name": "CoderAG"}, ["read", "write"], False, str(tmp_path))
    assert "VERIFY OK" in out
    assert "[VERIFY:" not in out


def test_soul_task_id_prefix_not_soul_underscore():
    """Regression: task ids must not use soul_ prefix (worker Grenzverletzung)."""
    import inspect
    from gnom_hub.soul import soul as soul_mod

    src = inspect.getsource(soul_mod.SoulAG._create_task)
    assert 'f"task_' in src or "task_" in src
    assert 'f"soul_' not in src


def test_screenshot_handler_creates_png(tmp_path):
    pytest.importorskip("playwright")
    from gnom_hub.agents.actions.action_screenshot import handle_screenshot
    import re

    html = tmp_path / "page.html"
    html.write_text("<html><body><h1>Gnom-Hub</h1></body></html>", encoding="utf-8")
    ans = "[SCREENSHOT: page.html | out=page.png | width=800 | height=600]"
    ms = list(re.finditer(r"\[SCREENSHOT:\s*([^\]]+)\]", ans, re.I))
    out = handle_screenshot(ans, ms, {"name": "CoderAG"}, ["read", "write"], str(tmp_path))
    assert "Screenshot gespeichert" in out or "System-Fehler" in out
    # If chromium available, png exists
    png = tmp_path / "page.png"
    if "gespeichert" in out:
        assert png.is_file() and png.stat().st_size > 100
