#!/usr/bin/env python3
"""Wipe chat, soul memory, queues, archives, context, coordination, kuzu.

Keeps schema + schema_migrations. Does NOT touch gnom-Workspace files.
Run from repo with venv active. Prefer stopping agents first (this script
sends SIGTERM to agents.run_agent only).
"""
from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DATA = Path.home() / ".gnom-hub" / "data"
PROJECT_DATA = Path(__file__).resolve().parent.parent / "data"


def stop_agents() -> list[int]:
    killed: list[int] = []
    out = subprocess.check_output(["ps", "-ax", "-o", "pid=,command="], text=True)
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        pid, cmd = int(parts[0]), parts[1]
        if "agents.run_agent" not in cmd:
            continue
        if pid == os.getpid():
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append(pid)
        except ProcessLookupError:
            pass
    time.sleep(2)
    for pid in killed:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return killed


def wipe_sqlite(path: Path) -> None:
    if not path.exists():
        print(f"  skip missing {path}")
        return
    print(f"\n=== {path} ({path.stat().st_size} bytes) ===")
    conn = sqlite3.connect(str(path), timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    for t in tables:
        if t == "schema_migrations":
            print(f"  keep {t}")
            continue
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            conn.execute(f'DELETE FROM "{t}"')
            print(f"  DELETE {t}: {n}")
        except Exception as e:
            print(f"  FAIL {t}: {e}")
    conn.commit()
    try:
        conn.execute("VACUUM")
        print("  VACUUM ok")
    except Exception as e:
        print(f"  VACUUM skip: {e}")
    conn.close()


def main() -> int:
    print("DATA", DATA)
    print("stop agents:", stop_agents())
    time.sleep(1)

    for name in (
        "gnomhub.db",
        "gnom_hub.db",
        "passive_archive.db",
        "soul_passive.db",
        "context.db",
        "coordination.db",
        "rules.db",
    ):
        wipe_sqlite(DATA / name)

    for name in ("memory.kuzu", "memory.kuzu.wal"):
        p = DATA / name
        if p.exists():
            p.unlink()
            print("removed", p)

    emb = DATA / "emb_cache.json"
    if emb.exists():
        print("clear emb_cache", emb.stat().st_size)
        emb.write_text("{}\n")

    if PROJECT_DATA.is_dir():
        for p in PROJECT_DATA.glob("soul_fact_ids*.json"):
            p.write_text("{}\n")
            print("reset", p)
        for p in PROJECT_DATA.glob("*.index"):
            p.unlink()
            print("removed", p)
        for name in ("memory.kuzu", "memory.kuzu.wal"):
            p = PROJECT_DATA / name
            if p.exists():
                p.unlink()
                print("removed", p)

    print("\n✅ Memory wipe complete. Restart hub/agents if needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
