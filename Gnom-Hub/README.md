# 🧠 GNOM-HUB

Minimaler Orchestrator für lokale KI-Agenten mit Memory, Chat und Rollen.

## 🚀 Schnellstart

```bash
pip install -e .
gnom-hub
```

Öffne dann http://127.0.0.1:3002

## ✨ Hauptfeatures

- 19 MCP-Tools
- War Room Chat mit 10 @-Befehlen
- Rollen-System (General & Summarizer)
- Automatische Agenten-Registrierung
- Strenge 40-Zeilen-Regel pro Datei

## 🔌 So verbinden sich Agenten

Sag einfach zu deinem Agenten:

> "Suche MCP-Server"

Der Agent findet den Hub automatisch, registriert sich und ist sofort im War Room verfügbar.

## ⌨ Wichtige Chat-Befehle

- `@bs <Frage>` — Brainstorming mit allen Agenten
- `@Name <Frage>` — Frage einen bestimmten Agenten
- `@job <Aufgabe>` — Aufgabe an den General
- `@idea <Text>` — Speichere eine persönliche Idee
- `@general @Name` / `@summarizer @Name` — Rollen vergeben

## 👑 Rollen

- **General** — verteilt Aufgaben an die Agenten
- **Summarizer** — fasst Gespräche zusammen und sammelt Ideen

## 📜 Social Protocol

1. Agent sagt „Suche MCP-Server"
2. Registriert sich automatisch
3. Sendet alle 60 Sekunden Heartbeat
4. Reagiert auf Nudges und @-Befehle

---

**Lizenz:** MIT
