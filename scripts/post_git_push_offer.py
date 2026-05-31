#!/usr/bin/env python3
import sqlite3
import uuid
import os
import datetime
import json

db_path = os.path.expanduser('~/.gnom-hub/data/gnomhub.db')
conn = sqlite3.connect(db_path)

msg_id = str(uuid.uuid4())
content = (
    "Ich bemerke, dass lokale Commits vorhanden sind, die noch nicht auf GitHub hochgeladen wurden. "
    "Möchten Sie, dass ich ein `git push` durchführe? "
    "Sie können den Befehl über `@@git push` direkt im Chat ausführen, oder mir antworten, damit ich es für Sie erledige."
)

# Insert the message under GeneralAG's name
conn.execute(
    "INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    (msg_id, "default", "GeneralAG", "61a3eef8-4482-48f7-9b7f-51d2b238f8a0", "chat", content, datetime.datetime.utcnow().isoformat() + "Z", json.dumps({"model": "deepseek/deepseek-chat", "token_count": 50}))
)
conn.commit()
print("Git push offer message inserted successfully!")
