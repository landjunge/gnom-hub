"""node_resolver.py — Lookup service for offloaded tool-output refs.

Given a ``node_id`` (8 hex chars) and a ``session_id``, read the
offloaded content from ``<data_dir>/<session_id>/refs/<node_id>.md``
and return the full body as a string.

Security
--------
The resolver is callable by agents (via the ``offload_recall`` action
tag) so it MUST defend against path-traversal payloads. The defense is
layered:

1. ``node_id`` is matched against ``NODE_ID_PATTERN`` (strict regex
   ``^[a-f0-9]{8}$``) BEFORE any filesystem access. Any non-conforming
   input is rejected with ``None`` — no exception is raised.
2. ``session_id`` is passed through
   :func:`gnom_hub.memory.offload.ContextOffloader._sanitize_session_id`
   to strip ``/``, ``\\``, and ``..`` segments. Anything unsafe falls
   back to ``"default"``.
3. The constructed path is resolved and re-checked against the data
   root. If the resolved path escapes the data root, ``None`` is
   returned. This is a defense-in-depth check for symlinks or unusual
   edge cases.

The function never raises on missing files or invalid input — it
returns ``None`` so the calling agent code can produce a graceful
``[System: node not found]`` reply.
"""
from __future__ import annotations

import logging
from pathlib import Path

from gnom_hub.memory.offload import NODE_ID_PATTERN

logger = logging.getLogger(__name__)


def resolve_node(
    node_id: str,
    session_id: str,
    data_dir: str = "data/offload",
) -> str | None:
    """Return the offloaded content for ``node_id`` or ``None``.

    Parameters
    ----------
    node_id
        Exactly 8 lowercase hex chars (e.g. ``"a1b2c3d4"``). Any other
        value is rejected without touching the filesystem.
    session_id
        The session that produced the offload. Sanitized internally;
        ``None`` or values containing path separators or ``..`` fall
        back to ``"default"``.
    data_dir
        Root directory of the offload store. Defaults to
        ``"data/offload"`` (relative to the gnom-hub repo root). Can be
        overridden for tests.

    Returns
    -------
    The full file body as a UTF-8 string, or ``None`` if the file does
    not exist, the ``node_id`` fails the regex, or any other error
    occurs (logged at ``DEBUG``).
    """
    # Layer 1: strict regex. We MUST do this BEFORE any FS access so a
    # malicious node_id never even reaches the filesystem.
    if not isinstance(node_id, str) or not NODE_ID_PATTERN.match(node_id):
        logger.debug("resolve_node: rejected node_id=%r (regex mismatch)", node_id)
        return None

    # Layer 2: sanitize session_id via the same helper the offloader
    # uses, so attacker can't sneak ../ into the directory path.
    safe_session = _sanitize_session_id(session_id)
    safe_data_dir = _sanitize_data_dir(data_dir)

    # Layer 3: build the path and verify it stays under the data root.
    ref_path = Path(safe_data_dir) / safe_session / "refs" / f"{node_id}.md"
    try:
        # ``resolve`` follows symlinks; ``relative_to`` then confirms
        # we did not escape the root.
        resolved = ref_path.resolve(strict=False)
        root_resolved = Path(safe_data_dir).resolve(strict=False)
        try:
            resolved.relative_to(root_resolved)
        except ValueError:
            logger.warning(
                "resolve_node: resolved path %s escaped data root %s",
                resolved, root_resolved,
            )
            return None

        if not resolved.is_file():
            logger.debug("resolve_node: file not found at %s", resolved)
            return None
        return resolved.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("resolve_node: read failed for %s: %s", ref_path, exc)
        return None


def _sanitize_session_id(session_id: str) -> str:
    """Mirror of :meth:`ContextOffloader._sanitize_session_id` (private)."""
    if not session_id or not isinstance(session_id, str):
        return "default"
    if "/" in session_id or "\\" in session_id:
        return "default"
    if ".." in session_id:
        return "default"
    if not session_id.strip():
        return "default"
    return session_id


def _sanitize_data_dir(data_dir: str) -> str:
    """Sanitize the data_dir path. Reject obviously unsafe values."""
    if not data_dir or not isinstance(data_dir, str):
        return "data/offload"
    # We allow absolute paths so production deployments can point at
    # their own storage, but we block anything that looks like an
    # obvious traversal attempt.
    if "\x00" in data_dir:
        return "data/offload"
    return data_dir


__all__ = ["resolve_node"]