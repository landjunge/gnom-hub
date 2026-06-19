#!/usr/bin/env python3
"""Verify all Gnom-Hub databases are not corrupt."""
import sqlite3
import sys
from pathlib import Path

GNOM_DATA = Path.home() / ".gnom-hub" / "data"

def verify_db(path: Path) -> tuple:
    try:
        conn = sqlite3.connect(str(path))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return (result[0] == "ok", result[0])
    except Exception as e:
        return (False, str(e))

def main():
    if not GNOM_DATA.exists():
        print(f"❌ Verzeichnis nicht gefunden: {GNOM_DATA}")
        sys.exit(1)
    db_files = sorted(GNOM_DATA.glob("*.db"))
    if not db_files:
        print(f"❌ Keine DB-Dateien in {GNOM_DATA}")
        sys.exit(1)
    all_ok = True
    for db in db_files:
        ok, msg = verify_db(db)
        size_kb = db.stat().st_size / 1024
        status = "✓" if ok else "✗"
        print(f"{status} {db.name:30s} {size_kb:>10.1f} KB  {msg}")
        if not ok:
            all_ok = False
    sys.exit(0 if all_ok else 2)

if __name__ == "__main__":
    main()