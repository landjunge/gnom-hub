"""Supervisor-report fixes: Soul auto-dispatch off, flock dispatch, stuck recovery."""
from __future__ import annotations

import inspect
import time



def test_soul_auto_dispatch_default_off():
    src = inspect.getsource(
        __import__("gnom_hub.soul.soul", fromlist=["SoulAG"]).SoulAG._ex
    )
    assert 'SOUL_AUTO_DISPATCH' in src
    assert '"0"' in src or "'0'" in src


def test_soul_nudge_gated_on_auto_dispatch():
    src = inspect.getsource(
        __import__("gnom_hub.soul.soul", fromlist=["SoulAG"]).SoulAG._nudge_loop
    )
    assert "SOUL_AUTO_DISPATCH" in src


def test_dispatch_uses_cross_process_lock():
    from gnom_hub.agents.swarm import swarm_comms as sc

    src = inspect.getsource(sc.dispatch_mention)
    assert "cross_process_write_lock" in src
    assert "range(5)" in src


def test_recover_stuck_default_timeout_120():
    from gnom_hub.agents.swarm.swarm_comms import recover_stuck_messages

    sig = inspect.signature(recover_stuck_messages)
    assert sig.parameters["timeout"].default == 120.0


def test_recover_stuck_requeues_old_processing(tmp_path, monkeypatch):
    """Stuck processing row becomes pending after recovery."""
    import sqlite3

    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE agent_messages (
            id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, payload TEXT,
            priority INTEGER, status TEXT, retry_count INTEGER DEFAULT 0,
            created_at REAL, deliver_after REAL DEFAULT 0, context_id TEXT,
            depth INTEGER DEFAULT 0, processing_since REAL, parent_msg_id INTEGER,
            completed_at REAL
        )"""
    )
    old = time.time() - 200
    conn.execute(
        """INSERT INTO agent_messages
           (sender, recipient, payload, priority, status, retry_count, created_at, processing_since)
           VALUES ('user','GeneralAG','{}',5,'processing',0,?,?)""",
        (old, old),
    )
    conn.commit()
    conn.close()

    from gnom_hub.agents.swarm import swarm_comms as sc

    def _conn():
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(sc, "get_db_connection", _conn)
    sc.recover_stuck_messages(str(db), timeout=120.0)
    c = sqlite3.connect(str(db))
    st, rc = c.execute("SELECT status, retry_count FROM agent_messages WHERE id=1").fetchone()
    c.close()
    assert st == "pending"
    assert rc == 1


def test_flock_helper_works():
    from gnom_hub.db.db_lock import cross_process_write_lock

    with cross_process_write_lock(timeout_s=1.0):
        x = 1
    assert x == 1


def test_slice_text_for_mention_isolates_agents():
    from gnom_hub.agents.swarm.swarm_comms import _slice_text_for_mention
    text = (
        "@ResearcherAG Lies README.\n"
        "@CoderAG Baue v1.html aus README.\n"
        "@WriterAG Baue overview.html\n"
    )
    c = _slice_text_for_mention(text, "CoderAG")
    assert "Baue v1" in c
    assert "@ResearcherAG" not in c
    assert "@WriterAG" not in c
