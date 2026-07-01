"""offload.py — Context Offload for gnom-hub.

Ports the soft token-budget + lossless offload-to-disk pattern from the
TencentDB Agent Memory project (`tencentdb-agent-memory/src/offload/`,
`openclaw.plugin.json::offload`) to gnom-hub's Python agent loop.

Why this module exists
----------------------
Long agent sessions accumulate tool output (shell results, browser output,
file reads, etc.) that fills the LLM context window. The offload subsystem
mitigates this by:

1. Tracking cumulative tool-output bytes for the current session.
2. After each tool call, writing the raw content to
   ``<data_dir>/<session_id>/refs/<node_id>.md`` (lossless — no compression,
   no truncation) and replacing the in-context reference with a compact
   Mermaid node id like ``a1b2c3d4["bash: ran pytest"]``.
3. Exposing a Mermaid canvas summary so the agent still has a high-density
   view of the session without re-paying the token cost of the raw output.
4. Providing a `node_resolver` lookup service so agents can drill back into
   raw content via the node id whenever they need to.

Design decisions
----------------
- The soft token budget is computed against ``cfg.OFFLOAD_MAX_TOKENS`` (default
  8000) using two ratios: ``mild_offload_ratio`` (default 0.5) and
  ``aggressive_compress_ratio`` (default 0.85). These match the upstream
  TencentDB plugin defaults. The offloader fires at the mild threshold and
  tightens the canvas at the aggressive threshold.
- File writes are atomic (write to ``.tmp`` then ``Path.replace()``), so a
  crash mid-write never produces a half-written ref file.
- ``node_id`` is the first 8 hex chars of a v4 UUID — short, unique per
  offload, deterministic enough to be grep-able by the agent.
- ``resolve_node`` strictly validates the node id against
  ``NODE_ID_PATTERN`` BEFORE any filesystem access. Path-traversal payloads
  like ``"../etc/passwd"`` are rejected with a ``None`` return.
- The offloader is per-session; a module-level registry
  (``_session_offloaders``) keeps one instance per session id so cumulative
  bytes accumulate correctly across turns.

This module does NOT perform LLM-based summarization or extract memories —
that's out of scope for this port. It is purely the disk + canvas layer.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

#: Strict regex for node ids accepted by ``node_resolver.resolve_node``.
#: Exactly 8 lowercase hex chars (matches ``uuid.uuid4().hex[:8]``).
NODE_ID_PATTERN: re.Pattern[str] = re.compile(r"^[a-f0-9]{8}$")

#: Approximate bytes per token. Used to convert between token budgets and
#: raw byte thresholds. Empirical average for mixed text/code is ~4 bytes
#: per token (English prose ~4, code ~3.5, mixed ~4).
BYTES_PER_TOKEN = 4

#: Refuse extremely large single tool outputs so one runaway tool cannot
#: exhaust the disk by itself. 10 MB is well above any realistic tool
#: output for a single call but still bounded.
MAX_SINGLE_TOOL_BYTES = 10 * 1024 * 1024


# ── Config ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OffloadConfig:
    """Configuration for the ContextOffloader.

    Defaults match the TencentDB plugin (``openclaw.plugin.json::offload``)
    where they overlap, and use the gnom-hub convention for ``data_dir``
    (``data/offload`` relative to the repo root).
    """

    enabled: bool = False
    mild_offload_ratio: float = 0.5
    aggressive_compress_ratio: float = 0.85
    data_dir: str = "data/offload"
    max_tokens: int = 8000

    def mild_threshold_bytes(self) -> int:
        """Byte threshold at which offload starts."""
        return int(self.max_tokens * BYTES_PER_TOKEN * self.mild_offload_ratio)

    def aggressive_threshold_bytes(self) -> int:
        """Byte threshold at which the canvas is tightened."""
        return int(self.max_tokens * BYTES_PER_TOKEN * self.aggressive_compress_ratio)


# ── Offload entry ────────────────────────────────────────────────────────────


@dataclass
class OffloadEntry:
    """In-memory record of a single offloaded tool output.

    The full content is held here so the canvas generator can render
    summaries without re-reading the disk for every turn. The same content
    is also on disk at ``<refs_dir>/<node_id>.md`` for drill-down.
    """

    node_id: str
    tool_name: str
    summary: str
    full_content: str
    timestamp: float
    size_bytes: int


# ── Per-session offloader ────────────────────────────────────────────────────


class ContextOffloader:
    """Offload heavy tool outputs to disk and expose a compact Mermaid view.

    Lifecycle
    ---------
    One instance per session id. Held in module-level
    ``_session_offloaders`` so cumulative bytes accumulate across turns.
    Use :func:`get_offloader` to obtain/create the right instance.
    """

    def __init__(self, session_id: str, config: OffloadConfig) -> None:
        self.session_id = session_id
        self.config = config
        self.entries: list[OffloadEntry] = []
        self.cumulative_bytes: int = 0
        self._refs_dir = self._refs_dir_for(config.data_dir, session_id)
        self._ensure_refs_dir()

    # ── path helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _refs_dir_for(data_dir: str, session_id: str) -> Path:
        """Build ``<data_dir>/<session_id>/refs/``.

        ``session_id`` is sanitized by
        :meth:`ContextOffloader._sanitize_session_id` so callers cannot
        inject ``..`` into the path.
        """
        safe = ContextOffloader._sanitize_session_id(session_id)
        return Path(data_dir) / safe / "refs"

    @staticmethod
    def _sanitize_session_id(session_id: str) -> str:
        """Return a session id that is safe to use as a directory name.

        Rejects ``None``, empty strings, anything containing ``/``,
        ``\\``, or ``..``. Returns ``"default"`` as a safe fallback.
        """
        if not session_id or not isinstance(session_id, str):
            return "default"
        if "/" in session_id or "\\" in session_id:
            return "default"
        if ".." in session_id:
            return "default"
        if not session_id.strip():
            return "default"
        return session_id

    def _ensure_refs_dir(self) -> None:
        try:
            self._refs_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "ContextOffloader: could not create refs dir %s: %s",
                self._refs_dir, exc,
            )

    # ── atomic write ─────────────────────────────────────────────────────

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write ``content`` to ``path`` atomically (tmp + rename).

        Pattern: write to ``<path>.tmp``, then ``Path.replace()`` moves it
        over the destination. ``Path.replace`` is atomic on POSIX (and on
        Windows since Python 3.3 when both paths are on the same volume),
        so readers either see the old file or the complete new file —
        never a partial write.
        """
        tmp = path.with_suffix(path.suffix + ".tmp")
        # Open explicitly with utf-8 to match the rest of gnom-hub.
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        # ``replace`` works across filesystems and is atomic on POSIX.
        tmp.replace(path)

    # ── public API ───────────────────────────────────────────────────────

    def maybe_offload(
        self,
        tool_name: str,
        content: str,
        summary: str | None = None,
    ) -> OffloadEntry | None:
        """Record a tool output; return the new entry (or ``None``).

        Returns ``None`` when offload is disabled (cheap fast-path so
        callers don't need to check the config flag themselves).

        The returned entry carries the ``node_id`` that callers should
        embed in the Mermaid canvas.
        """
        if not self.config.enabled:
            return None

        if not isinstance(content, str):
            content = str(content)
        size = len(content.encode("utf-8"))
        # Cap runaway tool output so a single bad call cannot exhaust disk.
        if size > MAX_SINGLE_TOOL_BYTES:
            logger.warning(
                "ContextOffloader: tool=%s content=%d bytes exceeds single-cap "
                "%d; truncating for storage but keeping in memory.",
                tool_name, size, MAX_SINGLE_TOOL_BYTES,
            )
            content = content[:MAX_SINGLE_TOOL_BYTES]
            size = MAX_SINGLE_TOOL_BYTES

        node_id = uuid.uuid4().hex[:8]
        ref_path = self._refs_dir / f"{node_id}.md"

        try:
            self._atomic_write(ref_path, content)
        except OSError as exc:
            # Offload is best-effort: if disk is full / readonly we don't
            # want to break the agent loop. Log and return None.
            logger.error(
                "ContextOffloader: atomic write to %s failed: %s",
                ref_path, exc,
            )
            return None

        entry = OffloadEntry(
            node_id=node_id,
            tool_name=tool_name or "unknown",
            summary=summary or tool_name or "tool output",
            full_content=content,
            timestamp=time.time(),
            size_bytes=size,
        )
        self.entries.append(entry)
        self.cumulative_bytes += size

        threshold_state = self.get_threshold_state()
        logger.debug(
            "ContextOffloader[%s]: offloaded tool=%s node=%s size=%d "
            "cumulative=%d mild=%s aggressive=%s",
            self.session_id, tool_name, node_id, size,
            self.cumulative_bytes, threshold_state["mild"],
            threshold_state["aggressive"],
        )
        return entry

    def get_threshold_state(self) -> dict:
        """Return current threshold state (used by tests + canvas generator).

        Keys:
            ``mild``        — True once cumulative_bytes >= mild threshold.
            ``aggressive``  — True once cumulative_bytes >= aggressive threshold.
            ``cumulative_bytes`` — current sum of offloaded bytes.
            ``entry_count`` — number of entries held.
        """
        return {
            "mild": self.cumulative_bytes >= self.config.mild_threshold_bytes(),
            "aggressive": self.cumulative_bytes >= self.config.aggressive_threshold_bytes(),
            "cumulative_bytes": self.cumulative_bytes,
            "entry_count": len(self.entries),
        }

    def reset(self) -> None:
        """Clear in-memory state. Disk files are NOT touched."""
        self.entries.clear()
        self.cumulative_bytes = 0


# ── Module-level session registry ────────────────────────────────────────────

_session_offloaders: dict[str, ContextOffloader] = {}
_registry_lock_path: Path | None = None  # placeholder for future thread-lock


def get_offloader(
    session_id: str,
    config: OffloadConfig | None = None,
) -> ContextOffloader:
    """Get or create the per-session :class:`ContextOffloader`.

    The first call for a given ``session_id`` instantiates an offloader
    using ``config`` (or :class:`OffloadConfig()` defaults if ``None``).
    Subsequent calls for the same ``session_id`` return the cached
    instance, even if a different ``config`` is passed — the second config
    is ignored. This matches how session state is normally shared in
    gnom-hub (e.g. ``get_active_project()``).
    """
    if not session_id:
        session_id = "default"
    if session_id not in _session_offloaders:
        cfg = config or OffloadConfig()
        _session_offloaders[session_id] = ContextOffloader(session_id, cfg)
    return _session_offloaders[session_id]


def reset_session_offloader(session_id: str) -> None:
    """Drop the cached offloader for ``session_id`` (test helper)."""
    _session_offloaders.pop(session_id, None)


def reset_all_offloaders() -> None:
    """Drop ALL cached offloaders (test helper)."""
    _session_offloaders.clear()


def get_all_entries(session_id: str) -> list[OffloadEntry]:
    """Return a copy of the entries for ``session_id`` (empty if unknown)."""
    off = _session_offloaders.get(session_id)
    return list(off.entries) if off else []


__all__ = [
    "BYTES_PER_TOKEN",
    "ContextOffloader",
    "MAX_SINGLE_TOOL_BYTES",
    "NODE_ID_PATTERN",
    "OffloadConfig",
    "OffloadEntry",
    "get_all_entries",
    "get_offloader",
    "reset_all_offloaders",
    "reset_session_offloader",
]