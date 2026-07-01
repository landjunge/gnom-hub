"""Frozen agent names + colors guard.

Die Agent-Namen und ihre Farben sind Vertrag. Dieser Test schlägt
fehl, sobald jemand einen Namen umbenennt, einen Agent hinzufügt
ohne Farbe zu setzen, oder FROZEN auf False flippt.

Wenn du wirklich einen Agent umbenennen willst: überlege dir das
zweimal. Die ganze Codebase hängt von diesen Strings.
"""
from pathlib import Path

import pytest

from gnom_hub.core.agent_names import (
    AGENT_AVATARS,
    AGENT_COLORS,
    ALL_AGENTS,
    FROZEN,
    SHOWBOX_THEME,
    SYSTEM_AGENTS,
    WORKER_AGENTS,
    avatar_url,
    category_of,
    color_of,
    is_known_agent,
)


def test_frozen_is_true():
    assert FROZEN is True, "FROZEN flag was flipped to False — that's a contract breach"


def test_system_agents_exact_set():
    assert SYSTEM_AGENTS == ("SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG")


def test_worker_agents_exact_set():
    assert WORKER_AGENTS == ("WriterAG", "CoderAG", "ResearcherAG", "EditorAG")


def test_all_agents_is_concatenation():
    assert ALL_AGENTS == SYSTEM_AGENTS + WORKER_AGENTS


def test_all_agents_unique():
    assert len(set(ALL_AGENTS)) == len(ALL_AGENTS), "duplicate agent name"


def test_every_agent_has_color():
    for name in ALL_AGENTS:
        assert name in AGENT_COLORS, f"missing color for {name}"
        assert AGENT_COLORS[name].startswith("#"), f"color for {name} not hex"
        assert len(AGENT_COLORS[name]) == 7, f"color for {name} wrong length"


def test_system_agents_are_cyan():
    for name in SYSTEM_AGENTS:
        assert AGENT_COLORS[name] == "#00e5ff", f"{name} should be cyan"


def test_worker_agents_are_orange():
    for name in WORKER_AGENTS:
        assert AGENT_COLORS[name] == "#ffa500", f"{name} should be orange"


def test_every_agent_has_avatar():
    for name in ALL_AGENTS:
        assert name in AGENT_AVATARS
        assert AGENT_AVATARS[name].endswith(".png")


def test_every_avatar_file_exists():
    avatars_dir = Path(__file__).parent.parent / "src" / "gnom_hub" / "frontend" / "static" / "avatars"
    for name in ALL_AGENTS:
        f = avatars_dir / AGENT_AVATARS[name]
        assert f.exists(), f"missing avatar file: {f}"
        assert f.stat().st_size > 1000, f"avatar {f} suspiciously small"


def test_showbox_theme_keys():
    assert set(SHOWBOX_THEME.keys()) == {"system", "worker", "user"}


def test_is_known_agent():
    assert is_known_agent("SoulAG")
    assert is_known_agent("CoderAG")
    assert not is_known_agent("FooAG")
    assert not is_known_agent("")


def test_category_of():
    assert category_of("SoulAG") == "system"
    assert category_of("CoderAG") == "worker"
    with pytest.raises(ValueError):
        category_of("UnknownAG")


def test_color_of():
    assert color_of("SoulAG") == "#00e5ff"
    assert color_of("WriterAG") == "#ffa500"
    with pytest.raises(ValueError):
        color_of("NotAnAgent")


def test_avatar_url():
    assert avatar_url("SoulAG") == "/static/avatars/soulag.png"
    assert avatar_url("EditorAG") == "/static/avatars/editorag.png"
    with pytest.raises(ValueError):
        avatar_url("GhostAG")
