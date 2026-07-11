#!/usr/bin/env python3
import json
import os
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone

db_path = os.path.expanduser('~/.gnom-hub/data/gnomhub.db')

# Messages to insert into the Gnom-Hub chat database
messages = [
    {
        "sender": "WriterAG",
        "content": "Ich präsentiere die neue Netzwerkpunkt-Präsentationsseite, die jetzt auf netzwerkpunkt.de online ist."
    },
    {
        "sender": "WriterAG",
        "content": "Die Seite zeigt den @bake Compiler, das 3-Agenten-Sicherheits-Tribunal und steganographische Code-Signaturen."
    },
    {
        "sender": "WriterAG",
        "content": "Zusätzlich sehen Sie das interaktive Live-Tribunal der 8 Agenten sowie das Bento-Grid-Metriken-Dashboard."
    }
]

print("Inserting messages into Gnom-Hub database...")
with sqlite3.connect(db_path) as conn:
    # Dynamically resolve agent ID instead of using hardcoded UUID
    row = conn.execute("SELECT id FROM agents WHERE LOWER(name) = 'writerag'").fetchone()
    agent_id = row[0] if row else str(uuid.uuid4())

    for msg in messages:
        msg_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        meta = json.dumps({"model": "deepseek/deepseek-chat", "token_count": 50})

        conn.execute(
            "INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, "default", msg["sender"], agent_id, "chat", msg["content"], timestamp, meta)
        )

print("Chat messages inserted successfully!")

# Walkthrough text for macOS system-level TTS
tts_text = (
    "Hallo! Ich bin Writer A G. Die Netzwerkpunkt-Showcase-Seite ist jetzt online auf netzwerkpunkt.de. "
    "Die Seite stellt Gnom-Hub vor. Gnom-Hub ist eine lokale Multi-Agenten-Schmiede für KI-Teams. "
    "Zu den wichtigsten Funktionen der Seite gehören: Erstens der @bake Compiler, mit dem lokale Agenten zu stabilen Produkten kompiliert werden. "
    "Zweitens das Drei-Agenten-Sicherheits-Tribunal, das riskante Schreib- und Shell-Aktionen validiert. "
    "Drittens die Steganographie mit unsichtbaren Zeichen als Herkunftsbeweis. "
    "Viertens das Fünf-Achsen-Agenten-Tuning zur präzisen Kalibrierung. "
    "Fünftens das automatische Git-basierte Tracking für System-Prompts. "
    "Schließlich zeigt die Seite auch ein interaktives Agenten-Tribunal in Echtzeit und ein übersichtliches Metriken-Dashboard. "
    "Schau dir die Seite gerne live im geöffneten Browser an!"
)

print("Speaking walkthrough text...")
subprocess.run(["say", "-v", "Anna", tts_text])
print("TTS speech completed.")
