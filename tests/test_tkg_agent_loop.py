"""S5: TKG auto-recall / auto-curate in the runtime agent loop."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gnom_hub.core.prompt.builder import _inject_tkg_recall, build_system_prompt


@pytest.fixture(autouse=True)
def _tkg_flags_on(monkeypatch):
    from gnom_hub.core import config as cfg
    monkeypatch.setattr(cfg.Config, "TKG_AUTO_RECALL", True)
    monkeypatch.setattr(cfg.Config, "TKG_AUTO_CURATE", True)


def test_inject_tkg_recall_skips_short_message():
    base = "SYSTEM"
    assert _inject_tkg_recall(base, "CoderAG", "hi") == base
    assert _inject_tkg_recall(base, "CoderAG", "Du bist ein Assistent.") == base


def test_inject_tkg_recall_appends_facts():
    with patch(
        "gnom_hub.memory_tkg.adapter.retrieve_relevant",
        return_value=["FAISS needs numpy<2", "use WAL for SQLite"],
    ):
        out = _inject_tkg_recall(
            "SYSTEM",
            "CoderAG",
            "How should we fix the FAISS crash with numpy?",
        )
    assert "[KONTEXT:tkg_recall]" in out
    assert "FAISS needs numpy<2" in out
    assert "WAL for SQLite" in out


def test_inject_tkg_recall_fail_open():
    with patch(
        "gnom_hub.memory_tkg.adapter.retrieve_relevant",
        side_effect=RuntimeError("backend down"),
    ):
        out = _inject_tkg_recall(
            "SYSTEM",
            "CoderAG",
            "this is a long enough query for recall",
        )
    assert out == "SYSTEM"


def test_inject_tkg_recall_respects_flag(monkeypatch):
    from gnom_hub.core import config as cfg
    monkeypatch.setattr(cfg.Config, "TKG_AUTO_RECALL", False)
    with patch(
        "gnom_hub.memory_tkg.adapter.retrieve_relevant",
        return_value=["should-not-appear"],
    ) as mock_r:
        out = _inject_tkg_recall(
            "SYSTEM",
            "CoderAG",
            "this is a long enough query for recall",
        )
    assert out == "SYSTEM"
    mock_r.assert_not_called()


def test_build_system_prompt_wires_user_message_to_tkg():
    """Empty message_text → no TKG block; real message → block if facts exist."""
    with patch(
        "gnom_hub.memory_tkg.adapter.retrieve_relevant",
        return_value=["pattern: use [WRITE:] first"],
    ) as mock_r:
        no_msg = build_system_prompt("CoderAG", message_text="", runtime_settings=None)
        with_msg = build_system_prompt(
            "CoderAG",
            message_text="Please implement the HTML landing page with WRITE tags",
            runtime_settings=None,
        )
    assert "[KONTEXT:tkg_recall]" not in no_msg
    assert "[KONTEXT:tkg_recall]" in with_msg
    assert "pattern: use [WRITE:] first" in with_msg
    mock_r.assert_called()
    # last call should be the long user message
    assert "HTML landing" in mock_r.call_args[0][0]


def test_build_sys_passes_user_message_not_default_sys():
    from gnom_hub.infrastructure.router.router import _build_sys

    captured = {}

    def fake_build(*, agent_name, message_text="", runtime_settings=None):
        captured["message_text"] = message_text
        captured["agent_name"] = agent_name
        return f"PROMPT:{agent_name}"

    with patch(
        "gnom_hub.infrastructure.router.router.get_state_value",
        side_effect=lambda k, default=None: {} if k == "agent_settings" else "Web Development",
    ), patch(
        "gnom_hub.core.prompt.builder.build_system_prompt",
        side_effect=fake_build,
    ):
        # Import path used inside _build_sys
        with patch(
            "gnom_hub.core.prompt.builder.build_system_prompt",
            side_effect=fake_build,
        ):
            # Re-patch at the import site: _build_sys does local import
            import gnom_hub.core.prompt.builder as builder_mod
            with patch.object(builder_mod, "build_system_prompt", side_effect=fake_build):
                out = _build_sys(
                    "coderag",
                    "User asks about numpy FAISS issues carefully",
                    "CoderAG",
                )
    assert out == "PROMPT:CoderAG"
    assert "numpy FAISS" in captured["message_text"]


def test_ask_router_builds_sys_from_user_payload():
    from gnom_hub.infrastructure.router import router as router_mod

    seen = {}

    def fake_build_sys(n, message_text, agent_name):
        seen["message_text"] = message_text
        seen["agent_name"] = agent_name
        return "SYS"

    mock_ans = "ok"
    with patch.object(router_mod, "_build_sys", side_effect=fake_build_sys), patch.object(
        router_mod, "get_all_agents", return_value=[]
    ), patch.object(router_mod, "set_agent_status"), patch.object(
        router_mod, "get_state_value",
        side_effect=lambda k, default=None: (
            {"coderag": {"provider": "lokal", "model": "llama3"}} if k == "llm_agents" else {}
        ),
    ), patch.object(router_mod, "_resolve", return_value=[("lokal", "llama3")]), patch.object(
        router_mod, "_try", return_value=mock_ans
    ), patch.object(router_mod, "record_agent_request"), patch.object(
        router_mod, "wrap_response",
        side_effect=lambda ans, *a, **k: MagicMock(content=ans),
    ):
        r = router_mod.ask_router(
            "Please fix the FAISS embedding crash in production",
            sys="Du bist ein Assistent.",
            agent_name="CoderAG",
        )
    assert seen["message_text"].startswith("Please fix the FAISS")
    assert seen["agent_name"] == "CoderAG"
    assert r is not None


def test_extract_facts_also_writes_tkg():
    from gnom_hub.soul.zwc_soul import extract_facts_from_text

    text = (
        "ich merke, dass write-continue nach action cap greifen muss wenn "
        "mehrere HTML-Dateien im selben turn geschrieben werden. "
        "Die beste Strategie ist action input auf 120k zu heben."
    )
    with patch("gnom_hub.db.soul_repo.save_soul_fact_smart", return_value="k1") as soul, patch(
        "gnom_hub.memory_tkg.adapter.store_memory", return_value="fid"
    ) as tkg:
        keys = extract_facts_from_text(text, "CoderAG")
    assert keys  # at least one pattern hit
    assert soul.called
    assert tkg.called
