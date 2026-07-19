"""Process-local write serialization for SQLite (Wave A).

Multiple hub threads (chat, register, heartbeat, recovery) used to open
concurrent writers and amplify ``database is locked``. A single RLock per
process serializes commits without changing the API of get_db_conn.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager

from gnom_hub.db.connection import get_db_connection

_write_lock = threading.RLock()


@contextmanager
def serialized_db_write():
    """Exclusive write section — one writer at a time in this process."""
    with _write_lock:
        conn = get_db_connection()
        try:
            yield conn
            try:
                conn.commit()
            except Exception:
                pass
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass
