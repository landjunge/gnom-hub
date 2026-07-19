"""Prio-5: GeneralAG orchestrator tools + prompt + worker-watch helper."""
from __future__ import annotations

from gnom_hub.agents.agent_base import _WORKER_MENTION_RE, _schedule_worker_reply_watch
from gnom_hub.agents.tool_registry import format_tools_prompt, get_tools_for_agent


def test_generalag_tools_not_empty():
    soul = {"role": "general", "character": "Dirigent", "directive": "orchestrate", "permissions": ["read", "@job", "showbox_write"]}
    tools = get_tools_for_agent(soul)
    assert tools, "GeneralAG must not have empty tool dict"
    assert "delegate" in tools
    assert "showbox" in tools
    assert "run_command" not in tools
    assert "write_file" not in tools


def test_generalag_prompt_has_delegation_and_user_visibility():
    soul = {
        "role": "general",
        "character": "Dirigent",
        "directive": "orchestrate",
        "permissions": ["read", "@job", "showbox_write"],
    }
    p = format_tools_prompt(soul, "GeneralAG")
    assert "DELEGATION" in p
    assert "@CoderAG" in p
    assert "USER-SICHTBARKEIT" in p or "sichtbar" in p.lower()
    assert "[SHELL:" not in p  # no shell for conductor


def test_worker_tools_still_have_write_for_coder():
    soul = {"role": "coder", "permissions": ["read", "write", "run", "showbox_write"]}
    tools = get_tools_for_agent(soul)
    assert "write_file" in tools
    assert "run_command" in tools


def test_worker_mention_regex():
    text = "Plan: @CoderAG -> bau X\n@WriterAG doku"
    found = {m.group(1) for m in _WORKER_MENTION_RE.finditer(text)}
    assert found == {"CoderAG", "WriterAG"}


def test_schedule_worker_watch_no_op_without_mentions():
    calls = []
    _schedule_worker_reply_watch(lambda *a, **k: calls.append(a), "nur Text ohne Mentions", "ctx")
    # Thread may start but should exit early without posting
    assert calls == []


def test_agent_definitions_generalag_allows_user_chat():
    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
    g = AGENT_DEFINITIONS["generalag"]
    prompt = g["sys_prompt"]
    assert "User-Chat" in prompt or "sichtbare Chat" in prompt or "Chat-Antwort" in prompt
    assert "Kein direkter User-Chat" not in prompt
    assert "@CoderAG ->" in prompt
