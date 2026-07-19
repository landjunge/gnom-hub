"""Cross-process SQLite write coordination via flock.

Process-local RLocks are not enough: hub + 8 agents are separate PIDs.
A short exclusive flock around BEGIN IMMEDIATE / multi-statement writes
reduces ``database is locked`` storms (Supervisor-Test 2026-07).
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

_LOCK_PATH: Path | None = None


def _lock_path() -> Path:
    global _LOCK_PATH
    if _LOCK_PATH is None:
        try:
            from gnom_hub.core.config import RUN_DIR
            base = Path(RUN_DIR)
        except Exception:
            base = Path.home() / ".gnom-hub" / "run"
        base.mkdir(parents=True, exist_ok=True)
        _LOCK_PATH = base / "sqlite_write.lock"
    return _LOCK_PATH


@contextmanager
def cross_process_write_lock(timeout_s: float = 8.0):
    """Exclusive flock; falls back to no-op on platforms without fcntl."""
    path = _lock_path()
    try:
        import fcntl
    except ImportError:
        yield
        return

    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.time() + max(0.2, timeout_s)
    locked = False
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except BlockingIOError:
                if time.time() >= deadline:
                    # Last chance: blocking lock with remaining grace
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX)
                        locked = True
                    except OSError:
                        pass
                    break
                time.sleep(0.05)
        yield
    finally:
        if locked:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        try:
            os.close(fd)
        except OSError:
            pass
