import sqlite3
from contextlib import contextmanager
from datetime import datetime

from gnom_hub.core.config import Config


class Await:
    def __init__(self, v): self._v = v
    def __await__(self):
        async def _f(): return self._v
        return _f().__await__()
    def __getattr__(self, k): return getattr(self._v, k)
    def __getitem__(self, i): return self._v[i]
    def __iter__(self): return iter(self._v)
    def __len__(self): return len(self._v)
    def __bool__(self): return bool(self._v)

def parse_dt(s) -> datetime | None:
    if not s: return None
    s = str(s)
    if s.endswith("Z"): s = s[:-1] if ("+" in s[:-1] or "-" in s[:-1]) else s[:-1] + "+00:00"
    try: return datetime.fromisoformat(s)
    except Exception: return None

def get_db_connection() -> sqlite3.Connection:
    """Create a raw SQLite connection with all necessary PRAGMAs.

    This is the single source of truth for DB connections in the entire project.
    Prefer :func:`get_db_conn` so connections are always closed (leak guard).

    busy_timeout is intentionally short (5s). A 60s wait starved the hub
    thread pool under multi-agent register storms and made chat POSTs hang
    until the browser timed out with "Hub unreachable".
    """
    import os
    db_path = str(Config.DB_PATH)
    # check_same_thread=False: agents/hub share threads; timeout+busy_timeout
    # absorb multi-writer contention (BEGIN IMMEDIATE / WAL).
    # Default 1.5s: fail fast under contention so chat/register don't pin threads.
    busy_ms = int(os.environ.get("GNOM_DB_BUSY_MS", "1500"))
    timeout_s = max(busy_ms / 1000.0, 0.5)
    conn = sqlite3.connect(db_path, timeout=timeout_s, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-20000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={busy_ms}")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db_conn():
    """Context manager that yields a DB connection and ensures it is closed."""
    conn = get_db_connection()
    try:
        yield conn
        try:
            conn.commit()
        except sqlite3.Error:
            pass
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass

