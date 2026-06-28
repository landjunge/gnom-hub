#!/usr/bin/env python3
"""Import memory_facts_*.json → soul_memory.db (SoulAG exclusive writer)."""
import sqlite3
import json
import sys
from pathlib import Path

FACTS_FILE = "/Users/landjunge/gnom-Workspace/default/memory_facts_landing_2026-07-28.json"
DB_PATH = "/Users/landjunge/gnom-hub/soul/soul_memory.db"


def import_facts(facts_path: str = FACTS_FILE, db_path: str = DB_PATH):
    facts_path = Path(facts_path)
    db_path = Path(db_path)
    if not facts_path.exists():
        print(f"ERROR: facts file missing: {facts_path}")
        sys.exit(1)

    with open(facts_path) as f:
        data = json.load(f)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS memory_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            priority TEXT,
            target_agent TEXT,
            source TEXT,
            extracted_at TEXT,
            schema_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    inserted = 0
    skipped = 0
    errors = []
    for fact in data.get("facts", []):
        try:
            c.execute("""
                INSERT OR REPLACE INTO memory_facts
                  (key, value, priority, target_agent, source, extracted_at, schema_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                fact["key"],
                fact["value"],
                fact.get("priority"),
                fact.get("target_agent"),
                data.get("source"),
                data.get("extracted_at"),
                data.get("schema_version"),
            ))
            inserted += 1
        except Exception as e:
            errors.append((fact.get("key", "?"), str(e)))
            skipped += 1

    conn.commit()

    # Verify
    c.execute("SELECT COUNT(*) FROM memory_facts")
    total_in_db = c.fetchone()[0]

    # Index by target_agent for fast retrieval
    c.execute("CREATE INDEX IF NOT EXISTS idx_target_agent ON memory_facts(target_agent)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_priority ON memory_facts(priority)")
    conn.commit()
    conn.close()

    return {
        "inserted_or_replaced": inserted,
        "skipped": skipped,
        "errors": errors,
        "total_in_db": total_in_db,
        "source_file": str(facts_path),
        "db_path": str(db_path),
    }


if __name__ == "__main__":
    result = import_facts()
    print(json.dumps(result, indent=2, ensure_ascii=False))