import sqlite3
import os

db_path = os.path.expanduser('~/.gnom-hub/data/passive_archive.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT timestamp, sender, substr(content, 1, 150) as snippet, length(content) as length FROM archive_log WHERE category = 'chat' AND timestamp >= '2026-06-01T00:00:00Z' ORDER BY timestamp ASC"
).fetchall()

print(f"Found {len(rows)} chat messages on June 1st:")
for r in rows:
    print(f"[{r['timestamp']}] {r['sender']} (len={r['length']}): {repr(r['snippet'])}")

conn.close()
