"""Honest agent health: process + heartbeat + queue."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import patch

from gnom_hub.infrastructure.agent_health import (
    HEARTBEAT_STALE_S,
    build_agent_health_entry,
    collect_all_agent_health,
)


class _FakeConn:
    def __init__(self, queue_rows=None):
        self._queue_rows = queue_rows or []

    def execute(self, sql, params=None):
        class R:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

            def fetchone(self):
                return self._rows[0] if self._rows else None

        if "agent_messages" in sql and "GROUP BY" in sql:
            return R(self._queue_rows)
        return R([])


def test_zombie_when_db_online_process_dead():
    conn = _FakeConn()
    with patch("gnom_hub.infrastructure.agent_health._process_alive", return_value=False):
        h = build_agent_health_entry(
            "CoderAG",
            "online",
            datetime.now(timezone.utc).isoformat(),
            conn,
        )
    assert h["effective_status"] == "zombie"
    assert h["healthy"] is False
    assert "process_dead" in h["issues"]


def test_online_when_process_alive_fresh_heartbeat():
    conn = _FakeConn()
    now = time.time()
    with patch("gnom_hub.infrastructure.agent_health._process_alive", return_value=True):
        h = build_agent_health_entry(
            "GeneralAG",
            "online",
            datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            conn,
            now=now,
        )
    assert h["effective_status"] == "online"
    assert h["healthy"] is True
    assert h["process_alive"] is True


def test_stale_when_heartbeat_old():
    conn = _FakeConn()
    now = time.time()
    old = datetime.fromtimestamp(now - HEARTBEAT_STALE_S - 10, tz=timezone.utc).isoformat()
    with patch("gnom_hub.infrastructure.agent_health._process_alive", return_value=True):
        h = build_agent_health_entry("WriterAG", "online", old, conn, now=now)
    assert h["effective_status"] == "stale"
    assert "heartbeat_stale" in h["issues"]


def test_queue_counts_included():
    # sqlite Row-like dicts
    rows = [
        {"status": "pending", "cnt": 3},
        {"status": "processing", "cnt": 1},
        {"status": "dead_letter", "cnt": 2},
    ]
    conn = _FakeConn(queue_rows=rows)
    with patch("gnom_hub.infrastructure.agent_health._process_alive", return_value=True):
        h = build_agent_health_entry(
            "EditorAG",
            "busy",
            datetime.now(timezone.utc).isoformat(),
            conn,
        )
    assert h["queue"]["pending"] == 3
    assert h["queue"]["processing"] == 1
    assert h["queue"]["dead_letter"] == 2
    assert "has_dead_letters" in h["issues"]


def test_collect_all_uses_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GNOM_HUB_DB", str(tmp_path / "h.db"))
    from gnom_hub.core import config as cfg
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "h.db")
    monkeypatch.setattr(cfg.Config, "DB_PATH", tmp_path / "h.db")
    from gnom_hub.db.schema import create_tables
    create_tables()
    from gnom_hub.db.connection import get_db_connection
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO agents (name, id, status, last_seen) VALUES (?,?,?,?)",
            ("CoderAG", "id-c", "online", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    with patch("gnom_hub.infrastructure.agent_health._process_alive", return_value=False):
        snap = collect_all_agent_health()
    assert snap["summary"]["total"] >= 1
    names = [a["name"] for a in snap["agents"]]
    assert "CoderAG" in names
