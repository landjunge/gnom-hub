"""GeneralAG must answer short user prompts directly — not browser-delegate."""
from __future__ import annotations

from gnom_hub.agents.agent_base import (
    _reply_is_mostly_delegation,
    _user_wants_direct_reply,
)
from gnom_hub.core.prompt.context import _is_noise_chat_line


def test_user_wants_direct_reply_patterns():
    assert _user_wants_direct_reply("Sag nur: JA")
    assert _user_wants_direct_reply("@GeneralAG Sag nur: JA")
    assert _user_wants_direct_reply("Antworte mit genau einem Wort: FUNKTIONIERT")
    assert _user_wants_direct_reply("pong")
    assert _user_wants_direct_reply("Was ist 2+2?")
    assert not _user_wants_direct_reply(
        "öffne den browser und gehe auf https://grok.ai und mach screenshot"
    )
    assert not _user_wants_direct_reply(
        "Schreibe eine HTML Landingpage mit [WRITE:] Tags"
    )


def test_reply_is_mostly_delegation():
    assert _reply_is_mostly_delegation(
        "@CoderAG öffne via Browser https://grok.ai und verifiziere"
    )
    assert _reply_is_mostly_delegation(
        "<think>x</think>\n@CoderAG browser whitelist grok.ai screenshot"
    )
    assert not _reply_is_mostly_delegation("JA")
    assert not _reply_is_mostly_delegation(
        "Kurz: nein. Ich delegiere nichts.\nHier die Antwort."
    )


def test_short_generalag_answers_not_filtered():
    from gnom_hub.db.chat_repo import _agent_message_filter
    # The bug: "JA" was dropped as stub:empty_or_too_short
    filtered, reason = _agent_message_filter("GeneralAG", "JA", "chat")
    assert not filtered, reason
    filtered, reason = _agent_message_filter("GeneralAG", "OK", "chat")
    assert not filtered, reason
    filtered, reason = _agent_message_filter("GeneralAG", "Nein", "chat")
    assert not filtered, reason
    # truly empty still filtered
    filtered, reason = _agent_message_filter("GeneralAG", "   ", "chat")
    assert filtered


def test_noise_chat_line_filters_browser_loop():
    assert _is_noise_chat_line(
        "CoderAG",
        "⚠️ CoderAG — Orange — hier. Auftrag erfasst: Browser via Whitelist grok.ai",
    )
    assert _is_noise_chat_line(
        "GeneralAG",
        "@CoderAG öffne via System-Browser die URL https://grok.ai und verifiziere Erreichbarkeit Screenshot",
    )
    assert not _is_noise_chat_line("user", "Sag nur: JA")
    assert not _is_noise_chat_line("GeneralAG", "JA")
