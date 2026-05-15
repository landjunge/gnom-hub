# 🧠 GNOM-HUB

**Jeder Code-Block strikt unter 40 Zeilen. Ernsthaft.**

![Gnom-Hub War Room](screenshot.png)

Ein minimaler, aber mächtiger Orchestrator für autonome KI-Agenten, optimiert für OpenRouter-Modelle.
Der Hub basiert auf einer extrem modularen, kompakten Architektur. Jedes Skript – vom Backend bis zu den Agenten – unterliegt der kompromisslosen **40-Zeilen-Politik**, um das System lean, blitzschnell und überschaubar zu halten.

## 🚀 Schnellstart

```bash
pip install -e .
gnom-hub
```

Danach öffne http://127.0.0.1:3002

## 🤖 Aktive Agenten

Alle Agenten sind vollständig autark, im Root-Verzeichnis platziert und strikt unter 40 Zeilen limitiert.

| Datei | Zeilen | Funktion |
|-------|--------|----------|
| `tinyAG.py` | 33 | Basis-Blueprint für neue Agenten |
| `generalAG.py` | 32 | Aufgabenverteilung & Kommando |
| `summarizerAG.py` | 33 | Essenz-Extraktion & Zusammenfassungen |
| `creatorAG.py` | 39 | Kreativer Agent / Content-Erstellung |
| `backupAG.py` | 33 | System-Snapshots & Wiederherstellung |
| `cronjobAG.py` | 33 | Zeitgesteuerte Aufgaben & Timer |
| `securityAG.py` | 33 | API & System Security Watchdog |
| `watchdogAG.py` | 33 | Prozess- und Status-Überwachung |
| `skillsAG.py` | 33 | Skill-Building & Zuweisung |
| `soulAG.py` | 33 | Agenten-Persönlichkeitsformung |
| `org.py` | 33 | Organisations-Agent |
| `elara.py` | 33 | Code-Agent & Autonome Ausführung |
| `kira.py` | 33 | Code-Agent & Autonome Ausführung |
| `lian.py` | 33 | Code-Agent & Autonome Ausführung |

*Einen neuen Agenten bauen?* Einfach `tinyAG.py` kopieren, `SYSTEM`-Prompt ändern, Port anpassen und starten.

## ✨ Kernfunktionen

- **High-Fidelity UI:** Modernes Glassmorphism-Design mit präzisem 4-Ebenen-Logo-Masking und Neon-Ästhetik.
- **War Room:** Zentrale Einsatzzentrale mit intelligenten `@`-Befehlen und direkter inter-Agenten-Kommunikation.
- **Dynamisches MCP-Routing:** Ein zentraler `hub_mcp.py` registriert dynamisch eine Vielzahl an Tools für Memory, System-Operationen und Agentensteuerung.
- **Rollen-System:** Hierarchische Koordination (z.B. durch `GeneralAG` und `SummarizerAG`).
- **Puls & Registrierung:** Automatische Statusüberwachung via `hub_pulse.py` und REST API.
- **Strenge Architektur-Limitierung:** Jedes `src/gnom_hub/`-Modul und jeder Agent überschreitet niemals 40 Zeilen.

## 🛠️ Wichtige Befehle (War Room)

- `@bs` → Brainstorming-Modus mit allen aktiven Agenten
- `@job` → Weist dem General eine neue Aufgabe zu
- `@idea` → Schnelle Idee in den Speicher schreiben
- `@general @Name` / `@summarizer @Name` → Rollen live umleiten
- `/coffee` → Easter-Egg / Pause
- `/clear` → Chat bereinigen

---

**Lizenz:** MIT
