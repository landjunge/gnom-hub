#!/usr/bin/env python3
"""Aktiviert WAL-Mode für alle Gnom-Hub DBs und führt VACUUM aus.
WAL = Write-Ahead-Logging: gleichzeitige Lese/Schreibzugriffe ohne Locking."""
import sqlite3
from pathlib import Path

GNOM_DATA = Path.home() / ".gnom-hub" / "data"

def optimize_db(path: Path) -> None:
    try:
        conn = sqlite3.connect(str(path))
        # WAL-Mode aktivieren (Write-Ahead-Logging)
        conn.execute("PRAGMA journal_mode=WAL")
        # Synchronous=NORMAL für Performance (sicher mit WAL)
        conn.execute("PRAGMA synchronous=NORMAL")
        # VACUUM (komprimiert, gibt ungenutzten Speicher frei)
        conn.execute("VACUUM")
        # ANALYZE (aktualisiert Query-Planer-Statistiken)
        conn.execute("ANALYZE")
        size_kb = path.stat().st_size / 1024
        print(f"✓ {path.name:30s} {size_kb:>10.1f} KB  WAL=on")
        conn.close()
    except Exception as e:
        print(f"✗ {path.name}: {e}")

def main():
    db_files = sorted(GNOM_DATA.glob("*.db"))
    if not db_files:
        print(f"Keine DBs in {GNOM_DATA}")
        return
    print(f"=== Optimiere {len(db_files)} DBs in {GNOM_DATA} ===")
    for db in db_files:
        optimize_db(db)
    print("\n✓ Alle DBs optimiert (WAL + VACUUM + ANALYZE)")

if __name__ == "__main__":
    main()