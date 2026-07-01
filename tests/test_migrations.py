"""Tests for the versioned migration-history system.

These tests use real sqlite3 databases in a tmpdir (never the live DB) and
exercise the public API of :mod:`gnom_hub.db.migrations`.

Coverage:
    1. Fresh DB — every migration is applied, every expected table exists.
    2. Bootstrap mode — pre-existing DB without ``schema_migrations`` is
       recognised and all migrations are recorded as applied WITHOUT
       clobbering existing data.
    3. Idempotency — running the runner multiple times is a no-op after the
       first call (no duplicate ``schema_migrations`` rows).
    4. Numeric ordering — migrations are applied in ascending version order
       even when the on-disk filename order would otherwise differ.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# Ensure tests don't accidentally touch the user's live DB.
os.environ["GNOM_HUB_ENV"] = "test"
os.environ["TESTING"] = "true"

from gnom_hub.db.migrations import (  # noqa: E402  (after env-var set)
    DEFAULT_MIGRATIONS_DIR,
    apply_pending_migrations,
    get_migration_status,
    list_migration_files,
)

# Tables that should exist after a clean run of every migration.
EXPECTED_TABLES = {
    "schema_migrations",
    "state",
    "agents",
    "chat",
    "soul_memory",
    "general_memory",
    "audit_log",
    "blockade_log",
    "security_audit_log",
    "security_permissions",
    "watchdog_blockades",
    "prompt_versions",
    "capabilities",
    "showbox_presentations",
    "explainable_outputs",
    "graceful_degradation_failures",
    "token_budget_logs",
    "token_budget_alerts",
    "agent_messages",
    "swarm_callbacks",
    "agent_capabilities",
    "workflows",
    "workflow_tasks",
    "soul_tasks",
    "generalag_discussions",
    "generalag_outcomes",
    "generalag_pending",
    "generalag_worker_profile",
    "generalag_preset_history",
}


def _open_db(path: Path) -> sqlite3.Connection:
    """Open a sqlite3 connection with row-factory set."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _apply_and_commit(conn: sqlite3.Connection, **kwargs):
    """Run the migration runner and commit (caller-driven transaction model)."""
    result = apply_pending_migrations(conn, **kwargs)
    conn.commit()
    return result


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r["name"] for r in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: fresh DB — every migration applied, every expected table exists
# ─────────────────────────────────────────────────────────────────────────────
def test_fresh_db_applies_all_migrations(tmp_path: Path):
    db = tmp_path / "fresh.db"
    conn = _open_db(db)
    try:
        touched = _apply_and_commit(conn)
        statuses = [t["status"] for t in touched]
        assert statuses.count("applied") == 6, f"expected 6 applied, got {statuses}"
        assert "skipped" not in statuses
        assert "bootstrap" not in statuses

        # All 6 migrations now show up in status
        status = get_migration_status(conn)
        assert len(status["applied"]) == 6
        assert status["pending"] == []

        # Every expected table exists
        tables = _existing_tables(conn)
        missing = EXPECTED_TABLES - tables
        assert not missing, f"missing tables after fresh run: {missing}"

        # agent_messages has the full column set from migration 001
        cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(agent_messages)").fetchall()
        }
        for col in ("processing_since", "parent_msg_id", "completed_at"):
            assert col in cols, f"agent_messages.{col} missing"
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: bootstrap mode — existing DB without schema_migrations
# ─────────────────────────────────────────────────────────────────────────────
def test_bootstrap_existing_db_no_data_loss(tmp_path: Path):
    db = tmp_path / "legacy.db"
    conn = _open_db(db)
    try:
        # Simulate a pre-migration-system DB. Real legacy DBs were created
        # via the old SCHEMA_SQL Python string (now retired), so they have
        # the full column set on each table — just without any
        # ``schema_migrations`` tracking. The agents table here uses an
        # OLDER column set (no circuit_state / consecutive_failures) to
        # exercise the ALTER TABLE ADD COLUMN path on a partial schema.
        conn.execute("""
            CREATE TABLE agents (
                name TEXT PRIMARY KEY,
                id TEXT NOT NULL UNIQUE,
                port INTEGER DEFAULT 0,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'offline',
                capabilities TEXT DEFAULT '[]',
                role TEXT DEFAULT 'normal',
                active_job TEXT DEFAULT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO agents (name, id, status, last_seen) "
            "VALUES ('CoderAG', 'id-coder', 'online', '2026-01-01T00:00:00Z'), "
            "       ('WriterAG', 'id-writer', 'online', '2026-01-01T00:00:00Z')"
        )
        conn.execute("""
            CREATE TABLE chat (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL DEFAULT 'default',
                sender TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'chat',
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute(
            "INSERT INTO chat (id, sender, agent_id, content, timestamp) "
            "VALUES ('msg-1', 'user', 'coderag', 'hi', '2026-01-01T00:00:00Z')"
        )
        conn.commit()

        # No schema_migrations table yet, no migrations applied
        assert "schema_migrations" not in _existing_tables(conn)

        touched = _apply_and_commit(conn)

        # All 6 migrations should be recorded as bootstrap (not applied)
        bootstrap_count = sum(1 for t in touched if t["status"] == "bootstrap")
        assert bootstrap_count == 6, (
            f"expected 6 bootstrap entries, got statuses={[t['status'] for t in touched]}"
        )

        status = get_migration_status(conn)
        assert len(status["applied"]) == 6
        assert status["pending"] == []

        # Original data preserved (with realistic schema columns)
        agents = {
            (r["name"], r["status"])
            for r in conn.execute("SELECT name, status FROM agents").fetchall()
        }
        assert agents == {
            ("CoderAG", "online"),
            ("WriterAG", "online"),
        }, f"agents data lost: {agents}"
        chat_ids = {
            r["id"]
            for r in conn.execute("SELECT id FROM chat").fetchall()
        }
        assert chat_ids == {"msg-1"}, f"chat data lost: {chat_ids}"

        # New tables from migrations ARE auto-created during bootstrap — this
        # is the whole point of re-executing the SQL with benign-error
        # tolerance. Without creating generalag_discussions, code that
        # depends on it would fail with "no such table" on a legacy DB.
        tables = _existing_tables(conn)
        for expected in (
            "generalag_discussions",
            "generalag_outcomes",
            "generalag_pending",
            "generalag_worker_profile",
            "generalag_preset_history",
            "workflows",
            "soul_tasks",
            "schema_migrations",
        ):
            assert expected in tables, (
                f"bootstrap should have created {expected}, tables={sorted(tables)}"
            )

        # Columns that the legacy `agents` was missing are now present
        # (ALTER TABLE ADD COLUMN ran during bootstrap).
        agents_cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(agents)").fetchall()
        }
        for col in ("circuit_state", "consecutive_failures"):
            assert col in agents_cols, (
                f"bootstrap should have added agents.{col}, "
                f"got columns={sorted(agents_cols)}"
            )
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: idempotency — running twice is a no-op
# ─────────────────────────────────────────────────────────────────────────────
def test_idempotent_double_init(tmp_path: Path):
    db = tmp_path / "idempotent.db"
    conn = _open_db(db)
    try:
        # First call — applies everything
        first = _apply_and_commit(conn)
        first_applied = sum(1 for t in first if t["status"] == "applied")
        assert first_applied == 6

        # Second call — every migration should be skipped
        second = _apply_and_commit(conn)
        for entry in second:
            assert entry["status"] == "skipped", (
                f"re-run should skip {entry['name']}, got {entry['status']}"
            )

        # Third call for good measure
        third = _apply_and_commit(conn)
        assert all(t["status"] == "skipped" for t in third)

        # schema_migrations has exactly 6 rows — no duplicates
        count = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        assert count == 6, f"expected 6 rows, got {count}"

        # Verify status is stable
        status = get_migration_status(conn)
        assert len(status["applied"]) == 6
        assert status["pending"] == []

        # Simulate a hub restart: close and reopen the DB
        conn.close()
        conn2 = _open_db(db)
        try:
            fourth = _apply_and_commit(conn2)
            assert all(t["status"] == "skipped" for t in fourth)
            status = get_migration_status(conn2)
            assert len(status["applied"]) == 6
        finally:
            conn2.close()
    finally:
        # Re-open if previously closed, then close.
        try:
            conn.close()
        except sqlite3.ProgrammingError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: numeric ordering — migrations applied in ascending version
# ─────────────────────────────────────────────────────────────────────────────
def test_migrations_applied_in_numeric_order(tmp_path: Path):
    db = tmp_path / "ordering.db"
    conn = _open_db(db)
    try:
        # list_migration_files should return them already sorted by version
        files = list_migration_files(DEFAULT_MIGRATIONS_DIR)
        versions = [v for v, _n, _p in files]
        assert versions == sorted(versions), (
            f"migration files out of order: {versions}"
        )
        assert versions == [1, 2, 3, 4, 5, 6], f"unexpected versions: {versions}"

        # apply_pending_migrations records them in numeric order
        touched = _apply_and_commit(conn)
        touched_versions = [t["version"] for t in touched]
        assert touched_versions == [1, 2, 3, 4, 5, 6], (
            f"runner returned out-of-order versions: {touched_versions}"
        )

        # The schema_migrations table is also ordered by version
        rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        stored = [int(r["version"]) for r in rows]
        assert stored == [1, 2, 3, 4, 5, 6]

        # Each migration name maps to the expected version
        expected_names = {
            1: "001_initial_schema.sql",
            2: "002_add_agents_circuit_columns.sql",
            3: "003_add_showbox_buttons.sql",
            4: "004_add_workflow_retry_columns.sql",
            5: "005_add_soul_tasks_nudge.sql",
            6: "006_add_generalag_tables.sql",
        }
        for entry in touched:
            assert entry["name"] == expected_names[entry["version"]], (
                f"version {entry['version']} -> {entry['name']} "
                f"(expected {expected_names[entry['version']]})"
            )
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Bonus: status helpers + init_database() integration
# ─────────────────────────────────────────────────────────────────────────────
def test_get_migration_status_empty_db(tmp_path: Path):
    """On a fresh DB the status helper reports every bundled migration as pending."""
    db = tmp_path / "empty.db"
    conn = _open_db(db)
    try:
        status = get_migration_status(conn)
        assert status["applied"] == []
        # All bundled migrations appear as pending
        assert len(status["pending"]) == 6
        pending_versions = [p["version"] for p in status["pending"]]
        assert pending_versions == [1, 2, 3, 4, 5, 6]
    finally:
        conn.close()


def test_init_database_creates_schema_migrations(tmp_path: Path, monkeypatch):
    """High-level smoke test: full init_database() registers migrations."""
    db_file = tmp_path / "hub.db"
    # Patch Config.DB_PATH so init_database() uses this tmp db
    from gnom_hub.core import config as cfg_module
    from gnom_hub.db import connection as conn_module

    monkeypatch.setattr(cfg_module, "DB_PATH", db_file)
    monkeypatch.setattr(cfg_module.Config, "DB_PATH", db_file)
    monkeypatch.setattr(conn_module.Config, "DB_PATH", db_file)

    from gnom_hub.db.schema import init_database

    init_database()

    conn = _open_db(db_file)
    try:
        status = get_migration_status(conn)
        assert len(status["applied"]) >= 6, (
            f"expected ≥6 applied, got {len(status['applied'])}: {status}"
        )
        assert status["pending"] == []

        # schema_migrations table itself exists
        assert "schema_migrations" in _existing_tables(conn)

        # Sanity: at least one of the state-seeded rows is present
        state_keys = {
            r["key"]
            for r in conn.execute("SELECT key FROM state").fetchall()
        }
        assert "active_project" in state_keys
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Regression guard: bootstrap mode must add missing columns via ALTER TABLE
# ─────────────────────────────────────────────────────────────────────────────
def test_bootstrap_adds_missing_columns(tmp_path: Path):
    """Legacy DBs that are missing columns added in recent migrations must
    actually get those columns when the migration system is first installed.

    Original bug: ``apply_pending_migrations`` entered bootstrap mode for any
    DB that had legacy marker tables but no ``schema_migrations`` row. In
    that mode it recorded every migration as "applied" WITHOUT running the
    SQL — so a legacy DB without ``agents.circuit_state`` (added in
    migration 002) would silently stay without that column forever, even
    though ``schema_migrations`` claimed 002 was applied. Heartbeat code
    that writes ``circuit_state`` would crash on every restart.

    Fix: bootstrap mode re-executes the SQL with tolerance for benign
    ``duplicate column`` errors. This test exercises both halves of that
    contract — a column that already exists (tolerated) and a column that
    doesn't exist yet (added).
    """
    db = tmp_path / "legacy_partial.db"
    conn = _open_db(db)
    try:
        # Build a legacy DB with the `agents` table missing the columns
        # added in migration 002. Existing rows must survive.
        conn.execute("""
            CREATE TABLE agents (
                name TEXT PRIMARY KEY,
                id TEXT NOT NULL UNIQUE,
                port INTEGER DEFAULT 0,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'offline',
                capabilities TEXT DEFAULT '[]',
                role TEXT DEFAULT 'normal',
                active_job TEXT DEFAULT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO agents (name, id, status, last_seen) "
            "VALUES ('LegacyAG', 'abc-123', 'online', '2026-01-01T00:00:00Z')"
        )
        conn.commit()

        # Pre-condition: columns missing, table exists, no schema_migrations
        cols_before = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(agents)").fetchall()
        }
        assert "circuit_state" not in cols_before
        assert "consecutive_failures" not in cols_before
        assert "schema_migrations" not in _existing_tables(conn)

        # Run the migration system for the first time on this DB
        touched = _apply_and_commit(conn)

        # Status: every migration went through the bootstrap path
        for entry in touched:
            assert entry["status"] == "bootstrap", (
                f"expected all-bootstrap, got {entry}"
            )

        # The previously-missing columns are now present
        cols_after = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(agents)").fetchall()
        }
        assert "circuit_state" in cols_after, (
            f"bootstrap should have added circuit_state, got {cols_after}"
        )
        assert "consecutive_failures" in cols_after, (
            f"bootstrap should have added consecutive_failures, got {cols_after}"
        )

        # Original data is still there
        legacy_row = conn.execute(
            "SELECT name, status FROM agents WHERE name='LegacyAG'"
        ).fetchone()
        assert legacy_row is not None
        assert legacy_row["status"] == "online"

        # Idempotent: re-run is a no-op (all skipped, not bootstrap again)
        second = _apply_and_commit(conn)
        assert all(t["status"] == "skipped" for t in second)
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Regression guard: bootstrap must tolerate "duplicate column" without dying
# ─────────────────────────────────────────────────────────────────────────────
def test_bootstrap_tolerates_duplicate_column(tmp_path: Path):
    """A legacy DB that ALREADY has ``agents.circuit_state`` must not crash
    when the migration system re-applies migration 002 in bootstrap mode.

    Without the benign-error swallow, ``ALTER TABLE agents ADD COLUMN
    circuit_state`` raises ``OperationalError: duplicate column name:
    circuit_state`` and the whole migration aborts. With the fix, the
    error is logged at INFO and the runner continues to the next
    migration.
    """
    db = tmp_path / "legacy_full.db"
    conn = _open_db(db)
    try:
        # Legacy DB with full schema (everything except schema_migrations)
        conn.execute("""
            CREATE TABLE agents (
                name TEXT PRIMARY KEY,
                id TEXT NOT NULL UNIQUE,
                port INTEGER DEFAULT 0,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'offline',
                capabilities TEXT DEFAULT '[]',
                role TEXT DEFAULT 'normal',
                active_job TEXT DEFAULT NULL,
                last_seen TEXT NOT NULL,
                circuit_state TEXT DEFAULT 'CLOSED',
                consecutive_failures INTEGER DEFAULT 0
            )
        """)
        conn.commit()

        # First apply: every migration goes through bootstrap, ALTERs raise
        # but are tolerated.
        touched = _apply_and_commit(conn)
        assert len(touched) == 6
        for entry in touched:
            assert entry["status"] == "bootstrap", entry

        # DB is fully consistent
        cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(agents)").fetchall()
        }
        assert {"circuit_state", "consecutive_failures"} <= cols

        # schema_migrations has exactly 6 rows
        count = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
        assert count == 6
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Regression guard: row_factory must be set defensively by the runner itself
# ─────────────────────────────────────────────────────────────────────────────
def test_runner_sets_row_factory_defensively(tmp_path: Path):
    """Regression test for the live-DB row_factory crash (attempt 3 reject).

    Both ``apply_pending_migrations()`` and ``get_migration_status()`` MUST set
    ``conn.row_factory = sqlite3.Row`` themselves at the top of the function —
    not rely on the caller to do it. This test opens a connection with
    ``row_factory = None`` (the raw default sqlite3 gives you) and exercises
    both functions. If anyone removes the defensive ``conn.row_factory`` line
    from either function, this test fails immediately.

    The original bug: line 155 in migrations.py used ``r["version"]`` (dict
    access), but on a connection without ``row_factory`` set, ``fetchall()``
    returns plain tuples, and dict access raises
    ``TypeError: tuple indices must be integers or slices, not str``.
    """
    db = tmp_path / "no_row_factory.db"
    # Open connection WITHOUT setting row_factory — simulate any caller
    # that forgot to configure the connection (CLI script, third-party tool,
    # or simply a fresh sqlite3.connect() call).
    conn = sqlite3.connect(str(db), timeout=15.0)
    try:
        # Sanity: row_factory really is unset at the start of this test
        assert conn.row_factory is None, (
            "test setup wrong: expected default (None) row_factory before "
            "calling apply_pending_migrations / get_migration_status"
        )

        # 1) apply_pending_migrations must work without the caller setting it
        touched = apply_pending_migrations(conn)
        conn.commit()
        statuses = [t["status"] for t in touched]
        assert statuses.count("applied") == 6, (
            f"expected 6 applied, got {statuses}"
        )

        # After the call, the runner should have switched row_factory to Row
        assert conn.row_factory is sqlite3.Row, (
            "apply_pending_migrations must defensively set row_factory"
        )

        # 2) get_migration_status must also work on a fresh no-row_factory
        #    connection. To prove it, re-open the DB without row_factory.
        conn.close()
        conn = sqlite3.connect(str(db), timeout=15.0)
        assert conn.row_factory is None, (
            "freshly-opened connection should still have default row_factory"
        )

        status = get_migration_status(conn)
        assert len(status["applied"]) == 6
        assert status["pending"] == []
        assert conn.row_factory is sqlite3.Row, (
            "get_migration_status must defensively set row_factory"
        )

        # 3) Dict-style access on returned rows works (proof that row_factory
        #    really is sqlite3.Row, not just a coincidental success).
        if status["applied"]:
            first = status["applied"][0]
            assert "version" in first and "name" in first and "applied_at" in first
    finally:
        try:
            conn.close()
        except sqlite3.ProgrammingError:
            pass