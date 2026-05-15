# 🧠 GNOM-HUB

**Jeder Agent strikt unter 55 Zeilen. Ernsthaft.**

![Gnom-Hub War Room](screenshot.png)

Ein minimaler, aber mächtiger Orchestrator für autonome KI-Agenten, optimiert für OpenRouter-Modelle (wie DeepSeek).
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
| `tinyAG.py` | 🧠 Basis-Agent | 38 |
| `generalAG.py` | ⚔️ Aufgaben verteilen | 41 |
| `summarizerAG.py` | 📋 Essenz extrahieren | 40 |
| `skillsAG.py` | 🛠️ Skills bauen & zuweisen | 41 |
| `cronjobAG.py` | ⏰ Zeitgesteuerte Jobs | 41 |
| `soulAG.py` | 👻 Agent-Persönlichkeit formen | 41 |
| `apikeysAG.py` | 🔑 Key-Management | 41 |
| `watchdogAG.py` | 🐕 Prozesse überwachen | 41 |

Eigenen Agent bauen? `tinyAG.py` kopieren, `SYSTEM` ändern. Das war's.

## ✨ Kernfunktionen

- **High-Fidelity UI:** Glassmorphism-Design mit präzisem 4-Ebenen-Logo-Masking und Neon-Ästhetik.
- **15 MCP-Tools** für lokales Memory, Chat-Management und Agenten-Steuerung.
- **War Room** mit intelligenten @-Befehlen und inter-Agenten-Kommunikation.
- **Rollen-System:** General und Summarizer koordinieren die Agenten-Schwärme.
- **Automatische Erkennung:** Agenten können sich selbst über das Backend (`hub_app.py`) registrieren.
- **Strenge Limitierung:** Maximale Übersicht durch strikte Code-Limits pro Modul (≤ 55 Zeilen).

## Wichtige Chat-Befehle

- `@bs` → Brainstorming mit allen Agenten
- `@job` → Aufgabe an den General
- `@idea` → Persönliche Idee speichern
- `@general @Name` / `@summarizer @Name` → Rollen vergeben

---

**Lizenz:** MIT
