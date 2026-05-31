#!/usr/bin/env python3
import sqlite3
import uuid
import os
import datetime
import json
import subprocess

db_path = os.path.expanduser('~/.gnom-hub/data/gnomhub.db')
conn = sqlite3.connect(db_path)

# Messages to insert into the Gnom-Hub chat database
messages = [
    {
        "sender": "WriterAG",
        "agent_id": "e3ad494b-720a-4aa7-a1e2-eff389cf0179",
        "content": "Ich präsentiere die neue Netzwerkpunkt-Präsentationsseite, die jetzt auf netzwerkpunkt.de online ist."
    },
    {
        "sender": "WriterAG",
        "agent_id": "e3ad494b-720a-4aa7-a1e2-eff389cf0179",
        "content": "Die Seite zeigt den @bake Compiler, das 3-Agenten-Sicherheits-Tribunal und steganographische Code-Signaturen."
    },
    {
        "sender": "WriterAG",
        "agent_id": "e3ad494b-720a-4aa7-a1e2-eff389cf0179",
        "content": "Zusätzlich sehen Sie das interaktive Live-Tribunal der 8 Agenten sowie das Bento-Grid-Metriken-Dashboard."
    }
]

print("Inserting messages into Gnom-Hub database...")
for msg in messages:
    msg_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    meta = json.dumps({"model": "deepseek/deepseek-chat", "token_count": 50})
    
    conn.execute(
        "INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (msg_id, "default", msg["sender"], msg["agent_id"], "chat", msg["content"], timestamp, meta)
    )
conn.commit()
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
# Use macOS native 'say' command with German voice Anna
subprocess.run(["say", "-v", "Anna", tts_text])
print("TTS speech completed.")
