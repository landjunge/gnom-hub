"""Honest agent health: process alive + heartbeat age + queue depths.

DB ``status`` alone is a lie when the process died or heartbeats stalled.
This module is the single source for operator-facing health.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Heartbeat older than this while process claims online → stale/zombie.
HEARTBEAT_STALE_S = 90.0
# Soft warn threshold (UI can show yellow).
HEARTBEAT_WARN_S = 45.0


def _parse_last_seen(last_seen: Any) -> float | None:
    if last_seen is None:
        return None
    if isinstance(last_seen, (int, float)):
        return float(last_seen)
    s = str(last_seen).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _process_alive(agent_name: str) -> bool:
    """True if a live process matches this agent (PID file or cmdline)."""
    try:
        from gnom_hub.infrastructure.process.process_manager import _get_proc
        p = _get_proc(agent_name)
        if p is not None and p.is_running():
            return True
    except Exception as e:
        logger.debug("process check failed for %s: %s", agent_name, e)
    # Fallback: any cmdline with agents.run_agent --name <name>
    try:
        import psutil
        needle = agent_name.lower()
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmd = " ".join(proc.info.get("cmdline") or []).lower()
                if "run_agent" in cmd and needle in cmd:
                    return True
                if f"agents.{needle}" in cmd or f"agents.{agent_name}" in cmd:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.debug("psutil scan failed: %s", e)
    return False


def _queue_counts(conn, recipient: str) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS cnt
        FROM agent_messages
        WHERE recipient = ?
          AND status IN ('pending', 'processing', 'dead_letter')
        GROUP BY status
        """,
        (recipient,),
    ).fetchall()
    out = {"pending": 0, "processing": 0, "dead_letter": 0}
    for r in rows:
        st = r["status"] if hasattr(r, "keys") else r[0]
        cnt = r["cnt"] if hasattr(r, "keys") else r[1]
        if st in out:
            out[st] = int(cnt)
    return out


def build_agent_health_entry(
    name: str,
    db_status: str,
    last_seen: Any,
    conn,
    now: float | None = None,
) -> dict[str, Any]:
    """Build one agent health dict."""
    now = now if now is not None else time.time()
    db_status = (db_status or "offline").lower()
    if db_status == "running":
        db_status = "online"

    alive = _process_alive(name)
    ts = _parse_last_seen(last_seen)
    age = (now - ts) if ts is not None else None
    q = _queue_counts(conn, name)

    issues: list[str] = []
    if db_status in ("online", "busy", "paused") and not alive:
        issues.append("process_dead")
    if alive and age is not None and age > HEARTBEAT_STALE_S:
        issues.append("heartbeat_stale")
    if alive and age is None:
        issues.append("heartbeat_missing")
    if not alive and db_status == "offline":
        pass  # consistent offline
    if q["dead_letter"] > 0:
        issues.append("has_dead_letters")
    if q["processing"] > 0 and not alive:
        issues.append("stuck_processing_no_process")

    # Effective status for UI (honest)
    if not alive and db_status != "offline":
        effective = "zombie"  # DB says online, process gone
    elif alive and age is not None and age > HEARTBEAT_STALE_S:
        effective = "stale"
    elif alive and db_status == "busy":
        effective = "busy"
    elif alive and db_status == "paused":
        effective = "paused"
    elif alive:
        effective = "online"
    else:
        effective = "offline"

    healthy = effective in ("online", "busy", "paused") and "process_dead" not in issues and "heartbeat_stale" not in issues

    return {
        "name": name,
        "db_status": db_status,
        "effective_status": effective,
        "healthy": healthy,
        "process_alive": alive,
        "heartbeat_age_s": round(age, 1) if age is not None else None,
        "last_seen": last_seen,
        "queue": q,
        "issues": issues,
    }


def collect_all_agent_health() -> dict[str, Any]:
    """Snapshot for GET /api/agents/health and enriched /api/health."""
    from gnom_hub.db.connection import get_db_connection

    now = time.time()
    agents_out: list[dict] = []
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT name, status, last_seen FROM agents ORDER BY name"
        ).fetchall()
        for r in rows:
            name = r["name"] if hasattr(r, "keys") else r[0]
            status = r["status"] if hasattr(r, "keys") else r[1]
            last_seen = r["last_seen"] if hasattr(r, "keys") else r[2]
            agents_out.append(
                build_agent_health_entry(name, status, last_seen, conn, now=now)
            )

    healthy_n = sum(1 for a in agents_out if a["healthy"])
    zombie_n = sum(1 for a in agents_out if a["effective_status"] == "zombie")
    stale_n = sum(1 for a in agents_out if a["effective_status"] == "stale")
    offline_n = sum(1 for a in agents_out if a["effective_status"] == "offline")
    pending_total = sum(a["queue"]["pending"] for a in agents_out)
    processing_total = sum(a["queue"]["processing"] for a in agents_out)
    dlq_total = sum(a["queue"]["dead_letter"] for a in agents_out)

    overall = "ok"
    if zombie_n or stale_n:
        overall = "degraded"
    if healthy_n == 0 and agents_out:
        overall = "down"

    return {
        "status": overall,
        "ts": now,
        "summary": {
            "total": len(agents_out),
            "healthy": healthy_n,
            "zombie": zombie_n,
            "stale": stale_n,
            "offline": offline_n,
            "pending": pending_total,
            "processing": processing_total,
            "dead_letter": dlq_total,
        },
        "agents": agents_out,
    }
