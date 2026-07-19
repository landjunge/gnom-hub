"""Gnom-Hub Agent-Namen + Farben (eingefroren).

Diese Konstanten sind VERTRAG — sie ändern sich nie. Der Router, die UI,
das Showbox-Theming, die Avatar-Registry und alle Tests beziehen sich
auf genau diese Werte.

Wenn du einen Agent umbenennen willst: lass es. Die Namen sind seit
dem ersten Commit der Gnom-Hub-Codebase dieselben und haben sich
historisch als gut lesbar erwiesen.
"""
from __future__ import annotations

from typing import Final

# ── Frozen agent names ────────────────────────────────────────────────────────
SYSTEM_AGENTS: Final[tuple[str, ...]] = (
    "SoulAG",
    "WatchdogAG",
    "GeneralAG",
    "SecurityAG",
)
WORKER_AGENTS: Final[tuple[str, ...]] = (
    "WriterAG",
    "CoderAG",
    "ResearcherAG",
    "EditorAG",
)
ALL_AGENTS: Final[tuple[str, ...]] = SYSTEM_AGENTS + WORKER_AGENTS
FROZEN: Final[bool] = True  # if you ever set this to False, the guard test fails

# ── Frozen agent colors (cyan = system, orange = worker) ─────────────────────
AGENT_COLORS: Final[dict[str, str]] = {
    "SoulAG":      "#00e5ff",
    "WatchdogAG":  "#00e5ff",
    "GeneralAG":   "#00e5ff",
    "SecurityAG":  "#00e5ff",
    "WriterAG":    "#ffa500",
    "CoderAG":     "#ffa500",
    "ResearcherAG": "#ffa500",
    "EditorAG":    "#ffa500",
}

# ── Avatar filenames (PNG) — files live in config/avatars/, URL /static/avatars/
AGENT_AVATARS: Final[dict[str, str]] = {
    "SoulAG":       "soulag.png",
    "WatchdogAG":   "watchdogag.png",
    "GeneralAG":    "generalag.png",
    "SecurityAG":   "securityag.png",
    "WriterAG":     "writerag.png",
    "CoderAG":      "coderag.png",
    "ResearcherAG": "researcherag.png",
    "EditorAG":     "editorag.png",
}

# ── Showbox theme colors (per category) ───────────────────────────────────────
SHOWBOX_THEME: Final[dict[str, dict[str, str]]] = {
    "system": {"color": "#00e5ff", "rgb": "0, 229, 255"},
    "worker": {"color": "#ffa500", "rgb": "255, 165, 0"},
    "user":   {"color": "#39ff14", "rgb": "57, 255, 20"},
}


def is_known_agent(name: str) -> bool:
    """Return True iff *name* is one of the 8 frozen agent names."""
    return name in ALL_AGENTS


def category_of(name: str) -> str:
    """Return 'system' or 'worker' for a known agent name."""
    if name in SYSTEM_AGENTS:
        return "system"
    if name in WORKER_AGENTS:
        return "worker"
    raise ValueError(f"unknown agent: {name!r}")


def color_of(name: str) -> str:
    """Return the frozen hex color for an agent name."""
    if name not in AGENT_COLORS:
        raise ValueError(f"unknown agent: {name!r}")
    return AGENT_COLORS[name]


def avatar_url(name: str) -> str:
    """Return the static URL for the agent's avatar PNG."""
    if name not in AGENT_AVATARS:
        raise ValueError(f"unknown agent: {name!r}")
    return f"/static/avatars/{AGENT_AVATARS[name]}"


__all__ = [
    "SYSTEM_AGENTS",
    "WORKER_AGENTS",
    "ALL_AGENTS",
    "FROZEN",
    "AGENT_COLORS",
    "AGENT_AVATARS",
    "SHOWBOX_THEME",
    "is_known_agent",
    "category_of",
    "color_of",
    "avatar_url",
]     

