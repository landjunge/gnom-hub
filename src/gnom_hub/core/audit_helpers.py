"""audit_helpers.py — Dünne Wrapper um log_audit_event mit festen Vokabular.

Ziel: einheitliche `event_type`-Namen für `audit_log`, damit nachher
per SQL einfach aggregierbar (GROUP BY event_type). Bei DB-Fehler
no-op (log_audit_event selbst failt auch nicht hart).
"""
from __future__ import annotations

import logging
from typing import Any

try:
    from gnom_hub.core.structured_log import get_trace_id
    from gnom_hub.db import log_audit_event
except Exception:  # pragma: no cover — DB noch nicht initialisiert
    log_audit_event = None  # type: ignore
    get_trace_id = lambda: None  # type: ignore


_log = logging.getLogger(__name__)


# ── Vokabular (siehe memory/gnom-hub-context für Quellen) ────────────────────
#   block            — Pfad-Validator hat Schreibzugriff verweigert
#   write_fail       — Datei konnte nicht geschrieben werden (IO/perm/parse)
#   blockade_change  — Admin-Endpoint hat Blockade-Level geändert
#   llm_call         — schon in router.py geloggt (success + failed)
#   cooldown         — Rate-Limit-Throttle (noch nicht implementiert, Slot)


def record_block(agent: str, *, path: str, reason: str, level: int | None = None,
                 **extra: Any) -> None:
    """Pfad-Validator hat blockiert. Schreibt ein `block`-Event."""
    if log_audit_event is None:
        return
    details = {"path": path, "reason": reason}
    if level is not None:
        details["blockade_level"] = level
    details.update(extra)
    try:
        log_audit_event(agent, "block", details, get_trace_id())
    except Exception as e:  # pragma: no cover
        _log.warning("audit_helpers.record_block failed: %s", e)


def record_write_fail(agent: str, *, path: str, error: str, **extra: Any) -> None:
    """Schreibvorgang fehlgeschlagen. Schreibt ein `write_fail`-Event."""
    if log_audit_event is None:
        return
    details = {"path": path, "error": error[:500]}
    details.update(extra)
    try:
        log_audit_event(agent, "write_fail", details, get_trace_id())
    except Exception as e:  # pragma: no cover
        _log.warning("audit_helpers.record_write_fail failed: %s", e)


def record_blockade_change(actor: str, *, old_level: int, new_level: int,
                           **extra: Any) -> None:
    """Admin-Endpoint hat den Blockade-Level geändert."""
    if log_audit_event is None:
        return
    details = {"from": old_level, "to": new_level}
    details.update(extra)
    try:
        log_audit_event(actor, "blockade_change", details, get_trace_id())
    except Exception as e:  # pragma: no cover
        _log.warning("audit_helpers.record_blockade_change failed: %s", e)


def record_cooldown(agent: str, *, reason: str, duration_s: float,
                    **extra: Any) -> None:
    """Rate-Limit hat einen Agent gebremst. Slot für künftigen Cooldown-Decorator."""
    if log_audit_event is None:
        return
    details = {"reason": reason, "duration_s": duration_s}
    details.update(extra)
    try:
        log_audit_event(agent, "cooldown", details, get_trace_id())
    except Exception as e:  # pragma: no cover
        _log.warning("audit_helpers.record_cooldown failed: %s", e)


__all__ = [
    "record_block",
    "record_write_fail",
    "record_blockade_change",
    "record_cooldown",
]
