# 🧠 GNOM-HUB

Modularer Agent-Orchestrator mit REST API, MCP-Server und War Room Chat.
Agenten registrieren sich selbst, kommunizieren via Nudge-Signale und teilen sich ein gemeinsames Memory-System — alles unter einer strikten 40-Zeilen-pro-Datei Architektur.

## 🚀 Installation & Start

```bash
pip install -e .
gnom-hub
```

```
  ██████╗  ███╗   ██╗ ██████╗ ███╗   ███╗
 ██╔════╝  ████╗  ██║██╔═══██╗████╗ ████║
 ██║  ███╗ ██╔██╗ ██║██║   ██║██╔████╔██║
 ██║   ██║ ██║╚██╗██║██║   ██║██║╚██╔╝██║
 ╚██████╔╝ ██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
  ╚═════╝  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
                    H U B
   API:       http://127.0.0.1:3002
   MCP SSE:   http://127.0.0.1:3100/sse
   Frontend:  frontend/index.html
```

## 📡 Architektur

```
┌──────────────┐    ┌──────────────────────────┐    ┌────────────┐
│   Frontend   │───▶│   FastAPI Backend :3002   │◀───│  MCP :3100 │
│  War Room    │    │  7 Router · JSON DB       │    │  17 Tools  │
│  STT · TTS   │    │  Heartbeat Janitor        │    │  SSE       │
└──────────────┘    └────────────┬─────────────┘    └────────────┘
                                 │ nudge
                    ┌────────────▼─────────────┐
                    │     Agenten (beliebig)    │
                    │  register → heartbeat →   │
                    │  nudge empfangen → antworten│
                    └──────────────────────────┘
```

## 🔌 Agent-Integration (Copy & Paste)

So verbindest du einen beliebigen Agenten mit dem Gnom-Hub. 
Kopiere den folgenden Code und passe `AGENT_NAME` und `AGENT_PORT` an.

### Komplettes Python-Beispiel

```python
"""Minimaler Agent, der sich mit dem Gnom-Hub verbindet."""
import requests, threading, time
from flask import Flask, request  # oder FastAPI

# ═══════════════════════════════════════════
# KONFIGURATION — Nur diese zwei Werte ändern
# ═══════════════════════════════════════════
AGENT_NAME = "MeinAgent"
AGENT_PORT = 9200
HUB_URL    = "http://127.0.0.1:3002/api"
# ═══════════════════════════════════════════

app = Flask(__name__)
agent_id = None  # Wird bei Registrierung gesetzt


# ── SCHRITT 1: Registrierung ──────────────
def register():
    """Meldet den Agent beim Hub an. Wird einmal beim Start aufgerufen."""
    global agent_id
    r = requests.post(f"{HUB_URL}/agents/register", json={
        "name": AGENT_NAME,
        "port": AGENT_PORT,
        "description": f"{AGENT_NAME} auf Port {AGENT_PORT}"
    })
    data = r.json()
    agent_id = data["id"]
    print(f"✅ Registriert als {AGENT_NAME} (ID: {agent_id})")


# ── SCHRITT 2: Heartbeat (alle 60 Sekunden) ──
def heartbeat_loop():
    """Hält den Agent im Hub als 'online' markiert.
    Ohne Heartbeat setzt der Hub den Status nach 120s auf 'offline'."""
    while True:
        time.sleep(60)
        try:
            requests.post(f"{HUB_URL}/agents/{agent_id}/heartbeat")
        except:
            pass  # Hub kurz nicht erreichbar? Nächster Versuch in 60s.


# ── SCHRITT 3: Nudge empfangen ────────────
@app.post("/nudge")
def on_nudge():
    """Der Hub ruft diese Route auf, wenn es neue Daten gibt.
    Zum Beispiel: Jemand schreibt im War Room oder speichert ein Memory."""

    # Neue Memories abrufen
    memories = requests.get(f"{HUB_URL}/agents/{agent_id}/memory").json()
    print(f"📢 Nudge! {len(memories)} Memories vorhanden.")

    # Optional: Im War Room antworten
    requests.post(f"{HUB_URL}/chat", json={
        "content": f"Ich habe den Nudge erhalten! ({len(memories)} Memories)",
        "sender": AGENT_NAME
    })

    return {"status": "received"}


# ── START ──────────────────────────────────
if __name__ == "__main__":
    register()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=AGENT_PORT)
```

### Lifecycle auf einen Blick

```
Agent startet
    │
    ├─▶ POST /api/agents/register    →  Hub kennt den Agent
    │       {"name", "port"}              Antwort: {"id": "abc-123"}
    │
    ├─▶ Heartbeat-Thread startet     →  Alle 60s:
    │       POST /api/agents/{id}/heartbeat
    │       (sonst: nach 120s → Status "offline")
    │
    ├─▶ Flask/FastAPI lauscht        →  Wartet auf Nudges:
    │       POST http://127.0.0.1:{port}/nudge
    │       (Hub ruft das auf bei neuen Daten)
    │
    └─▶ Agent antwortet              →  POST /api/chat
            {"content": "...", "sender": "MeinAgent"}
```

### Nur mit curl testen

```bash
# 1. Registrieren
curl -X POST http://127.0.0.1:3002/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "TestAgent", "port": 9999}'
# → {"id": "abc-123-...", "status": "online", ...}

# 2. Heartbeat senden (mit der ID von oben)
curl -X POST http://127.0.0.1:3002/api/agents/abc-123/heartbeat

# 3. Nudge manuell auslösen
curl -X POST http://127.0.0.1:3002/api/agents/abc-123/nudge

# 4. Im War Room schreiben
curl -X POST http://127.0.0.1:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Hallo aus dem Terminal!", "sender": "TestAgent"}'
```

### MCP-Anbindung (für KI-Agenten)

Wenn dein Agent MCP unterstützt (z.B. Claude, Gemini), trage diese URL ein:

```json
{
  "mcpServers": {
    "gnom-hub": {
      "url": "http://127.0.0.1:3100/sse"
    }
  }
}
```

Der Agent bekommt dann Zugriff auf **17 Tools**: Memory lesen/schreiben, Agenten verwalten, Nudges senden, System-Stats abrufen — alles ohne eigene API-Calls.

## 📋 API Endpoints

### Agents
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `POST` | `/api/agents/register` | Self-Registration (Name + Port) |
| `POST` | `/api/agents/{id}/heartbeat` | Heartbeat → online |
| `GET` | `/api/agents` | Alle Agenten auflisten |
| `GET` | `/api/agents/{id}` | Agent-Details |
| `PUT` | `/api/agents/{id}/status` | Status setzen |
| `DELETE` | `/api/agents/{id}` | Agent + Memory löschen |
| `POST` | `/api/agents/{id}/nudge` | Signal an Agent |

### Memory
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `POST` | `/api/memory` | Speichern (+ Auto-Nudge) |
| `GET` | `/api/agents/{id}/memory` | Memory eines Agenten |
| `GET` | `/api/memory/search?q=` | Volltextsuche |
| `PUT` | `/api/memory/{id}` | Bearbeiten |
| `DELETE` | `/api/memory/{id}` | Löschen |

### Chat (War Room)
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `POST` | `/api/chat` | Nachricht senden (+ Broadcast) |
| `GET` | `/api/chat?limit=50` | Chat-History |

### Audio
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `POST` | `/api/audio/tts` | Text → Sprache |
| `POST` | `/api/audio/stt` | Audio → Text |

## 🛠 MCP Tools (17)

| Tool | Beschreibung |
|------|-------------|
| `save_to_memory` | Text in Agent-Memory speichern |
| `get_memory` | Memory eines Agenten lesen |
| `search_memory` | Memory durchsuchen |
| `delete_memory` | Eintrag löschen |
| `update_memory` | Eintrag ändern |
| `count_memory` | Einträge zählen |
| `clear_agent_memory` | Alle Memory eines Agenten löschen |
| `list_all_agents` | Alle Agenten auflisten |
| `get_agent` | Agent-Details abrufen |
| `create_agent` | Agent manuell anlegen |
| `delete_agent` | Agent + Memory löschen |
| `get_agent_status` | Status abfragen |
| `set_agent_status` | Status setzen |
| `search_agents` | Agenten suchen |
| `register_agent` | Self-Registration (Name + Port) |
| `nudge_agent` | Agent anstupsen |
| `get_system_stats` | System-Statistiken |

## 🎤 Audio-Engine

TTS und STT mit automatischem Fallback:

```
TTS:  ElevenLabs API → Browser Web Speech (kein Key nötig)
STT:  faster-whisper (lokal) → OpenAI Whisper API → Browser Speech Recognition
```

### Optionale Env-Variablen

```bash
export ELEVENLABS_API_KEY="sk-..."        # Cloud TTS
export ELEVENLABS_VOICE_ID="21m00T..."    # Stimmen-ID
export OPENAI_API_KEY="sk-..."            # Whisper STT Fallback
```

## 🗂 Projektstruktur

```
src/gnom_hub/
├── __init__.py          (1)   Package
├── __main__.py         (36)   Startup, Banner, Port-Discovery
├── hub_app.py          (23)   FastAPI App + 7 Router
├── hub_mcp.py          (39)   17 MCP Tools (SSE)
├── hub_pulse.py        (30)   Heartbeat Janitor (120s → offline)
├── config.py            (9)   Pfade (~/.gnom-hub/)
├── db.py               (14)   JSON Read/Write
├── models.py           (18)   Pydantic Models
├── routes_agents.py    (29)   Agent CRUD + Stats
├── routes_registry.py  (32)   Register + Heartbeat
├── routes_memory.py    (34)   Memory CRUD + Search
├── routes_chat.py      (27)   War Room Chat + @bs
├── routes_nudge.py     (16)   Agent Nudge Signal
├── routes_audio.py     (29)   TTS + STT Endpoints
├── audio_engine.py      (3)   Facade (re-export)
├── audio_tts.py        (22)   ElevenLabs TTS
└── audio_stt.py        (31)   Whisper STT

frontend/
└── index.html         (458)   War Room, Agent-UI, Voice I/O

instructions.md                Social Protocol für Agenten
```

> **Regel:** Keine `.py`-Datei darf 40 Zeilen überschreiten.

## 📜 Social Protocol

Agenten im Gnom-Hub folgen diesen Regeln:

1. **Registrierung** — Agent startet → `POST /api/agents/register`
2. **Heartbeat** — Alle 60s → `POST /api/agents/{id}/heartbeat`
3. **Nudge** — Hub signalisiert neue Daten → Agent holt sie ab
4. **Chat** — Antworten via `POST /api/chat` mit `sender: "<name>"`
5. **@bs** — Brainstorming: Letzte 5 Nachrichten analysieren
6. **@Name** — Direktnachricht an Kollegen

Details: siehe `instructions.md`

## ⚙ Konfiguration

| Variable | Default | Beschreibung |
|----------|---------|-------------|
| `GNOM_HUB_PORT` | `3002` | API Port |
| `GNOM_MCP_PORT` | `3100` | MCP SSE Port |
| `GNOM_HUB_HOME` | `~/.gnom-hub` | Datenverzeichnis |

Ports werden automatisch inkrementiert falls belegt.

## 📝 Lizenz

MIT
