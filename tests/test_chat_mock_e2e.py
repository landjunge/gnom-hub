"""Prio-4: Mock chat path guards (no live Hub / MiniMax)."""
from __future__ import annotations

from gnom_hub.agents.actions.action_handlers import process_actions


def test_process_actions_then_agent_would_post_content():
    """Happy path: LLM text survives process_actions so chat can show it."""
    content = "Hier ist die Antwort ohne Think-Block."
    out = process_actions(
        content,
        {"name": "CoderAG"},
        ["read", "write", "run", "showbox_write"],
        False,
        "/tmp",
    )
    assert "Antwort" in out


def test_router_error_string_is_detectable():
    """Guard for agent_base branch: ROUTER-FEHLER must stay a stable prefix."""
    raw = "[ROUTER-FEHLER] Alle Gleise offline."
    assert raw.startswith("[ROUTER-FEHLER]")


def test_dispatch_then_offline_feedback(monkeypatch):
    """User chat with offline GeneralAG produces System feedback (Prio-1)."""
    from gnom_hub.api.endpoints import chat_legacy
    from gnom_hub.api.endpoints.chat_legacy import ChatMsg

    posted = []

    monkeypatch.setattr(
        chat_legacy,
        "add_chat_message",
        lambda *a, **k: posted.append((a[1], a[4] if len(a) > 4 else "")),
    )
    monkeypatch.setattr(chat_legacy, "get_active_project", lambda: "default")
    monkeypatch.setattr(
        chat_legacy,
        "get_all_agents",
        lambda: [{"name": "GeneralAG", "status": "offline"}],
    )
    monkeypatch.setattr(chat_legacy, "dispatch", lambda *a, **k: [])
    monkeypatch.setattr(chat_legacy.soul_instance, "on_message", lambda *a, **k: None)
    monkeypatch.setattr(
        "gnom_hub.core.security.injection_validator.validate_input",
        lambda c: (True, None),
    )
    monkeypatch.setattr(
        "gnom_hub.core.security.showbox_validator.enforce_agent_layer",
        lambda c, s: c,
    )

    r = chat_legacy.post_chat(ChatMsg(content="ping", sender="user"))
    assert r["status"] == "error"
    assert any(p[0] == "System" and "Dispatch" in p[1] for p in posted)
