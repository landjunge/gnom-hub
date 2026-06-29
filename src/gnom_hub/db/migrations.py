"""Lightweight migration runner for Gnom-Hub.

Design goals (kept simple on purpose — no alembic, no DSL):
  * Each migration is a plain ``NNN_<name>.sql`` file under
    ``gnom_hub/db/migrations/``.
  * Applied versions are tracked in ``schema_migrations`` (version INTEGER PRIMARY KEY).
  * Migrations are sorted by version prefix and executed in numeric order.
  * Each migration file must be idempotent (CREATE TABLE IF NOT EXISTS, etc.).
  * On a pre-existing DB (legacy schema, no ``schema_migrations`` table) we
    enter **bootstrap mode** — every migration is recorded as already applied
    AND its SQL is re-executed with tolerance for benign errors (e.g.
    ``duplicate column name`` from ``ALTER TABLE ADD COLUMN`` on a column
    that already exists). This is safe because every migration uses
    ``IF NOT EXISTS`` for ``CREATE TABLE`` / ``CREATE INDEX``, and the only
    other statement type is ``ALTER TABLE ADD COLUMN`` whose benign failure
    mode is well-known and recoverable. Without the re-execute, legacy DBs
    would silently miss new columns added by recent migrations.

Public API:
    * ``apply_pending_migrations(conn, migrations_dir=None) -> list[dict]``
    * ``get_migration_status(conn) -> dict``  (keys: applied, pending)

The runner is intentionally synchronous and uses sqlite3 only — the same DB
engine every other gnom_hub repo uses. No async, no external deps.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_log = logging.getLogger("db.migrations")

# Default location of the SQL migration files.
DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Filename pattern: 3+ digit version prefix followed by "_" then descriptive name.
_MIGRATION_PATTERN = re.compile(r"^(\d{3,})_.+\.sql$")

# Tables that count as "the DB already existed" markers for bootstrap detection.
# If any of these exist on a DB that has no schema_migrations table yet,
# we assume this is a legacy DB and skip re-executing the SQL.
_LEGACY_MARKER_TABLES = (
    "agents",
    "chat",
    "soul_memory",
    "general_memory",
    "state",
    "audit_log",
    "showbox_presentations",
)


def _default_migrations_dir() -> Path:
    """Resolve the canonical migrations directory (lives next to this file)."""
    return DEFAULT_MIGRATIONS_DIR


def _list_migration_files(migrations_dir: Path) -> list[tuple[int, str, Path]]:
    """Return ``(version, name, path)`` triples, sorted by version ascending."""
    if not migrations_dir.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")
    out: list[tuple[int, str, Path]] = []
    for entry in sorted(migrations_dir.iterdir()):
        if not entry.is_file():
            continue
        m = _MIGRATION_PATTERN.match(entry.name)
        if not m:
            continue
        version = int(m.group(1))
        out.append((version, entry.name, entry))
    out.sort(key=lambda t: t[0])
    return out


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """Create the tracking table if it does not exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            applied_by TEXT DEFAULT 'system'
        )
        """
    )


def _has_legacy_tables(conn: sqlite3.Connection) -> bool:
    """Heuristic: any of the legacy marker tables present?"""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    existing = {r[0] for r in rows}
    return any(t in existing for t in _LEGACY_MARKER_TABLES)


def _record_applied(
    conn: sqlite3.Connection,
    version: int,
    name: str,
    applied_by: str,
    applied_at: str,
) -> None:
    """Insert a row into ``schema_migrations`` (idempotent via INSERT OR IGNORE)."""
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations
            (version, name, applied_at, applied_by)
        VALUES (?, ?, ?, ?)
        """,
        (version, name, applied_at, applied_by),
    )


def apply_pending_migrations(
    conn: sqlite3.Connection,
    migrations_dir: Path | None = None,
    applied_by: str = "system",
) -> list[dict[str, Any]]:
    """Apply every migration that has not yet been recorded as applied.

    Args:
        conn: open sqlite3 connection (caller owns the transaction/lifetime).
        migrations_dir: directory holding ``NNN_*.sql`` files. Defaults to the
            package-bundled migrations directory.
        applied_by: stored in ``schema_migrations.applied_by``.

    Returns:
        List of records ``{"version": int, "name": str, "status": str}``
        for every migration we touched this call. ``status`` is one of:
        ``"applied"`` (newly executed against a fresh DB), ``"bootstrap"``
        (legacy DB detected; SQL re-executed with tolerance for benign
        errors like ``duplicate column``), ``"skipped"`` (already applied
        on a previous run).
    """
    # Defensive: ensure rows come back as ``sqlite3.Row`` regardless of caller.
    # Without this, the dict-style ``r["version"]`` access below raises
    # ``TypeError: tuple indices must be integers or slices, not str`` on any
    # connection that hasn't pre-configured ``row_factory``. (gnom_hub's own
    # ``get_db_connection()`` does set it, but this function MUST also work
    # when called from a fresh ``sqlite3.connect(...)`` — e.g. a one-shot CLI
    # script or a different repo context.)
    conn.row_factory = sqlite3.Row

    mdir = Path(migrations_dir) if migrations_dir is not None else _default_migrations_dir()
    files = _list_migration_files(mdir)
    if not files:
        _log.warning("[migrations] No migration files found in %s", mdir)
        return []

    _ensure_migrations_table(conn)

    # Bootstrap detection: schema_migrations table is empty AND legacy marker
    # tables already exist. In that case we treat the DB as pre-existing and
    # record every migration as already applied WITHOUT re-executing its SQL.
    legacy_present = _has_legacy_tables(conn)
    schema_mig_has_rows = conn.execute(
        "SELECT 1 FROM schema_migrations LIMIT 1"
    ).fetchone() is not None
    bootstrap = legacy_present and not schema_mig_has_rows

    applied_rows = conn.execute(
        "SELECT version FROM schema_migrations"
    ).fetchall()
    applied_versions = {int(r["version"]) for r in applied_rows}

    now_iso = datetime.now(timezone.utc).isoformat()
    touched: list[dict[str, Any]] = []

    if bootstrap:
        _log.info(
            "[migrations] Bootstrap: existing DB detected, "
            "re-applying all migrations with tolerance for benign errors"
        )

    for version, name, path in files:
        if version in applied_versions:
            touched.append({"version": version, "name": name, "status": "skipped"})
            continue

        if bootstrap:
            # Re-execute the SQL with tolerance: legacy DBs may have some
            # tables/columns already and others missing. CREATE TABLE /
            # CREATE INDEX use IF NOT EXISTS so they're no-ops on existing
            # objects. ALTER TABLE ADD COLUMN may fail with
            # "duplicate column name" on a column that already exists —
            # we swallow that specific error since the desired end state
            # is "column present" which is already true. Any other error
            # is a real schema-drift problem and we re-raise.
            sql_text = path.read_text(encoding="utf-8")
            try:
                conn.executescript(sql_text)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column" not in msg:
                    _log.error(
                        "[migrations] Bootstrap re-apply of %s (v%d) "
                        "failed with non-benign error: %s",
                        name, version, e,
                    )
                    raise
                _log.info(
                    "[migrations] Bootstrap re-apply of %s (v%d) "
                    "tolerated benign 'duplicate column' error: %s",
                    name, version, e,
                )
            _record_applied(conn, version, name, applied_by, now_iso)
            touched.append({"version": version, "name": name, "status": "bootstrap"})
            continue

        sql_text = path.read_text(encoding="utf-8")
        try:
            # executescript runs each statement; wrapped in the caller's
            # transaction so a failure rolls everything back.
            conn.executescript(sql_text)
        except sqlite3.Error as e:
            _log.error(
                "[migrations] Failed to apply %s (v%d): %s", name, version, e
            )
            raise

        _record_applied(conn, version, name, applied_by, now_iso)
        touched.append({"version": version, "name": name, "status": "applied"})
        _log.info("[migrations] Applied %s (v%d)", name, version)

    return touched


def get_migration_status(conn: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    """Return ``{"applied": [...], "pending": [...]}`` for the given connection.

    Each entry is ``{"version": int, "name": str, "applied_at": str}``
    (pending entries omit ``applied_at``).
    """
    # See the matching block in ``apply_pending_migrations`` — same defensive
    # rationale: callers may pass a connection that hasn't set ``row_factory``.
    conn.row_factory = sqlite3.Row

    _ensure_migrations_table(conn)

    files = _list_migration_files(_default_migrations_dir())

    applied_rows = conn.execute(
        "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied = [
        {
            "version": int(r["version"]),
            "name": r["name"],
            "applied_at": r["applied_at"],
        }
        for r in applied_rows
    ]
    applied_versions = {int(r["version"]) for r in applied_rows}

    pending: list[dict[str, Any]] = []
    for version, name, _path in files:
        if version in applied_versions:
            continue
        pending.append({"version": version, "name": name})

    return {"applied": applied, "pending": pending}


def list_migration_files(migrations_dir: Path | None = None) -> list[tuple[int, str, Path]]:
    """Public helper: enumerate migration files. Exposed for tests and tooling."""
    return _list_migration_files(Path(migrations_dir) if migrations_dir else _default_migrations_dir())