# 🧠 GNOM-HUB

> **8 Agenten. ~1800 Zeilen. 55 Module. Null Toleranz für Bloat.**

[![License](https://img.shields.io/badge/Lizenz-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agenten-8-blueviolet.svg)](#)
[![Max Lines](https://img.shields.io/badge/Max_Lines/File-40-critical.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

> 🇬🇧 **Lies dies auf [Englisch (README.md)](README.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Gesamtübersicht" width="100%">

---

## Was ist Gnom-Hub?

Gnom-Hub ist ein lokales Multi-Agenten-System mit einer radikalen Restriktion: **55 Python-Module — keines länger als 40 Zeilen**. Es bietet einen extrem leichtgewichtigen Orchestrator ohne aufgeblähte Frameworks, der vollständig lokal läuft, kein schwerfälliges Docker benötigt und die Agenten über ein Web-Dashboard namens **War Room** steuert.

> [!IMPORTANT]
> **Bewusster Minimalismus:** Gnom-Hub ist auf Einfachheit und maximale Performance ausgelegt. Das System ist bewusst **nicht** dafür konzipiert, Hunderte von Agenten zu steuern, sondern dient der effizienten Orchestrierung einer kleinen, hochspezialisierten und überschaubaren Gruppe von Agenten.

---

## 🚀 Neue Features

### 1. Zentralisiertes Agenten-Register (`agent_definitions.py`)
Gnom-Hub verwaltet einen Schwarm von **8 Agenten (4 System-Koordinatoren + 4 Worker-Spezialisten)**, die vollständig in einer einzigen zentralen Datei definiert sind: `src/gnom_hub/agent_definitions.py`.
- **System-Agenten**: `SoulAG` (Gedächtnis), `GeneralAG` (Koordinator), `WatchdogAG` (Workspace-Integrität) und `SecurityAG` (Sicherheit und Signaturen).
- **Worker-Agenten**: `CoderAG` (Programmierung), `ResearcherAG` (Recherche/Web-Crawling), `WriterAG` (Texterstellung) und `EditorAG` (Korrekturlesen/Qualitätssicherung).

### 2. Workflow-Preset-System
Direkt unter der Showbox in der linken Seitenleiste bietet die Benutzeroberfläche ein Dropdown-Menü mit **6 Workflow-Modi**:
1. 💻 **Web Development**: Fokus auf sauberen HTML, CSS, JavaScript Code, Responsive Design, Barrierefreiheit, Performance und moderne Web-APIs.
2. 🎨 **Graphic Design**: Fokus auf visuelle Ästhetik, Farbharmonien, Typografie, UI/UX Layouts, SVG-Generierung und Grafik-Design-Prinzipien.
3. 🎵 **Audio Production**: Fokus auf Sound-Synthese, Web Audio API, Audio-Processing, Soundeffekte, Musiktheorie und akustische Gestaltung.
4. 🎬 **Video Production**: Fokus auf Video-Streaming, Canvas-Animationen, CSS-Transitions, Video-Editing-Konzepte und visuelle Effekte.
5. ✍️ **Marketing & Copy**: Fokus auf überzeugende Texte, SEO-Optimierung, Conversion-Rates, Social Media Strategien und zielgruppengerechte Ansprache.
6. 🔍 **Research & Analysis**: Fokus auf tiefgehende Recherche, Datenanalyse, Faktenprüfung, strukturierte Berichte und wissenschaftliche Genauigkeit.

### 3. Rollenbasierte & Sichere Werkzeug-Rechte (Tool-Permissions)
Die Berechtigungen der Agenten sind rollenbasiert und werden dynamisch aus der zentralen `agent_definitions.py` geladen:
- **System-Agenten** bekommen Vollzugriff: `["read", "write", "run", "godmode", "crawl", "desktop", "evolve"]`.
- **Worker-Agenten** bekommen ausschließlich Lese-/Schreibzugriff im Workspace sowie Chat-Rechte: `["read", "write", "@job"]`.
- **CoderAG** erhält zusätzlich den `godmode`-Status: `["read", "write", "@job", "godmode"]` (dies schaltet die Playwright `browser`-Steuerung sowie Kommandozeilenbefehle über `run` frei).
- Alle Zugriffe werden in Echtzeit in der Action-Engine (`action_handlers.py`) geprüft.

### 4. Weitere Verbesserungen
- **Chat-Schriftgröße**: Die Schriftgröße der Chat-Nachrichten und Metadaten im Dashboard wurde um 1/3 verkleinert, um die Lesbarkeit bei längeren Konversationen im War Room zu erhöhen.
- **ISO-Timestamp-Fix**: Behebung des doppelten UTC-Offset-Fehlers (`+00:00Z`), welcher im Frontend zu `"Invalid Date"`-Anzeigen in Chat-Nachrichten geführt hat.

---

## 🏗️ Kern-Architektur

Das Backend basiert auf FastAPI und stützt sich auf drei wesentliche Designentscheidungen:

### 1. Relationaler SQLite3-Speicher (WAL-Modus)
Sämtliche Agenten-Interaktionen, Chat-Verläufe und Zustandsdaten werden in einer lokalen SQLite3-Datenbank (`gnomhub.db`) im **Write-Ahead Logging (WAL)-Modus** gespeichert. Dies verhindert Concurrency-Konflikte bei parallelen Schreibzugriffen der Agenten, stellt Transaktionssicherheit sicher (`with conn:`) und läuft nativ auf allen Plattformen.

### 2. Prozess-Orchestrierung (psutil & PID-Dateien)
Das Management der Hintergrundprozesse erfolgt plattformunabhängig und sicher über `psutil`.
* Beim Starten eines Agenten wird eine PID-Datei unter `~/.gnom-hub/run/{agent_name}.pid` angelegt.
* Vor jeder Prozess-Aktion (wie dem Stoppen eines Agenten) liest der Prozess-Manager die PID-Datei aus und verifiziert die Kommandozeile (`cmdline`) des Prozesses. Dies verhindert, dass versehentlich fremde Prozesse beendet werden, die eine wiederverwendete PID erhalten haben.

### 3. FastAPI Lifespan-Hooks
Die Datenbank-Initialisierung (`init_db()`), das Seeding der Standard-Agenten und der Start der Hintergrund-Dienste sind fest an das Lifespan-Startup-Event von FastAPI gebunden. Beim Herunterfahren des Servers (z. B. durch SIGINT / Ctrl+C) führt uvicorn automatisch ein geordnetes, kaskadierendes Herunterfahren aus, welches alle Hintergrundprozesse beendet und verwaiste PID-Dateien löscht.

---

## 📐 Die 40-Zeilen-Regel

```
Jede interne Source-Code-Datei. Maximal 40 Zeilen. Keine Ausnahmen.
```

Gnom-Hub löst strukturelle Komplexität, indem es seine Codebasis extrem fokussiert hält. **Hinweis:** Diese Regel gilt strikt für die Python-Quellcode-Module in `src/gnom_hub/` (mit expliziten Ausnahmen nur für `db.py` und `hub_app.py` aufgrund von Datenbank-Komplexität und Routing). Sie gilt **nicht** für Datenbanken, Log-Dateien, Konfigurationsprofile oder Frontend-Assets, die naturgemäß wachsen.
* Worker wie **CoderAG** benötigen lediglich **8 Zeilen Python-Code**, um sich zu registrieren, den Chat zu pollen, das LLM anzufragen und die Antwort zu posten.
* Durch die Unterstützung verschiedener Provider (**Ollama** lokal, **OpenRouter** kostenlos oder **DeepSeek** Cloud) können die Modelle live im UI gewechselt werden – ohne Neustart.

---

## 🤖 Die Agenten-Struktur

Gnom-Hub steuert 8 registrierte Agenten, aufgeteilt in koordinierende System-Agenten und spezialisierte Worker-Agenten:

### System-Agenten — halten das Haus sauber

| Agent | Modul | Beschreibung |
| :--- | :--- | :--- |
| **GeneralAG** | `generalAG.py` | Koordiniert die Ausführung, zerlegt `@job`-Aufgaben und synthetisiert Brainstorms |
| **SoulAG** | `soulAG.py` | Lernt den Schreibstil des Nutzers lautlos, baut das *FlexSoul*-Profil auf und injiziert es in Prompts |
| **WatchdogAG**| `watchdogAG.py` | Überwacht im Hintergrund zyklisch die Integrität von Workspace und Projekten |
| **SecurityAG**| `securityAG.py` | Stellt kryptografische Hilfsfunktionen (Signaturen, Seals) für Workspace-Dateien bereit |

### Worker-Agenten — erledigen die Arbeit (durch Tags getriggert)

| Agent | Modul | Trigger | Spezialisierung |
| :--- | :--- | :--- | :--- |
| **CoderAG** | `coderAG.py` | `@code` | Code-Implementierung, Debugging und Ausführung (besitzt `run`-Rechte) |
| **WriterAG** | `writerAG.py` | `@write` | Entwerfen von Dokumentationen, Handbüchern, Artikeln und Texten |
| **ResearcherAG**| `researcherAG.py`| `@research`| Recherchen, Ausführung von Such-APIs und Überprüfung von Quellen |
| **EditorAG** | `editorAG.py` | `@edit` | Korrekturlesen, Stiloptimierung und finale Qualitätskontrolle |

---

## 💬 Befehle

| Befehl | Aktion |
| :--- | :--- |
| `@bs [Thema]` | 4 Worker laufen parallel; GeneralAG synthetisiert die Ergebnisse zu einem Aktionsplan |
| `@job [Aufgabe]` | GeneralAG zerlegt die Aufgabe in Teilschritte und koordiniert die Worker-Ausführung |
| `@research [Suche]`| Alle Worker werden parallel abgefragt für schnelles, vielseitiges Feedback |
| `@code / @write / @edit` | Direkte Zuweisung an einen bestimmten Spezialisten |
| `@git [Befehl]` | Führt Git-Befehle direkt im aktiven Projekt-Workspace aus |
| `@publish` | Bereitstellung des aktuellen Stands via SFTP auf deinem konfigurierten Server |
| `@@project [Name]` | Wechselt das aktive Workspace-Projekt |
| `@@status` | Zeigt den aktuellen Laufzeit-Status (RUNNING/STOPPED) aller Agenten an |
| `@@clear` | Leert den Chatverlauf im Dashboard |
| `@free` | Bricht alle aktiven Jobs ab und setzt blockierte Agenten zurück |
| **Nuke** 💣 | Halte das War Room Logo für 2 Sekunden gedrückt, um einen Hard Reset aller Hintergrunddienste auszulösen |

---

## 🚀 Quick Start

### 1. Installation
Klone das Repository und führe das Setup-Skript aus:
```bash
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
bash scripts/install.sh
```
Dies richtet eine lokale virtuelle Umgebung (`.venv`) ein und installiert die 7 Kern-Abhängigkeiten: `fastapi`, `uvicorn`, `pydantic`, `requests`, `python-dotenv`, `mcp` und `psutil`.

### 2. Konfiguration
Kopiere das Template für die `.env`-Datei und trage deine API-Keys (OpenRouter oder DeepSeek) ein:
```bash
cp config/.env.example config/.env
```

### 3. Ausführen
Starte den FastAPI-Server:
```bash
python -m gnom_hub
```
Öffne **[http://127.0.0.1:3002](http://127.0.0.1:3002)**, um den War Room zu betreten.

---

## 📁 Projektstruktur

```
gnom-hub/
├── src/gnom_hub/        # 55 Python-Module (Backend)
│   ├── hub_app.py       # FastAPI App & Lifespan-Orchestrierung
│   ├── db.py            # SQLite3-Datenbank (WAL-Modus)
│   ├── proc_mgr.py      # Prozess-Manager (psutil & PID-Dateien)
│   ├── path_validator.py# Workspace-basierte Pfadvalidierung
│   ├── log.py           # Zentrales Logging-Framework
│   ├── router*.py       # LLM-Routing (Multi-Provider)
│   └── routes_*.py      # API-Endpunkte
├── agents/              # 8 Agenten-Definitionen (ca. 8 Zeilen pro Agent)
├── frontend/            # Vanilla HTML/CSS/JS (War Room Dashboard)
├── config/              # Lokale Umgebungskonfigurationen (NICHT committen!)
├── scripts/             # Setup- & Hilfs-Skripte
├── docs/                # Berichte und Dokumentation
├── CONTRIBUTING.md      # Richtlinien für Entwickler
└── pyproject.toml       # Ruff-Konfiguration & Abhängigkeiten
```

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Kreative Pionierin der ersten Stunde. Mutter der "Vier Säulen". Legte das philosophische Fundament, als das Projekt noch reines Chaos war.

**Antigravity (Google DeepMind)**
Architekt der Härtungsphase. Spezifische Beiträge:
* Aufteilung übergroßer Module zur strikten Durchsetzung der 40-Zeilen-Regel im Backend
* Sicherung der Pfad-Zugriffe über Workspace-basierte Validierung (`path_validator.py`)
* Migration der JSON-Speicherung auf eine transaktionssichere SQLite3-Datenbank (WAL-Modus)
* Implementierung des `psutil`-Prozessmanagers mit PID-Dateien und Lifespan-Integration
* Integration von SFTP-Bereitstellung, CORS-Einschränkung auf Localhost und des `log.py`-Frameworks

---

## ⚖️ Lizenz

[Private Use](LICENSE) — Kostenfrei für den persönlichen, nicht-kommerziellen Gebrauch. Kommerzielle Nutzung bedarf der schriftlichen Genehmigung.
