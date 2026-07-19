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


def test_dispatch_only_restricts_user_fanout(tmp_path, monkeypatch):
    """User plan with nested @Workers must not queue every worker when only=GeneralAG."""
    import sqlite3

    db = tmp_path / "fanout.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE agents (
            name TEXT PRIMARY KEY, status TEXT
        );
        CREATE TABLE agent_messages (
            id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, payload TEXT,
            priority INTEGER, status TEXT DEFAULT 'pending', retry_count INTEGER DEFAULT 0,
            created_at REAL, deliver_after REAL DEFAULT 0, context_id TEXT,
            depth INTEGER DEFAULT 0, processing_since REAL, parent_msg_id INTEGER,
            completed_at REAL
        );
        """
    )
    for n in ("GeneralAG", "CoderAG", "WriterAG", "ResearcherAG", "EditorAG"):
        conn.execute("INSERT INTO agents(name,status) VALUES (?,?)", (n, "online"))
    conn.commit()
    conn.close()

    from gnom_hub.agents.swarm import swarm_comms as sc

    def _conn():
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(sc, "get_db_connection", _conn)
    monkeypatch.setattr(sc, "notify_agent", lambda *_a, **_k: None)

    plan = (
        "@GeneralAG SUPERVISOR plan\n"
        "@ResearcherAG [READ: x]\n"
        "@CoderAG [WRITE: v1/index.html]\n"
        "@WriterAG [WRITE: overview.html]\n"
        "@EditorAG [VERIFY: v1/index.html]\n"
    )
    got = sc.dispatch_mention(
        "user", plan, "default", str(db), only=["GeneralAG"]
    )
    assert got == ["GeneralAG"], got

    c = sqlite3.connect(str(db))
    rows = c.execute("SELECT recipient FROM agent_messages ORDER BY id").fetchall()
    c.close()
    assert [r[0] for r in rows] == ["GeneralAG"]


def test_dispatch_generalag_still_slices_workers(tmp_path, monkeypatch):
    """GeneralAG multi-@ without only= still slices to each worker."""
    import sqlite3

    db = tmp_path / "slice.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE agents (name TEXT PRIMARY KEY, status TEXT);
        CREATE TABLE agent_messages (
            id INTEGER PRIMARY KEY, sender TEXT, recipient TEXT, payload TEXT,
            priority INTEGER, status TEXT DEFAULT 'pending', retry_count INTEGER DEFAULT 0,
            created_at REAL, deliver_after REAL DEFAULT 0, context_id TEXT,
            depth INTEGER DEFAULT 0, processing_since REAL, parent_msg_id INTEGER,
            completed_at REAL
        );
        """
    )
    for n in ("CoderAG", "WriterAG"):
        conn.execute("INSERT INTO agents(name,status) VALUES (?,?)", (n, "online"))
    conn.commit()
    conn.close()

    from gnom_hub.agents.swarm import swarm_comms as sc
    import json

    def _conn():
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(sc, "get_db_connection", _conn)
    monkeypatch.setattr(sc, "notify_agent", lambda *_a, **_k: None)

    text = "@CoderAG write v1\n@WriterAG write overview\n"
    got = sc.dispatch_mention("GeneralAG", text, "default", str(db))
    assert set(got) == {"CoderAG", "WriterAG"}
    c = sqlite3.connect(str(db))
    for rec, payload in c.execute("SELECT recipient, payload FROM agent_messages"):
        body = json.loads(payload)["text"]
        if rec == "CoderAG":
            assert "write v1" in body
            assert "@WriterAG" not in body
        if rec == "WriterAG":
            assert "write overview" in body
            assert "@CoderAG" not in body
    c.close()
