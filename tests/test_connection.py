"""Tests for the unified connection layer."""
import sqlite3
from gnom_hub.db.connection import get_db_conn, get_db_connection


def test_get_db_conn_returns_connection(isolated_db):
    """Connection context manager should yield a valid connection."""
    with get_db_conn() as conn:
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)


def test_connection_has_wal_mode(isolated_db):
    """Connection should use WAL journal mode."""
    with get_db_conn() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


def test_connection_has_foreign_keys(isolated_db):
    """Connection should have foreign keys enabled."""
    with get_db_conn() as conn:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1


def test_connection_has_row_factory(isolated_db):
    """Connection should use sqlite3.Row as row factory."""
    with get_db_conn() as conn:
        assert conn.row_factory == sqlite3.Row


def test_connection_closes_after_context(isolated_db):
    """Connection should be closed after exiting the context manager."""
    with get_db_conn() as conn:
        conn.execute("SELECT 1")
    # After context exit, connection should be closed
    # Attempting to use it should raise
    try:
        conn.execute("SELECT 1")
        closed = False
    except Exception:
        closed = True
    assert closed
