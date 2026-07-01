"""mermaid_canvas.py — Build a compact Mermaid ``graph LR`` of session events.

Companion to :mod:`gnom_hub.memory.offload`. Each offloaded tool output
becomes a node in the canvas, identified by its ``node_id``. The agent can
parse this canvas cheaply (a few hundred tokens) and drill back into the
raw content via :func:`gnom_hub.memory.node_resolver.resolve_node`.

Design constraints (from the task spec)
---------------------------------------
- Output is a valid Mermaid ``graph LR`` diagram: no broken arrows,
  no unescaped special characters.
- Limits: at most :data:`MAX_NODES` nodes; final rendered text stays
  under :data:`MAX_TOKENS` estimated tokens when injected as a system-
  prompt block.
- Deterministic for the same input: ``node_id`` is whatever the offloader
  assigned — we never randomize here, so the canvas output depends only
  on the entries passed in.
- Lossless drill-down: the canvas carries ``node_id`` on every node, plus
  a short ``tool_name: summary`` label. Full content lives at
  ``refs/<node_id>.md`` on disk.

The aggressive mode (passed via ``mode="aggressive"``) drops the oldest
nodes when there are more than :data:`MAX_NODES` so the canvas stays
bounded under context pressure.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from gnom_hub.memory.offload import OffloadEntry

logger = logging.getLogger(__name__)

# ── Tunables ────────────────────────────────────────────────────────────────

#: Hard cap on nodes in a single canvas. Matches the TencentDB
#: plugin's ``maxPairsPerBatch`` default (20) so the agent never sees
#: more than a screen of Mermaid at once.
MAX_NODES: int = 20

#: Hard cap on estimated tokens for the rendered canvas. The agent
#: prompt builder will refuse to inject anything bigger.
MAX_TOKENS: int = 200

#: How many chars of summary to keep per node label.
MAX_SUMMARY_CHARS: int = 80

#: Chars reserved for the ``graph LR`` header + arrows + indent.
#: Subtract this from the budget when computing per-node label size.
FRAMEWORK_OVERHEAD_CHARS: int = 200

# ── Public API ──────────────────────────────────────────────────────────────


def build_canvas(
    entries: Iterable[OffloadEntry],
    mode: str = "normal",
    max_nodes: int = MAX_NODES,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """Render a Mermaid ``graph LR`` for ``entries``.

    Parameters
    ----------
    entries
        The offload entries to render. Order matters: entries are
        connected in the order they appear (oldest → newest), so the
        canvas reads as a left-to-right timeline.
    mode
        ``"normal"`` — keep all entries, trim if there are too many
        nodes or too many tokens.

        ``"aggressive"`` — used once the offloader's cumulative_bytes
        exceeds the aggressive threshold; drops the OLDEST entries so
        the most recent activity stays in view.
    max_nodes, max_tokens
        Override the defaults; mainly for tests.

    Returns
    -------
    A string containing a valid Mermaid ``graph LR`` block, or an
    empty string if there are no entries.
    """
    entries_list = list(entries)
    if not entries_list:
        return ""

    if mode == "aggressive" and len(entries_list) > max_nodes:
        # Drop oldest until we're under cap; preserves the timeline
        # of recent activity.
        entries_list = entries_list[-max_nodes:]
    elif len(entries_list) > max_nodes:
        # Normal mode: still trim but don't lose recency.
        entries_list = entries_list[-max_nodes:]

    lines: list[str] = ["graph LR", "    User([User])"]
    prev = "User"
    for entry in entries_list:
        label = _build_label(entry)
        node_line = f'    {entry.node_id}["{label}"]'
        arrow_line = f"    {prev} --> {entry.node_id}"
        lines.append(arrow_line)
        lines.append(node_line)
        prev = entry.node_id

    canvas = "\n".join(lines)

    # Final token trim: if we're still over budget (because some labels
    # were long), shorten labels further until we fit.
    canvas = _trim_to_token_budget(canvas, max_tokens)
    return canvas


def canvas_token_estimate(canvas: str) -> int:
    """Estimate token count of a canvas string.

    Uses the same ``words * 1.3`` heuristic as
    :func:`gnom_hub.memory.context_manager.count_tokens` so the two
    estimators agree.
    """
    if not canvas:
        return 0
    words = len(canvas.split())
    if words > 0:
        return max(1, int(words * 1.3))
    return max(1, len(canvas) // 4)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _build_label(entry: OffloadEntry) -> str:
    """Build a Mermaid-safe node label for ``entry``."""
    raw = f"{entry.tool_name}: {entry.summary}"
    safe = _escape_label(raw)
    if len(safe) > MAX_SUMMARY_CHARS:
        safe = safe[: MAX_SUMMARY_CHARS - 1] + "…"
    return safe


# Characters that have special meaning inside a Mermaid ``"…"`` label.
# We replace them with ASCII fallbacks. ``"`` itself is handled by the
# caller (the label is already inside a quoted label slot).
_LABEL_ESCAPES = {
    "\n": " ",
    "\r": " ",
    "\t": " ",
    "[": "(",
    "]": ")",
    "{": "(",
    "}": ")",
    "|": "/",
    "<": "(",
    ">": ")",
    "#": "h",
}


def _escape_label(text: str) -> str:
    """Sanitize ``text`` for use inside a Mermaid ``"…"`` label."""
    if not text:
        return ""
    out = []
    for ch in text:
        if ch in _LABEL_ESCAPES:
            out.append(_LABEL_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            # Drop control chars (Mermaid parsers reject them).
            out.append(" ")
        else:
            out.append(ch)
    # Mermaid labels cannot contain a literal double-quote unless we open
    # a new quoted region. We strip them.
    return "".join(out).replace('"', "'")


def _trim_to_token_budget(canvas: str, max_tokens: int) -> str:
    """Shorten labels until ``canvas`` fits within ``max_tokens``.

    Operates on the rendered text: parses lines, finds labels (text
    inside ``["…""]``), and shrinks the longest one until the canvas
    fits. Falls back to dropping the oldest node if even a 1-char
    label does not fit.
    """
    if canvas_token_estimate(canvas) <= max_tokens:
        return canvas

    # Pattern: '    NODENAME["label contents"]' (label may contain spaces).
    label_re = re.compile(r'^(\s*)([a-f0-9]{8})(\[")([^"]*)("\]$)')

    # Repeatedly shrink the longest label by 10 chars until we fit.
    while canvas_token_estimate(canvas) > max_tokens:
        lines = canvas.split("\n")
        # Find index of longest label line.
        idx = -1
        longest = -1
        for i, line in enumerate(lines):
            m = label_re.match(line)
            if not m:
                continue
            label = m.group(4)
            if len(label) > longest:
                longest = len(label)
                idx = i
        if idx < 0 or longest <= 4:
            # Nothing to shorten further — drop the oldest node.
            canvas = _drop_oldest_node(canvas, label_re)
            if canvas == "":
                return ""
            continue
        m = label_re.match(lines[idx])
        label = m.group(4)
        new_len = max(4, len(label) - 10)
        lines[idx] = f'{m.group(1)}{m.group(2)}{m.group(3)}{label[:new_len]}…{m.group(5)}'
        canvas = "\n".join(lines)
    return canvas


def _drop_oldest_node(canvas: str, label_re: re.Pattern[str]) -> str:
    """Drop the oldest user-arrow-target node from the canvas.

    We drop the second line (``User --> NODE``) and the corresponding
    node definition. The next ``prev --> NODE`` line gets re-pointed at
    ``User``.
    """
    lines = canvas.split("\n")
    if len(lines) < 4:
        return ""
    # Skip the header + User line; first arrow is lines[2], first
    # definition is lines[3] in our build order.
    arrow_idx = 2
    def_idx = 3
    if arrow_idx >= len(lines) or def_idx >= len(lines):
        return ""
    lines.pop(def_idx)
    lines.pop(arrow_idx)
    # Repoint the new first arrow at User.
    if len(lines) > 2 and "User" not in lines[2]:
        lines[2] = lines[2].split(" --> ", 1)[0]
        lines[2] = f"{lines[2]} --> User"
        # Actually we need to flip: the new first arrow should originate
        # from User. Original layout is "User --> N1", "N1 --> N2"… —
        # after dropping N1, we want "User --> N2".
        m = re.match(r'^(\s*)([a-f0-9]{8})\s*-->\s*([a-f0-9]{8})', lines[2])
        if m:
            lines[2] = f"{m.group(1)}User --> {m.group(3)}"
    return "\n".join(lines)


__all__ = [
    "FRAMEWORK_OVERHEAD_CHARS",
    "MAX_NODES",
    "MAX_SUMMARY_CHARS",
    "MAX_TOKENS",
    "build_canvas",
    "canvas_token_estimate",
]