#!/usr/bin/env python3
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

db_path = os.path.expanduser('~/.gnom-hub/data/gnomhub.db')

msg_id = str(uuid.uuid4())
content = (
    "Ich bemerke, dass lokale Commits vorhanden sind, die noch nicht auf GitHub hochgeladen wurden. "
    "Möchten Sie, dass ich ein `git push` durchführe? "
    "Sie können den Befehl über `@@git push` direkt im Chat ausführen, oder mir antworten, damit ich es für Sie erledige."
)

with sqlite3.connect(db_path) as conn:
    # Dynamically resolve agent ID instead of using hardcoded UUID
    row = conn.execute("SELECT id FROM agents WHERE LOWER(name) = 'generalag'").fetchone()
    agent_id = row[0] if row else str(uuid.uuid4())

    conn.execute(
        "INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (msg_id, "default", "GeneralAG", agent_id, "chat", content,
         datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
         json.dumps({"model": "deepseek/deepseek-chat", "token_count": 50}))
    )

print("Git push offer message inserted successfully!")
