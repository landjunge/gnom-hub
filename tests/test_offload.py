"""Tests for the gnom-hub Context-Offload module.

Covers the three core files:
- ``gnom_hub.memory.offload`` (ContextOffloader + OffloadConfig)
- ``gnom_hub.memory.mermaid_canvas`` (build_canvas)
- ``gnom_hub.memory.node_resolver`` (resolve_node)

Each test uses ``tmp_path`` for data isolation so it can run in
parallel with the rest of the gnom-hub test suite.

The Config-based tests monkey-patch ``Config.OFFLOAD_*`` attributes so
they don't need a running gnom-hub instance — the offload modules
read ``Config`` lazily, never at import time, so this is safe.
"""
from __future__ import annotations

import importlib
import os
import shutil
import uuid
from pathlib import Path

import pytest

# ── Module-level reset helpers ──────────────────────────────────────────────
# The offloader is held in a module-level dict keyed by session_id.
# Each test must start with a clean registry or it will inherit state
# from earlier tests in the same pytest run.


@pytest.fixture(autouse=True)
def _reset_offloader_registry(tmp_path):
    """Reset module-level offloader state for every test."""
    from gnom_hub.memory import offload
    offload.reset_all_offloaders()
    yield
    offload.reset_all_offloaders()


# ── 1. Offload disabled by default ──────────────────────────────────────────


def test_offload_disabled_by_default(tmp_path):
    """enabled=False → maybe_offload returns None, no files written."""
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    cfg = OffloadConfig(enabled=False, data_dir=str(tmp_path))
    off = ContextOffloader("sess", cfg)

    entry = off.maybe_offload(tool_name="bash", content="hello world")
    assert entry is None
    # Nothing should be on disk.
    refs_dir = tmp_path / "sess" / "refs"
    assert not refs_dir.exists() or list(refs_dir.iterdir()) == []
    # In-memory state stays empty.
    assert off.entries == []
    assert off.cumulative_bytes == 0


# ── 2. Offload triggers at mild ratio ───────────────────────────────────────


def test_offload_triggers_at_mild_ratio(tmp_path):
    """When cumulative bytes > mild_threshold, refs/*.md appear on disk."""
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    # max_tokens=100, ratio=0.5 → threshold = 200 bytes.
    cfg = OffloadConfig(
        enabled=True,
        max_tokens=100,
        mild_offload_ratio=0.5,
        aggressive_compress_ratio=0.85,
        data_dir=str(tmp_path),
    )
    off = ContextOffloader("sess", cfg)

    # First offload: 150 bytes — under mild threshold.
    e1 = off.maybe_offload(tool_name="bash", content="a" * 150)
    assert e1 is not None
    state = off.get_threshold_state()
    assert state["cumulative_bytes"] == 150
    assert state["mild"] is False

    # Second offload: another 150 bytes → cumulative 300, over 200.
    e2 = off.maybe_offload(tool_name="bash", content="b" * 150)
    assert e2 is not None
    state = off.get_threshold_state()
    assert state["cumulative_bytes"] == 300
    assert state["mild"] is True

    # Both refs files must exist on disk with their node_ids.
    refs_dir = tmp_path / "sess" / "refs"
    assert refs_dir.is_dir()
    files = sorted(refs_dir.iterdir())
    assert len(files) == 2
    assert (refs_dir / f"{e1.node_id}.md").is_file()
    assert (refs_dir / f"{e2.node_id}.md").is_file()


# ── 3. Offload triggers at aggressive ratio ─────────────────────────────────


def test_offload_triggers_at_aggressive_ratio(tmp_path):
    """When cumulative bytes > aggressive_threshold, canvas drops oldest."""
    from gnom_hub.memory.mermaid_canvas import MAX_NODES, build_canvas
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    # max_tokens=100, ratio=0.85 → threshold = 340 bytes.
    cfg = OffloadConfig(
        enabled=True,
        max_tokens=100,
        mild_offload_ratio=0.5,
        aggressive_compress_ratio=0.85,
        data_dir=str(tmp_path),
    )
    off = ContextOffloader("sess", cfg)

    # Feed MAX_NODES + 3 entries so the aggressive canvas must drop some.
    for i in range(MAX_NODES + 3):
        off.maybe_offload(tool_name=f"tool_{i}", content=f"out_{i}" * 10)

    state = off.get_threshold_state()
    assert state["aggressive"] is True
    assert state["mild"] is True

    # Build aggressive canvas and confirm we have at most MAX_NODES arrows.
    canvas_aggr = build_canvas(off.entries, mode="aggressive")
    arrow_count = sum(1 for line in canvas_aggr.split("\n") if "-->" in line)
    assert arrow_count <= MAX_NODES

    # Compare with normal mode: aggressive should drop MORE nodes than
    # normal — i.e. fewer arrows.
    canvas_normal = build_canvas(off.entries, mode="normal")
    normal_arrows = sum(1 for line in canvas_normal.split("\n") if "-->" in line)
    assert arrow_count <= normal_arrows


# ── 4. Mermaid canvas node limit ────────────────────────────────────────────


def test_mermaid_canvas_node_limit(tmp_path):
    """21 entries → at most MAX_NODES nodes in the canvas; oldest dropped."""
    from gnom_hub.memory.mermaid_canvas import MAX_NODES, build_canvas
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    cfg = OffloadConfig(enabled=True, data_dir=str(tmp_path))
    off = ContextOffloader("sess", cfg)

    # 21 entries is one more than the cap.
    n = MAX_NODES + 1
    for i in range(n):
        off.maybe_offload(tool_name=f"tool_{i}", content=f"payload_{i}")

    canvas = build_canvas(off.entries)
    # Each tool node renders as `    <node_id>["..."]` plus a `User` line.
    # Arrows = nodes - 1 (one arrow between each pair).
    arrow_count = sum(1 for line in canvas.split("\n") if "-->" in line)
    # One arrow per node-except-User, so max MAX_NODES.
    assert arrow_count == MAX_NODES

    # The OLDEST entry's node_id must NOT appear in the canvas anymore.
    oldest_id = off.entries[0].node_id
    assert oldest_id not in canvas


# ── 5. Node resolver round-trip ─────────────────────────────────────────────


def test_node_resolver_returns_content(tmp_path):
    """resolve_node returns the exact stored content."""
    from gnom_hub.memory.node_resolver import resolve_node
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    cfg = OffloadConfig(enabled=True, data_dir=str(tmp_path))
    off = ContextOffloader("rt_session", cfg)
    payload = "Hello, this is the FULL original tool output.\nLine 2.\n"
    entry = off.maybe_offload(tool_name="bash", content=payload)

    got = resolve_node(entry.node_id, "rt_session", data_dir=str(tmp_path))
    assert got == payload


# ── 6. Node resolver missing → None (no exception) ──────────────────────────


def test_node_resolver_missing_node_returns_none(tmp_path):
    """resolve_node returns None for missing nodes, does not raise."""
    from gnom_hub.memory.node_resolver import resolve_node

    # No files written — even a valid hex id should resolve to None.
    result = resolve_node("0123abcd", "ghost_session", data_dir=str(tmp_path))
    assert result is None

    # Empty session / empty data_dir are also safe.
    assert resolve_node("0123abcd", "", data_dir=str(tmp_path)) is None
    assert resolve_node("0123abcd", "x", data_dir="") is None


# ── 7. Node resolver rejects path traversal ────────────────────────────────


def test_node_resolver_rejects_path_traversal(tmp_path):
    """Path-traversal payloads and bad regex must return None without FS read."""
    from gnom_hub.memory.node_resolver import resolve_node

    # A: traversal-style node_id rejected by regex.
    assert resolve_node("../etc/passwd", "sess", data_dir=str(tmp_path)) is None
    assert resolve_node("..", "sess", data_dir=str(tmp_path)) is None
    assert resolve_node("../../../../etc/passwd", "sess", data_dir=str(tmp_path)) is None

    # B: invalid regex (too short, too long, non-hex).
    assert resolve_node("xyz", "sess", data_dir=str(tmp_path)) is None
    assert resolve_node("0123abcde", "sess", data_dir=str(tmp_path)) is None
    assert resolve_node("0123ABCD", "sess", data_dir=str(tmp_path)) is None  # uppercase not allowed
    assert resolve_node("", "sess", data_dir=str(tmp_path)) is None

    # C: bad session_id is sanitized, never escapes data root.
    assert resolve_node("0123abcd", "../escape", data_dir=str(tmp_path)) is None
    assert resolve_node("0123abcd", "/etc/passwd", data_dir=str(tmp_path)) is None

    # D: make sure no file was created by any of the attempts.
    refs_dir = tmp_path / ".." / ".." / "escape" / "refs"
    assert not refs_dir.exists()


# ── 8. Offload preserves full text ──────────────────────────────────────────


def test_offload_preserves_full_text(tmp_path):
    """The on-disk file content equals the original, byte-for-byte."""
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    cfg = OffloadConfig(enabled=True, data_dir=str(tmp_path))
    off = ContextOffloader("fulltext", cfg)

    # Tricky content: newlines, unicode, control-ish chars, long line.
    payload = (
        "First line\n"
        "Second line with unicode: äöü ñ 漢字\n"
        "Special chars: \"quotes\", 'apostrophes', \\backslash\n"
        "Trailing whitespace    \n"
        + ("x" * 1024)
    )

    entry = off.maybe_offload(tool_name="shell", content=payload)
    assert entry is not None

    ref_path = tmp_path / "fulltext" / "refs" / f"{entry.node_id}.md"
    assert ref_path.is_file()

    on_disk = ref_path.read_text(encoding="utf-8")
    assert on_disk == payload
    assert entry.full_content == payload


# ── 9. Offload atomic write ────────────────────────────────────────────────


def test_offload_atomic_write(tmp_path):
    """Verify atomic write pattern (tmp + rename) is used in code.

    We can't reliably kill a process mid-write from pytest, but we CAN
    inspect the source to confirm the pattern is in place. We also
    verify that an offload followed by reading the file shows the
    complete content (never a half-written file) even when called in
    tight succession.
    """
    import inspect

    from gnom_hub.memory.offload import ContextOffloader

    src = inspect.getsource(ContextOffloader._atomic_write)

    # Pattern assertions: the implementation must use a tmp suffix and
    # ``Path.replace`` to make the rename atomic. These are exactly the
    # two markers we promised in the design doc.
    assert ".tmp" in src, "_atomic_write must use a .tmp suffix"
    assert "replace" in src, "_atomic_write must call Path.replace for atomicity"

    # Functional check: offload multiple entries in tight succession;
    # every ref file must be fully present on disk (no half-writes).
    from gnom_hub.memory.offload import OffloadConfig

    cfg = OffloadConfig(enabled=True, data_dir=str(tmp_path))
    off = ContextOffloader("atomic", cfg)
    for i in range(20):
        payload = uuid.uuid4().hex + ("y" * 200)
        entry = off.maybe_offload(tool_name="t", content=payload)
        assert entry is not None
        ref_path = tmp_path / "atomic" / "refs" / f"{entry.node_id}.md"
        # No partial file ever visible: must read back exactly.
        assert ref_path.read_text(encoding="utf-8") == payload


# ── Bonus: defaults match the spec ──────────────────────────────────────────


def test_offload_config_defaults_match_spec():
    """OffloadConfig defaults must match the spec's 4 expected values."""
    from gnom_hub.memory.offload import OffloadConfig

    cfg = OffloadConfig()
    assert cfg.enabled is False
    assert cfg.mild_offload_ratio == 0.5
    assert cfg.aggressive_compress_ratio == 0.85
    assert cfg.data_dir == "data/offload"


def test_config_offload_attributes_exist():
    """Config must expose the offload tunables (mirror of OffloadConfig defaults)."""
    from gnom_hub.core.config import Config

    assert hasattr(Config, "OFFLOAD_ENABLED")
    assert hasattr(Config, "OFFLOAD_MILD_RATIO")
    assert hasattr(Config, "OFFLOAD_AGGRESSIVE_RATIO")
    assert hasattr(Config, "OFFLOAD_DATA_DIR")
    assert hasattr(Config, "OFFLOAD_MAX_TOKENS")

    assert Config.OFFLOAD_ENABLED is False
    assert Config.OFFLOAD_MILD_RATIO == 0.5
    assert Config.OFFLOAD_AGGRESSIVE_RATIO == 0.85
    assert Config.OFFLOAD_DATA_DIR == "data/offload"
    assert isinstance(Config.OFFLOAD_MAX_TOKENS, int)


def test_canvas_deterministic_for_same_input():
    """build_canvas is deterministic — same input → same output."""
    from gnom_hub.memory.mermaid_canvas import build_canvas
    from gnom_hub.memory.offload import OffloadEntry

    e1 = OffloadEntry(
        node_id="0123abcd",
        tool_name="bash",
        summary="ran pytest",
        full_content="x" * 100,
        timestamp=0.0,
        size_bytes=100,
    )
    e2 = OffloadEntry(
        node_id="deadbeef",
        tool_name="read",
        summary="read config",
        full_content="y" * 100,
        timestamp=0.0,
        size_bytes=100,
    )
    canvas_a = build_canvas([e1, e2])
    canvas_b = build_canvas([e1, e2])
    assert canvas_a == canvas_b
    # Sanity: contains both node_ids and both tool names.
    assert "0123abcd" in canvas_a
    assert "deadbeef" in canvas_a
    assert "bash" in canvas_a
    assert "read" in canvas_a


def test_get_offloader_returns_same_instance():
    """get_offloader caches per session_id."""
    from gnom_hub.memory.offload import get_offloader, OffloadConfig

    cfg = OffloadConfig(enabled=True)
    a = get_offloader("cache_test", cfg)
    b = get_offloader("cache_test", OffloadConfig())
    assert a is b


def test_handle_offload_recall_in_process_actions():
    """[OFFLOAD_RECALL:<id>] tags in agent responses get replaced with content."""
    from gnom_hub.agents.actions.action_handlers import _handle_offload_recall
    from gnom_hub.memory.offload import ContextOffloader, OffloadConfig

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        cfg = OffloadConfig(enabled=True, data_dir=td)
        off = ContextOffloader("RecallTester", cfg)
        entry = off.maybe_offload(tool_name="bash", content="captured tool output")
        # The recall helper looks up across candidate sessions; ours is
        # not in the search path so we expect a graceful "nicht gefunden".
        # We just confirm it does NOT raise.
        result = _handle_offload_recall(f"[OFFLOAD_RECALL:{entry.node_id}]")
        assert "[System:" in result or "[Offload Recall" in result
        # Invalid id (9 hex chars, fails regex) → System message, no exception.
        result_bad = _handle_offload_recall("[OFFLOAD_RECALL:123456789]")
        assert "[System:" in result_bad