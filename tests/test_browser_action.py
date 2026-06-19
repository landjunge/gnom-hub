"""Test for the BROWSER action handler + gatekeeper.

Verifies the worker-tool chain end-to-end:
1. Gatekeeper blocks dangerous patterns (os.system, subprocess, eval, etc.)
2. Gatekeeper allows clean Playwright scripts
3. handle_browser extracts Python from [BROWSER:...[/BROWSER]] tags
4. handle_browser returns formatted output or error
5. Tool registry actually exposes `browser` to workers with godmode permission
"""
import os
import re
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


# ── Gatekeeper: forbidden patterns ─────────────────────────────────────────

class TestBrowserGatekeeperForbidden:
    """Each forbidden pattern must be blocked by verify_browser()."""

    @pytest.fixture
    def agent(self):
        return {"name": "CoderAG"}

    @pytest.mark.parametrize("code,expected_reason_keyword", [
        ('import os\nos.system("rm -rf /")', "os.system"),
        ('from os import system\nsystem("echo pwned")', "os.system"),
        ('import subprocess\nsubprocess.run(["ls"])', "subprocess"),
        ('eval("1+1")', "eval"),
        ('exec("print(1)")', "exec"),
        ('x = compile("print(1)", "<s>", "exec")', "compile"),
        ('__import__("os").system("ls")', "__import__"),
        ('import ctypes\nctypes.CDLL("/usr/lib/libc.dylib")', "ctypes"),
        ('import socket\ns = socket.socket()', "socket"),
        ('import shutil\nshutil.rmtree("/")', "rmtree"),
        ('import os\nos.remove("/etc/passwd")', "os.remove"),
        ('import importlib\nimportlib.import_module("os")', "importlib"),
        ('open("/etc/passwd", "r").read()', "absolute"),
        ('open("/tmp/x", "w")', "absolute"),
    ])
    def test_forbidden_pattern_blocked(self, agent, code, expected_reason_keyword):
        from gnom_hub.core.security.gatekeeper_browser import verify_browser
        result = verify_browser(agent, code, wd=tempfile.gettempdir(), perms=["godmode"])
        assert result is False, f"Code with {expected_reason_keyword!r} should be blocked, but verify_browser returned True. Code:\n{code}"


# ── Gatekeeper: clean Playwright scripts pass ──────────────────────────────

class TestBrowserGatekeeperAllowed:
    """Clean Playwright code must pass the gatekeeper."""

    @pytest.fixture
    def agent(self):
        return {"name": "ResearcherAG"}

    def test_simple_goto(self, agent):
        from gnom_hub.core.security.gatekeeper_browser import verify_browser
        code = (
            "from playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p:\n"
            "    b = p.chromium.launch(headless=True)\n"
            "    page = b.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    print(page.title())\n"
            "    b.close()\n"
        )
        assert verify_browser(agent, code, wd=tempfile.gettempdir(), perms=["godmode"]) is True

    def test_screenshot(self, agent):
        from gnom_hub.core.security.gatekeeper_browser import verify_browser
        code = (
            "from playwright.sync_api import sync_playwright\n"
            "import json\n"
            "with sync_playwright() as p:\n"
            "    b = p.chromium.launch(headless=True)\n"
            "    page = b.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    page.screenshot(path='shot.png')\n"
            "    print('ok')\n"
            "    b.close()\n"
        )
        assert verify_browser(agent, code, wd=tempfile.gettempdir(), perms=["godmode"]) is True

    def test_evaluate(self, agent):
        from gnom_hub.core.security.gatekeeper_browser import verify_browser
        code = (
            "from playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p:\n"
            "    b = p.chromium.launch(headless=True)\n"
            "    page = b.new_page()\n"
            "    page.goto('https://example.com')\n"
            "    result = page.evaluate('() => document.title')\n"
            "    print(result)\n"
            "    b.close()\n"
        )
        assert verify_browser(agent, code, wd=tempfile.gettempdir(), perms=["godmode"]) is True


# ── handle_browser: extraction + output format ─────────────────────────────

class TestHandleBrowserExtraction:
    """handle_browser must extract Python code from [BROWSER:...[/BROWSER]] tags
    and produce well-formed output or error markers."""

    def test_extracts_python_from_multiline_tag(self):
        from gnom_hub.agents.actions.action_browser import handle_browser
        # Use a script that succeeds quickly without network
        code_block = (
            "[BROWSER:]\n"
            "print('hello-from-browser')\n"
            "[/BROWSER]"
        )
        ans = code_block
        agent = {"name": "TestAG"}
        perms = ["godmode"]
        with tempfile.TemporaryDirectory() as wd:
            ms = list(re.finditer(r"\[BROWSER:\s*\]([\s\S]*?)\[/BROWSER\]", ans))
            result = handle_browser(ans, ms, agent, perms, wd)
        assert "[BROWSER:" not in result, f"Original tag not replaced:\n{result}"
        assert "[/BROWSER]" not in result, f"Closing tag not replaced:\n{result}"
        assert "Browser-Ausgabe" in result, f"Expected Browser-Ausgabe marker, got:\n{result}"
        assert "hello-from-browser" in result, f"Expected stdout in output, got:\n{result}"

    def test_replaces_blocked_script_with_security_message(self):
        from gnom_hub.agents.actions.action_browser import handle_browser
        ans = "[BROWSER:]\nimport os\nos.system('echo pwned')\n[/BROWSER]"
        agent = {"name": "EvilAG"}
        perms = ["godmode"]
        with tempfile.TemporaryDirectory() as wd:
            ms = list(re.finditer(r"\[BROWSER:\s*\]([\s\S]*?)\[/BROWSER\]", ans))
            result = handle_browser(ans, ms, agent, perms, wd)
        assert "Sicherheitsüberprüfung fehlgeschlagen" in result, f"Expected gatekeeper block message, got:\n{result}"
        assert "Browser-Ausgabe" not in result, f"Blocked script must NOT be executed, got:\n{result}"

    def test_replaces_failing_script_with_error_marker(self):
        from gnom_hub.agents.actions.action_browser import handle_browser
        ans = "[BROWSER:]\nraise RuntimeError('intentional test error')\n[/BROWSER]"
        agent = {"name": "TestAG"}
        perms = ["godmode"]
        with tempfile.TemporaryDirectory() as wd:
            ms = list(re.finditer(r"\[BROWSER:\s*\]([\s\S]*?)\[/BROWSER\]", ans))
            result = handle_browser(ans, ms, agent, perms, wd)
        # Either Browser-Fehler (exception in wrapper) or Browser-Ausgabe
        # (subprocess non-zero, traceback captured) is acceptable — what
        # matters is that the original tags are gone and the error is shown.
        assert "Browser-Fehler" in result or "Browser-Ausgabe" in result, (
            f"Expected error or output marker, got:\n{result}"
        )
        assert "RuntimeError" in result, f"Expected traceback in result, got:\n{result}"
        assert "[BROWSER:" not in result
        assert "[/BROWSER]" not in result

    def test_no_match_returns_input_unchanged(self):
        from gnom_hub.agents.actions.action_browser import handle_browser
        ans = "no browser action here, just text"
        result = handle_browser(ans, [], {"name": "X"}, ["godmode"], "/tmp")
        assert result == ans


# ── Tool registry: workers with godmode get the browser tool ──────────────

class TestToolRegistryBrowser:
    """Workers with godmode permission must see the browser tool and the
    Playwright syntax hint — that's what the previous bug ate."""

    def test_coder_with_godmode_gets_browser(self):
        from gnom_hub.agents.tool_registry import get_tools_for_agent
        soul = {"role": "coder", "permissions": ["read", "write", "run", "@job", "godmode"]}
        tools = get_tools_for_agent(soul)
        assert "browser" in tools, f"CoderAG should have browser, got: {list(tools.keys())}"

    def test_browser_description_mentions_playwright(self):
        from gnom_hub.agents.tool_registry import get_tools_for_agent
        soul = {"role": "coder", "permissions": ["read", "write", "run", "godmode"]}
        tools = get_tools_for_agent(soul)
        assert "Playwright" in tools.get("browser", ""), (
            f"browser description must mention Playwright so workers know the runtime, "
            f"got: {tools.get('browser')!r}"
        )

    def test_format_tools_prompt_shows_python_syntax(self):
        from gnom_hub.agents.tool_registry import format_tools_prompt
        soul = {"role": "coder", "permissions": ["read", "write", "run", "godmode"]}
        sys_prompt = format_tools_prompt(soul, "CoderAG")
        # Must NOT show the old misleading JSON hint
        assert '"action":' not in sys_prompt or "playwright" in sys_prompt.lower(), (
            "Old JSON hint should be replaced with Playwright-based example"
        )
        # Must show the Python example
        assert "from playwright.sync_api import sync_playwright" in sys_prompt, (
            "System prompt must include the Python example so workers can copy the pattern"
        )

    def test_researcher_without_godmode_no_browser(self):
        from gnom_hub.agents.tool_registry import get_tools_for_agent
        soul = {"role": "researcher", "permissions": ["read"]}
        tools = get_tools_for_agent(soul)
        assert "browser" not in tools, "Without godmode, browser should not be exposed"
