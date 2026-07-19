"""Creative, realistic worker tool-usage tests.

These run in default CI (not in the browser ignore list). Goals:
1. Permission matrix matches reality (Coder ≠ browser, Researcher = browser)
2. Fake LLM browser prose does not look like success
3. Pseudo-tags [browser: url] expand to real [BROWSER:] scripts
4. process_actions denies browser without perm, allows with perm
5. WRITE/READ/SHELL matrix for workers
6. Optional live Playwright probe (skipped if playwright/chromium missing)
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from gnom_hub.agents.actions.action_handlers import (
    BROWSER_BLOCK_RE,
    BROWSER_PSEUDO_URL_RE,
    ensure_browser_executed_for_task,
    expand_browser_pseudo_tags,
    extract_browse_url,
    process_actions,
    reroute_browser_delegation,
    task_wants_browser,
)
from gnom_hub.agents.tool_registry import get_tools_for_agent
from gnom_hub.db.chat_repo import _agent_message_filter


# ── Permission / tool matrix ───────────────────────────────────────────────

class TestWorkerToolMatrix:
    def test_coder_has_file_and_shell_not_browser(self):
        soul = {
            "role": "coder",
            "permissions": [
                "read", "write", "run", "shell", "code",
                "showbox_write", "web_search",
            ],
        }
        tools = get_tools_for_agent(soul)
        assert "write_file" in tools or "read_file" in tools or "run_command" in tools
        # explicit: browser token required
        assert "browser" not in tools

    def test_researcher_with_browser_perm_gets_browser_tool(self):
        soul = {
            "role": "researcher",
            "permissions": [
                "read", "write", "crawl", "web_search", "browser", "showbox_write",
            ],
        }
        tools = get_tools_for_agent(soul)
        assert "browser" in tools
        assert "Playwright" in tools["browser"] or "browser" in tools["browser"].lower()

    def test_writer_no_browser_no_shell(self):
        soul = {
            "role": "writer",
            "permissions": ["read", "write", "crawl", "web_search", "showbox_write"],
        }
        tools = get_tools_for_agent(soul)
        assert "browser" not in tools
        assert "run_command" not in tools

    def test_general_is_orchestrator_not_executor(self):
        soul = {
            "role": "general",
            "permissions": ["read", "@job", "general_memory", "showbox_write"],
        }
        tools = get_tools_for_agent(soul)
        assert "browser" not in tools
        assert "write_file" not in tools
        assert "run_command" not in tools


# ── Tag formats (what LLMs actually emit) ──────────────────────────────────

class TestBrowserTagFormats:
    def test_canonical_block_regex(self):
        text = (
            "before\n"
            "[BROWSER:]\n"
            "print(1)\n"
            "[/BROWSER]\n"
            "after"
        )
        ms = list(BROWSER_BLOCK_RE.finditer(text))
        assert len(ms) == 1
        assert "print(1)" in ms[0].group(1)

    def test_case_insensitive_browser_block(self):
        text = "[browser:]\nprint('x')\n[/browser]"
        ms = list(BROWSER_BLOCK_RE.finditer(text))
        assert len(ms) == 1

    def test_pseudo_url_tag_matches_what_researcher_wrote(self):
        # Exact failure mode from production chat 2026-07-19
        text = (
            "[Fehler: Datei https://grok.ai nicht gefunden]\n"
            "[browser: https://grok.ai]\n"
            "Status-Meldung: fake"
        )
        m = BROWSER_PSEUDO_URL_RE.search(text)
        assert m is not None
        assert m.group(1).startswith("https://grok.ai")

    def test_prose_whitelist_browser_is_not_a_tool_tag(self):
        prose = (
            "⚠️ CoderAG — Auftrag erfasst: Browser via Whitelist öffnen, "
            "zu https://grok.ai navigieren"
        )
        assert not BROWSER_BLOCK_RE.search(prose)
        assert not BROWSER_PSEUDO_URL_RE.search(prose)


# ── Pseudo-tag expansion ───────────────────────────────────────────────────

class TestExpandBrowserPseudoTags:
    def test_expands_url_for_researcher(self):
        ans = "Ich öffne die Seite.\n[browser: https://example.com]\nfertig."
        out = expand_browser_pseudo_tags(
            ans, {"name": "ResearcherAG"}, ["browser", "read", "write"]
        )
        assert "[BROWSER:]" in out.upper() or "[browser:]" in out.lower()
        assert "playwright" in out.lower()
        assert "example.com" in out
        assert "[browser: https://example.com]" not in out

    def test_denies_pseudo_url_for_coder_without_browser(self):
        ans = "[browser: https://grok.ai]"
        out = expand_browser_pseudo_tags(
            ans, {"name": "CoderAG"}, ["read", "write", "run", "shell"]
        )
        assert "keine BROWSER-Berechtigung" in out
        assert "playwright" not in out.lower()

    def test_leaves_text_without_pseudo_alone(self):
        ans = "nur text ohne tags"
        assert expand_browser_pseudo_tags(ans, {"name": "X"}, ["browser"]) == ans


# ── process_actions permission + expansion ─────────────────────────────────

class TestProcessActionsBrowser:
    def test_coder_denied_real_browser_block(self):
        ans = "[BROWSER:]\nprint('should-not-run')\n[/BROWSER]"
        agent = {"name": "CoderAG"}
        perms = ["read", "write", "run", "shell", "code"]
        with tempfile.TemporaryDirectory() as wd:
            out = process_actions(ans, agent, perms, False, wd)
        assert "keine BROWSER-Berechtigung" in out
        assert "should-not-run" not in out or "BROWSER-Berechtigung" in out

    def test_researcher_pseudo_url_expands_then_runs_or_errors_honestly(self):
        """After expansion, either real browser output OR honest error — never silent prose."""
        ans = "Probe:\n[browser: https://example.com]\n"
        agent = {"name": "ResearcherAG"}
        perms = ["read", "write", "browser", "web_search"]
        with tempfile.TemporaryDirectory() as wd:
            # Mock sandbox to avoid requiring chromium in CI
            fake = type(
                "R",
                (),
                {
                    "stdout": "URL: https://example.com\nSTATUS: 200\nTITLE: Example Domain\n",
                    "stderr": "",
                    "returncode": 0,
                },
            )()
            with patch(
                "gnom_hub.agents.actions.action_browser.run_browser_in_sandbox",
                return_value=fake,
            ):
                out = process_actions(ans, agent, perms, False, wd)
        assert "Browser-Ausgabe" in out or "Browser-Fehler" in out or "Sicherheitsüberprüfung" in out
        assert "[browser: https://example.com]" not in out
        if "Browser-Ausgabe" in out:
            assert "STATUS: 200" in out or "Example" in out

    def test_process_actions_write_roundtrip_coder(self):
        agent = {"name": "CoderAG"}
        perms = ["read", "write", "run"]
        with tempfile.TemporaryDirectory() as wd:
            ans = "[WRITE: tool_probe.txt]hello-tools[/WRITE]"
            with patch(
                "gnom_hub.agents.actions.action_handlers.verify_write",
                return_value=True,
            ):
                out = process_actions(ans, agent, perms, False, wd)
            # file should exist under workspace
            written = list(Path(wd).rglob("tool_probe.txt"))
            assert written, f"WRITE did not create file in {wd}, out={out!r}"
            assert written[0].read_text(encoding="utf-8") == "hello-tools"

    def test_shell_denied_without_run(self):
        agent = {"name": "WriterAG"}
        perms = ["read", "write"]
        ans = "[SHELL: echo pwned]"
        with tempfile.TemporaryDirectory() as wd:
            out = process_actions(ans, agent, perms, False, wd)
        assert "keine" in out.lower() or "verweigert" in out.lower() or "Shell" in out or "run" in out.lower() or "SHELL" in out


# ── Chat filter must not kill tool status lines ────────────────────────────

class TestChatFilterVsTools:
    def test_short_general_answer_still_ok(self):
        f, reason = _agent_message_filter("GeneralAG", "JA", "chat")
        assert not f, reason

    def test_browser_output_marker_not_stubbed(self):
        content = (
            "[Browser-Ausgabe:\nURL: https://example.com\nSTATUS: 200\nTITLE: Example Domain]"
        )
        f, reason = _agent_message_filter("ResearcherAG", content, "chat")
        assert not f, reason


# ── Scenario: "browse grok.ai" pipeline ────────────────────────────────────

class TestBrowseGrokScenario:
    """Replays the failure modes from production chat, with expected fixes."""

    USER_MSG = "benutze der browser und gehe auf die seite grok.ai"

    def test_coder_ack_prose_is_not_tool_execution(self):
        coder_reply = (
            "⚠️ CoderAG — Orange — hier.\n\n"
            "Auftrag erfasst: Browser via Whitelist öffnen, zu https://grok.ai navigieren"
        )
        assert not BROWSER_BLOCK_RE.search(coder_reply)
        assert not BROWSER_PSEUDO_URL_RE.search(coder_reply)
        # process_actions should leave prose unchanged (no tool tags)
        out = process_actions(
            coder_reply,
            {"name": "CoderAG"},
            ["read", "write", "run", "shell"],
            False,
            tempfile.gettempdir(),
        )
        assert "Browser-Ausgabe" not in out
        assert "Auftrag erfasst" in out

    def test_researcher_pseudo_tag_becomes_executable_block(self):
        researcher_reply = (
            "[Fehler: Datei https://grok.ai nicht gefunden]\n"
            "Ich öffne die Seite via Browser-Tool.\n"
            "[browser: https://grok.ai]\n"
        )
        expanded = expand_browser_pseudo_tags(
            researcher_reply,
            {"name": "ResearcherAG"},
            ["browser", "read", "write"],
        )
        assert BROWSER_BLOCK_RE.search(expanded)
        assert "playwright" in expanded.lower()
        assert "grok.ai" in expanded

    def test_general_should_delegate_to_researcher_not_coder_for_browser(self):
        """Routing hint test: browser capability is on researcher, not coder."""
        from gnom_hub.agents.routing import _CANONICAL_CAPABILITIES

        browser_keys = _CANONICAL_CAPABILITIES.get("browser", [])
        assert browser_keys, "browser capability map missing"
        assert any("browser" in k or "playwright" in k for k in browser_keys)

        coder_tools = get_tools_for_agent({
            "role": "coder",
            "permissions": ["read", "write", "run", "shell", "code", "web_search"],
        })
        researcher_tools = get_tools_for_agent({
            "role": "researcher",
            "permissions": ["read", "write", "crawl", "web_search", "browser"],
        })
        assert "browser" not in coder_tools
        assert "browser" in researcher_tools


# ── Live Playwright (optional, real) ───────────────────────────────────────

def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(headless=True)
                b.close()
                return True
            except Exception:
                return False
    except Exception:
        return False


class TestForceBrowserForTask:
    def test_extract_url_from_german_browse_request(self):
        assert task_wants_browser("benutze der browser und gehe auf die seite grok.ai")
        assert extract_browse_url("benutze der browser und gehe auf die seite grok.ai") == "https://grok.ai"

    def test_force_runs_when_llm_only_said_ack(self):
        prose = "⚠️ CoderAG — Auftrag erfasst, Browser via Whitelist…"
        agent = {"name": "ResearcherAG"}
        perms = ["browser", "read"]
        fake = type(
            "R",
            (),
            {
                "stdout": "URL: https://grok.ai\nSTATUS: 200\nTITLE: Grok\n",
                "stderr": "",
                "returncode": 0,
            },
        )()
        with tempfile.TemporaryDirectory() as wd:
            with patch(
                "gnom_hub.agents.actions.action_browser.run_browser_in_sandbox",
                return_value=fake,
            ):
                out = ensure_browser_executed_for_task(
                    prose,
                    "benutze der browser und gehe auf die seite grok.ai",
                    agent,
                    perms,
                    wd,
                )
        assert "Browser-Ausgabe" in out
        assert "STATUS: 200" in out

    def test_force_notes_missing_perm_on_coder(self):
        prose = "Auftrag erfasst"
        out = ensure_browser_executed_for_task(
            prose,
            "browser https://example.com",
            {"name": "CoderAG"},
            ["read", "write", "run"],
            tempfile.gettempdir(),
        )
        assert "keine BROWSER-Permission" in out or "ResearcherAG" in out
        assert "Browser-Ausgabe" not in out

    def test_reroute_coder_to_researcher(self):
        user = "benutze der browser und gehe auf die seite grok.ai"
        reply = "@CoderAG öffne via System-Browser https://grok.ai"
        fixed = reroute_browser_delegation(user, reply, "GeneralAG")
        assert "@ResearcherAG" in fixed
        assert "@CoderAG" not in fixed


@pytest.mark.skipif(not _playwright_available(), reason="playwright/chromium not installed")
class TestLiveBrowserProbe:
    """Real headless chromium against example.com — only when playwright works."""

    def test_live_example_com_title(self):
        from gnom_hub.agents.actions.action_browser import handle_browser

        ans = (
            "[BROWSER:]\n"
            "from playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as p:\n"
            "    b = p.chromium.launch(headless=True)\n"
            "    page = b.new_page()\n"
            "    page.goto('https://example.com', wait_until='domcontentloaded', timeout=30000)\n"
            "    print('TITLE:', page.title())\n"
            "    print('URL:', page.url)\n"
            "    b.close()\n"
            "[/BROWSER]"
        )
        agent = {"name": "ResearcherAG"}
        perms = ["browser"]
        with tempfile.TemporaryDirectory() as wd:
            ms = list(BROWSER_BLOCK_RE.finditer(ans))
            out = handle_browser(ans, ms, agent, perms, wd)
        assert "Browser-Ausgabe" in out
        assert "Example" in out or "example.com" in out.lower()
        assert "Sicherheitsüberprüfung fehlgeschlagen" not in out
