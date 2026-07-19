"""Wave A: queue hygiene, concurrent hard limit, clear_queue."""
from __future__ import annotations

import json
import time

from gnom_hub.agents.swarm.swarm_comms import (
    MAX_CONCURRENT,
    MAX_QUEUE_DEPTH,
    can_accept_message,
    clear_queue,
    recover_stuck_messages,
)
from gnom_hub.db.connection import get_db_connection


def test_max_queue_depth_is_wave_a_cap():
    assert MAX_QUEUE_DEPTH <= 25
    assert MAX_CONCURRENT <= 3


def test_can_accept_hard_concurrent(isolated_db):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO agents (name, id, status, last_seen) VALUES (?,?,?,?)",
            ("CoderAG", "c1", "online", "t"),
        )
        now = time.time()
        for i in range(MAX_CONCURRENT):
            conn.execute(
                """
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, status, created_at, deliver_after, depth, processing_since)
                VALUES ('u', 'CoderAG', ?, 5, 'processing', ?, 0, 0, ?)
                """,
                (json.dumps({"text": f"p{i}"}), now, now),
            )
        conn.commit()
        assert can_accept_message("CoderAG", conn) is False
    finally:
        conn.close()


def test_clear_queue_moves_pending(isolated_db):
    conn = get_db_connection()
    try:
        now = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO agents (name, id, status, last_seen) VALUES (?,?,?,?)",
            ("WriterAG", "w1", "online", "t"),
        )
        for i in range(5):
            conn.execute(
                """
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, status, created_at, deliver_after, depth)
                VALUES ('u', 'WriterAG', ?, 5, 'pending', ?, 0, 0)
                """,
                (json.dumps({"text": f"q{i}"}), now),
            )
        conn.commit()
    finally:
        conn.close()

    r = clear_queue(statuses=("pending",), recipient="WriterAG")
    assert r["moved_to_dlq"] == 5

    conn = get_db_connection()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE status='pending' AND recipient='WriterAG'"
        ).fetchone()[0]
        assert n == 0
        dlq = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE status='dead_letter' AND recipient='WriterAG'"
        ).fetchone()[0]
        assert dlq == 5
    finally:
        conn.close()


def test_recover_dlq_stale_pending(isolated_db):
    conn = get_db_connection()
    try:
        now = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO agents (name, id, status, last_seen) VALUES (?,?,?,?)",
            ("CoderAG", "c1", "online", "t"),
        )
        conn.execute(
            """
            INSERT INTO agent_messages
                (sender, recipient, payload, priority, status, created_at, deliver_after, depth)
            VALUES ('u', 'CoderAG', ?, 5, 'pending', ?, 0, 0)
            """,
            (json.dumps({"text": "old"}), now - 900),
        )
        conn.commit()
    finally:
        conn.close()

    from gnom_hub.core.config import DB_PATH

    recover_stuck_messages(str(DB_PATH), timeout=300.0)
    conn = get_db_connection()
    try:
        st = conn.execute(
            "SELECT status FROM agent_messages WHERE payload LIKE '%old%'"
        ).fetchone()["status"]
        assert st == "dead_letter"
    finally:
        conn.close()
