# 🧠 GNOM-HUB

**Jeder Agent unter 40 Zeilen. Ernsthaft.**

![Gnom-Hub War Room](screenshot.png)

Ein minimaler, aber mächtiger Orchestrator für lokale KI-Agenten.
Eine Datei kopieren, SYSTEM-Prompt ändern, starten — fertig.

## 🚀 Schnellstart

```bash
pip install -e .
gnom-hub
```

Danach öffne http://127.0.0.1:3002

## 🤖 Agenten

| Datei | Rolle | Zeilen |
|-------|-------|--------|
| `tiny_agent.py` | 🧠 Basis-Agent | 38 |
| `general.py` | ⚔️ Aufgaben verteilen | 41 |
| `summarizer.py` | 📋 Essenz extrahieren | 40 |
| `skills.py` | 🛠️ Skills bauen & zuweisen | 41 |
| `cronjob.py` | ⏰ Zeitgesteuerte Jobs | 41 |
| `soul.py` | 👻 Agent-Persönlichkeit formen | 41 |
| `apikeys.py` | 🔑 Key-Management | 41 |
| `watchdog.py` | 🐕 Prozesse überwachen | 41 |

Eigenen Agent bauen? `tiny_agent.py` kopieren, `SYSTEM` ändern. Das war's.

## ✨ Kernfunktionen

- 19 MCP-Tools für Memory, Chat und Agenten-Management
- War Room mit intelligenten @-Befehlen
- Rollen-System: General und Summarizer
- Automatische Erkennung: Agenten sagen einfach "Suche MCP-Server"
- Strenge 40-Zeilen-Regel pro Datei

## Wichtige Chat-Befehle

- `@bs` → Brainstorming mit allen Agenten
- `@job` → Aufgabe an den General
- `@idea` → Persönliche Idee speichern
- `@general @Name` / `@summarizer @Name` → Rollen vergeben

---

**Lizenz:** MIT
