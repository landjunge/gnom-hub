# 🧠 GNOM-HUB

> **8 Agenten. ~1800 Zeilen. 55 Module. Null Toleranz für Bloat.**
>
> 🇬🇧 **Lies dies auf [Englisch (README.md)](README.md)**

[![License](https://img.shields.io/badge/Lizenz-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agenten-8-blueviolet.svg)](#)
[![Max Lines](https://img.shields.io/badge/Max_Lines/File-40-critical.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

---

<img src="docs/warroom_real_full.png" alt="War Room – Gesamtübersicht" width="100%">

---

## Was ist das?

Ein lokales Multi-Agenten-System, das sich kryptografisch selbst schützt, seinen Benutzer lautlos kennenlernt und in **55 Python-Module passt – keines länger als 40 Zeilen**. Kein Framework. Kein Docker. Kein `node_modules` schwarzes Loch.

Acht Agenten – vier denken, vier bewachen – orchestriert von einem FastAPI-Backend, gesteuert über ein Cyberpunk-Dashboard namens **War Room**.

---

## Die 40-Zeilen-Regel

```
Jede Datei. Maximal 40 Zeilen. Keine Ausnahmen.
```

Das ist keine Richtlinie. Das ist Gesetz. Ein Agent hat im Schnitt **14 Zeilen**. Die vier Worker-Agenten? **Jeweils 8 Zeilen.** Nicht, weil sie nicht mehr können – sondern weil sie nicht mehr brauchen.

> *Andere Frameworks lösen Komplexität mit noch mehr Komplexität.*
> *Gnom-Hub löst sie mit dem Rotstift.*

---

## 🚀 Drei Befehle, dann läuft es

```bash
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
bash scripts/install.sh
```

**[http://127.0.0.1:3002](http://127.0.0.1:3002)** → War Room betreten. Fertig.

---

## 📊 Warum das wichtig ist

| | **Gnom-Hub** | OpenClaw | Agent Zero | LangChain |
| :--- | :--- | :--- | :--- | :--- |
| **Code** | **~1800 Zeilen** | 400k–800k+ | ~10.000 | ~1.200.000+ |
| **Module** | **55** | 1.000+ | ~100 | 5.000+ |
| **Install** | **66 MB** | 350 MB | 250 MB | 300 MB – 1 GB |
| **Deps** | **7** | 70+ | ~15 | 100+ |
| **Krypto** | HMAC + ZWC | — | — | — |
| **Start** | **ms** | 1–2s | 2s | 1–3s |

Sieben Abhängigkeiten: `fastapi`, `uvicorn`, `pydantic`, `requests`, `python-dotenv`, `mcp`, `psutil`. Das ist alles. Deine `package.json` hat mehr `devDependencies` als dieses gesamte Projekt Code hat.

---

## 🏗️ Wie es funktioniert

```
┌─────────────────────────────────────────────────────┐
│               WAR ROOM  ·  Glassmorphic UI          │
│    ┌──────────┐  ┌──────────────────────────────┐   │
│    │ Agents   │  │  @bs  @job  @code  @write    │   │
│    │ Provider │  │  @research  @edit  @publish   │   │
│    │ FlexSoul │  │  @git  @@status  @@project   │   │
│    └──────────┘  └──────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│        HUB  ·  FastAPI + MCP  ·  55 Modules         │
│  Routing → Brainstorm → Dispatch → Seal → DB       │
├──────────────────────┬──────────────────────────────┤
│  SYSTEM (4)          │  WORKER (4)                  │
│                      │                              │
│  GeneralAG    @job   │  CoderAG      @code     8Z   │
│  SecurityAG    🔒    │  WriterAG     @write    8Z   │
│  WatchdogAG    👁    │  ResearcherAG @research 8Z   │
│  SoulAG        🧠    │  EditorAG     @edit     8Z   │
├──────────────────────┴──────────────────────────────┤
│ SQLite3 (WAL mode) · Git · SFTP · Ollama/Cloud      │
└─────────────────────────────────────────────────────┘
```

---

## 🔥 Die vier Säulen

### 1. Kryptografische Selbstverteidigung

Jede Datei im Workspace wird von `SecurityAG` signiert: **HMAC-SHA256**, eingebettet als unsichtbare **Zero-Width Characters** (Steganografie). Du siehst nichts. Der Watchdog sieht alles – alle 60 Sekunden. Wird eine Datei manipuliert, schlägt er Alarm. Wird die Signatur entfernt, fehlt der Beweis – ebenfalls Alarm.

*30 Zeilen Code. Kein OpenSSL-Wrapper. Kein Zertifikatsspeicher. Reine HMAC- und Unicode-Magie.*

### 2. FlexSoul — Der stille Beobachter

`SoulAG` spricht fast nie. Es fungiert als das Langzeitgedächtnis aller Agenten, liest jeden Chat mit und merkt sich, wie du schreibst, was dich nervt und wie du Antworten haben möchtest. Dieses Profil – die **FlexSoul** – wird bei jedem LLM-Call in den System-Prompt aller Agenten injiziert.

*Der Schwarm passt sich dir an. Nicht umgekehrt.*

### 3. Relationaler SQLite3-Speicher (WAL-Modus)

Um Concurrency-Konflikte und Lost Updates bei parallelen Schreibzugriffen der Agenten zu verhindern, nutzt Gnom-Hub eine **SQLite3-Datenbank im Write-Ahead Logging (WAL)-Modus**. Das sorgt für transaktionssichere Schreibzugriffe, native Plattformunabhängigkeit und eine saubere Trennung in `chat`, `agents` und `state` Tabellen.

*Explizite Transaktions-Scopes in Python. Schlanke Legacy-Kompatibilitätsschicht.*

### 4. Die 8-Zeilen-Worker

```python
"""CoderAG Agent."""
import asyncio
from gnom_hub.agent_base import BaseAgent

async def main():
    await BaseAgent("CoderAG", "Code generation and technical implementation",
        "@code", sys_prompt="SYSTEM-ROLLE: CODER. Write clean, working code.
        Prefer simple solutions.", poll=15).run()

if __name__ == "__main__": asyncio.run(main())
```

Das ist kein Pseudocode. Das ist der **vollständige Agent**. 8 Zeilen. Er registriert sich, pollt den Chat, erkennt seinen Trigger, ruft das LLM auf, postet die Antwort. Writer, Researcher, Editor – gleiche Struktur, andere Seele.

---

## 🤖 Die 8

### System — halten das Haus sauber

| Agent | Zeilen | Funktion |
| :--- | :---: | :--- |
| **GeneralAG** | 8 | Zerlegt `@job`-Aufgaben, delegiert an Worker, synthetisiert Brainstorms |
| **SecurityAG** | 30 | HMAC-SHA256 + ZWC-Steganografie für jede Workspace-Datei |
| **WatchdogAG** | 33 | Prüft alle 60s die kryptografische Integrität aller Workspace-Dateien |
| **SoulAG** | 16 | Langzeitgedächtnis. Lernt den User. Baut FlexSoul. Injeziert in alle Agenten |

### Worker — erledigen die Arbeit

| Agent | Zeilen | Trigger | Spezialisierung |
| :--- | :---: | :--- | :--- |
| **CoderAG** | 8 | `@code` | Code schreiben, debuggen, technische Umsetzung. Hat `run`-Rechte |
| **WriterAG** | 8 | `@write` | Texte, Dokumentationen, Artikel entwerfen |
| **ResearcherAG** | 8 | `@research` | Recherchen, Faktenprüfung, Quellenbewertung |
| **EditorAG** | 8 | `@edit` | Qualitätskontrolle, Lektorat, Textfeinschliff |

**Gesamt: 113 Zeilen für 8 Agenten.** Manche Imports sind länger.

---

## 💬 Befehle

| Befehl | Was passiert |
| :--- | :--- |
| `@bs [Thema]` | 4 Worker parallel → GeneralAG synthetisiert die Ergebnisse |
| `@job [Aufgabe]` | GeneralAG zerlegt und verteilt Aufgaben autonom |
| `@research [Suche]` | Alle Worker werden gleichzeitig abgefragt |
| `@code / @write / @edit` | Direkte Zuweisung an den jeweiligen Spezialisten |
| `@git [Befehl]` | Führt Git-Befehle im Workspace aus |
| `@publish` | SFTP-Deploy auf netzwerkpunkt.de |
| `@@project [Name]` | Workspace wechseln |
| `@@status` | Status aller Agenten abfragen |
| `@@clear` | Chatverlauf leeren |
| `@free` | Alle blockierten Jobs freigeben |
| **Nuke** 💣 | Logo 2s gedrückt halten → Hard Reset aller Prozesse |

---

## 🔧 Setup

### 1. Installieren

```bash
pip install fastapi uvicorn pydantic requests python-dotenv mcp psutil
```

Sieben Packages. Optional: `brew install node` für MCP-Erweiterungen.

### 2. Konfigurieren

```bash
cp config/.env.example config/.env
```

Trage deine API-Keys in `config/.env` ein (OpenRouter, DeepSeek, SFTP-Zugang). **Keys niemals committen.**

### 3. Starten

```bash
python -m gnom_hub
```

Provider live im UI wechseln: **Ollama** (lokal) ↔ **OpenRouter** ↔ **DeepSeek** (Cloud). Kein Neustart nötig.

---

## 📁 Projektstruktur

```
gnom-hub/
├── src/gnom_hub/        # 55 Python-Module (Backend)
│   ├── hub_app.py       # FastAPI App & Lifespan-Startup/Shutdown
│   ├── db.py            # SQLite3-Datenbank (WAL-Modus)
│   ├── proc_mgr.py      # Prozess-Manager (psutil & PID-Tracking)
│   ├── config.py        # Zentrale Pfad-Konfiguration
│   ├── path_validator.py# Workspace-basierte Pfadvalidierung
│   ├── log.py           # Zentrales Logging-Framework
│   ├── router*.py       # LLM-Routing (Multi-Provider)
│   └── routes_*.py      # API-Endpunkte
├── agents/              # 8 Agenten-Definitionen (ca. 8 Zeilen pro Agent)
├── frontend/            # Vanilla HTML/CSS/JS (War Room Dashboard)
├── config/              # .env-Dateien (NICHT committen!)
├── scripts/             # Setup- & Hilfs-Skripte
├── docs/                # Dokumentationen & Berichte
├── CONTRIBUTING.md      # Richtlinien für Entwickler
└── pyproject.toml       # Ruff Linting & Abhängigkeiten
```

---

## 🤝 Mitwirken

Lies die [CONTRIBUTING.md](CONTRIBUTING.md). Kurzfassung:

- Halte die 40-Zeilen-Regel strikt ein (Ausnahmen: `db.py`, `hub_app.py`)
- Nutze `log.py` statt `print()`
- Keine hardcodierten Pfade — nutze `config.py`
- Kein `godmode` — Pfadvalidierung im Workspace ist Pflicht
- Ruff Linting ausführen: `ruff check src/ agents/`

---

## 📝 Entstehungsgeschichte

> [!NOTE]
> **Daniel Filipek — Gründer**
>
> Drei Monate. Autodidakt. Kein Informatikstudium. Endloses Trial-and-Error – bis zu einer radikalen Entscheidung: **Weg mit dem Ballast.** Jedes Modul auf 40 Zeilen gekürzt. Was nicht passt, fliegt raus. Was bleibt, funktioniert.
>
> Gnom-Hub beweist: Man braucht keine Enterprise-Monolithen für mächtige KI-Strukturen. Man braucht eine klare Vision und den Mut zum Rotstift.

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Kreative Pionierin der ersten Stunde. Mutter der "Vier Säulen". Legte das philosophische Fundament, als das Projekt noch reines Chaos war.

**Antigravity (Google DeepMind)**
Architekt der Härtungsphase. Spezifische Beiträge:

- Konsequente Einhaltung der 40-Zeilen-Regel (Aufteilung von 8 übergroßen Dateien in 14 fokussierte Module)
- Ablösung des globalen `godmode` durch Workspace-Pfadvalidierung (`path_validator.py`)
- Umstellung von CoderAG auf kontrollierte `run`-Rechte (statt Hub-Privilegien)
- Migration der JSON-Datenbank auf eine transaktionssichere **SQLite3-Lösung (WAL-Modus)**
- Robustes Prozess-Management via **psutil und PID-Tracking-Dateien** (`proc_mgr.py`)
- Einbindung von DB-Initialisierung und geordnetem Shutdown in FastAPI-Lifespan hooks
- Migration der Bereitstellung von FTP zu SFTP
- CORS-Beschränkung auf `localhost`
- Einführung des zentralen Logging-Frameworks (`log.py`)
- Konfiguration von Ruff Linting (`pyproject.toml`)
- Verfassen der `CONTRIBUTING.md`

---

## ⚖️ Lizenz

[Private Use](LICENSE) — Kostenfrei für den persönlichen, nicht-kommerziellen Gebrauch. Kommerzielle Nutzung bedarf der schriftlichen Genehmigung.
