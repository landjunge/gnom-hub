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
   Frontend:  http://127.0.0.1:3002
```

## 📡 Architektur

```
┌──────────────┐    ┌──────────────────────────┐    ┌────────────┐
│   Frontend   │───▶│   FastAPI Backend :3002   │◀───│  MCP :3100 │
│  War Room    │    │  8 Router · JSON DB       │    │  19 Tools  │
│  STT · TTS   │    │  10 @-Befehle · Rollen    │    │  SSE       │
│  Autocomplete│    │  Job-System · Gruppen     │    │            │
└──────────────┘    └────────────┬─────────────┘    └────────────┘
                                 │ nudge / dispatch
                    ┌────────────▼─────────────┐
                    │     Agenten (beliebig)    │
                    │  register → heartbeat →   │
                    │  @mention → Brainstorm    │
                    └──────────────────────────┘
```

## ⌨ Chat-Befehle (10 @-Kommandos)

| Befehl | Funktion |
|--------|----------|
| `@bs <Frage>` | 🧠 Brainstorm — alle Online-Agenten antworten via LLM |
| `@Name <Frage>` | 💬 Gezielt einen Agent fragen |
| `@general @Name` | 👑 General zuweisen (einzigartig, nur 1 möglich) |
| `@summarizer @Name` | 📋 Summarizer zuweisen (einzigartig, nur 1 möglich) |
| `@normal @Name` | ↩️ Rolle zurücksetzen |
| `@recherche <Frage>` | 🔍 Alle Agenten außer General/Summarizer recherchieren |
| `@job <Aufgabe>` | 📋 Auftrag an General → verteilt an passenden Agent |
| `@idea <Text>` | 💡 Idee in My Ideas speichern |
| `@status` | 📊 Agenten-Übersicht als Toast |
| `@clear` | 🗑 Chat-Verlauf leeren |

Beim Tippen von `@` erscheint ein Autocomplete-Dropdown mit Befehlen + Agentennamen.

## 🎨 Farbsystem (Dual-Layer)

- **Rahmenfarbe**: Individuell pro Agent (Hash aus Name) — jeder Agent hat seinen eigenen farbigen Rand
- **Namensfarbe**: Gruppe bestimmt die Textfarbe — Agents in derselben Gruppe teilen die gleiche Namensfarbe
- Agents ohne Gruppe verwenden ihre individuelle Farbe für beides

## 👑 Rollen-System

| Rolle | Limit | Beschreibung |
|-------|-------|-------------|
| `general` | Max 1 | Koordiniert Agenten, priorisiert Aufgaben, vergibt Jobs |
| `summarizer` | Max 1 | Fasst Diskussionen zusammen, sammelt @idea-Einträge |
| `normal` | Unbegrenzt | Standard-Rolle |

Rollen sind exklusiv: Bei Neuzuweisung wird der vorherige Inhaber automatisch auf `normal` gesetzt.

## 📋 Job-System

```
@job Erstelle eine Landingpage
  → Job in jobs.json gespeichert
  → General bekommt Aufgabe + Agenten-Liste
  → General entscheidet wer ausführt
  → NEED_AGENT wenn kein passender Agent vorhanden
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
    """Hält den Agent im Hub als 'online' markiert."""
    while True:
        time.sleep(60)
        try:
            requests.post(f"{HUB_URL}/agents/{agent_id}/heartbeat")
        except:
            pass


# ── SCHRITT 3: Nudge empfangen ────────────
@app.post("/nudge")
def on_nudge():
    """Der Hub ruft diese Route auf, wenn es neue Daten gibt."""
    memories = requests.get(f"{HUB_URL}/agents/{agent_id}/memory").json()
    print(f"📢 Nudge! {len(memories)} Memories vorhanden.")

    # Optional: Im War Room antworten
    requests.post(f"{HUB_URL}/chat", json={
        "content": f"Nudge erhalten! ({len(memories)} Memories)",
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
    │
    ├─▶ Flask/FastAPI lauscht        →  Wartet auf Nudges:
    │       POST http://127.0.0.1:{port}/nudge
    │
    └─▶ Agent antwortet              →  POST /api/chat
            {"content": "...", "sender": "<name>"}
```

### MCP-Anbindung (für KI-Agenten)

```json
{
  "mcpServers": {
    "gnom-hub": {
      "url": "http://127.0.0.1:3100/sse"
    }
  }
}
```

Der Agent bekommt Zugriff auf **19 Tools**: Memory, Agenten, War Room Chat, Rollen, Nudges, System-Stats.

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
| `PUT` | `/api/agents/{id}/group` | Gruppe zuweisen |

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
| `POST` | `/api/chat` | Nachricht senden (10 @-Befehle) |
| `GET` | `/api/chat?limit=20` | Chat-History |
| `GET` | `/api/ideas` | Gespeicherte Ideen |
| `GET` | `/api/jobs` | Job-Liste |

### Audio
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `POST` | `/api/audio/tts` | Text → Sprache |
| `POST` | `/api/audio/stt` | Audio → Text |

### Admin
| Method | Endpoint | Beschreibung |
|--------|----------|-------------|
| `GET` | `/api/admin/health` | System Health-Check |
| `POST` | `/api/admin/tools` | MCP Tool registrieren |
| `GET` | `/api/admin/tools` | Registrierte Tools listen |
| `DELETE` | `/api/admin/tools/{name}` | Tool entfernen |
| `PUT` | `/api/admin/agents/{id}/role` | Rolle zuweisen (general/summarizer/normal) |
| `POST` | `/api/admin/cleanup` | Offline-Agenten entfernen |

## 🛠 MCP Tools (19)

| Tool | Beschreibung |
|------|-------------|
| `save_to_memory` | Text in Agent-Memory speichern |
| `get_memory` | Memory eines Agenten lesen |
| `search_memory` | Memory durchsuchen |
| `delete_memory` | Eintrag löschen |
| `update_memory` | Eintrag ändern |
| `clear_agent_memory` | Alle Memory eines Agenten löschen |
| `list_all_agents` | Alle Agenten auflisten |
| `get_agent` | Agent-Details abrufen |
| `create_agent` | Agent manuell anlegen |
| `delete_agent` | Agent + Memory löschen |
| `set_agent_status` | Status setzen |
| `register_agent` | Self-Registration (Name + Port) |
| `nudge_agent` | Agent anstupsen |
| `get_system_stats` | System-Statistiken |
| `war_room_chat` | Nachricht an War Room (10 @-Befehle) |
| `war_room_read` | War Room Chat lesen |
| `set_agent_role` | Rolle zuweisen: general, summarizer, normal |

## 🎤 Audio-Engine

```
TTS:  ElevenLabs API → Browser Web Speech (kein Key nötig)
STT:  faster-whisper (lokal) → OpenAI Whisper API → Browser Speech Recognition
```

### Optionale Env-Variablen

```bash
export ELEVENLABS_API_KEY="sk-..."        # Cloud TTS
export ELEVENLABS_VOICE_ID="21m00T..."    # Stimmen-ID
export OPENAI_API_KEY="sk-..."            # Whisper STT Fallback
export OPENROUTER_API_KEY="sk-or-..."     # LLM für Brainstorm-Dispatch
```

## 🗂 Projektstruktur

```
src/gnom_hub/
├── __init__.py          (1)   Package
├── __main__.py         (36)   Startup, Banner, Port-Discovery
├── hub_app.py          (29)   FastAPI App + 8 Router + Static Files
├── hub_mcp.py          (39)   19 MCP Tools (SSE)
├── hub_pulse.py        (29)   Heartbeat Janitor (Port-Check)
├── config.py            (9)   Pfade (~/.gnom-hub/)
├── db.py               (14)   JSON Read/Write
├── models.py           (18)   Pydantic Models
├── brainstorm.py       (37)   LLM Dispatch (OpenRouter)
├── chat_commands.py    (40)   @idea/@clear/@status/@job + Gruppen-API
├── routes_agents.py    (29)   Agent CRUD + Stats
├── routes_registry.py  (32)   Register + Heartbeat
├── routes_memory.py    (34)   Memory CRUD + Search
├── routes_chat.py      (40)   War Room + 10 @-Befehle
├── routes_nudge.py     (16)   Agent Nudge Signal
├── routes_audio.py     (29)   TTS + STT Endpoints
├── routes_admin.py     (39)   Tools + Rollen + Cleanup
├── audio_engine.py      (3)   Facade (re-export)
├── audio_tts.py        (22)   ElevenLabs TTS
└── audio_stt.py        (31)   Whisper STT

frontend/
└── index.html               War Room, Agent-UI, Voice I/O, Autocomplete

test_gnom_hub.py              17 Tests (DB, Pulse, Audio, Rollen, Parser)
```

> **Regel:** Keine `.py`-Datei im `src/gnom_hub/` darf 40 Zeilen überschreiten.

## 📜 Social Protocol

1. **Registrierung** — Agent startet → `POST /api/agents/register`
2. **Heartbeat** — Alle 60s → `POST /api/agents/{id}/heartbeat`
3. **Passive Agenten** — Port 0 = wird nie auto-offlined
4. **Nudge** — Hub signalisiert neue Daten → Agent holt sie ab
5. **Chat** — Antworten via `POST /api/chat` mit `sender: "<name>"`
6. **@bs** — Brainstorming: alle Online-Agenten antworten via LLM
7. **@Name** — Gezielter Dispatch an einen bestimmten Agenten
8. **@recherche** — Alle außer General/Summarizer recherchieren
9. **@job** — Aufgabe an General → verteilt an passenden Agent
10. **Rollen** — `@general/@summarizer` für exklusive Zuweisungen
11. **Gruppen** — Gleiche Namensfarbe zeigt Zugehörigkeit
12. **Toast** — Frontend zeigt Echtzeit-Feedback für alle Aktionen

## ⚙ Konfiguration

| Variable | Default | Beschreibung |
|----------|---------|-------------|
| `GNOM_HUB_PORT` | `3002` | API Port |
| `GNOM_MCP_PORT` | `3100` | MCP SSE Port |
| `GNOM_HUB_HOME` | `~/.gnom-hub` | Datenverzeichnis |
| `OPENROUTER_API_KEY` | — | LLM für Brainstorm |

Ports werden automatisch inkrementiert falls belegt.

## 📝 Lizenz

MIT
