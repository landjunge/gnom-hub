# 🧠 GNOM-HUB

> **8 Agenten. ~1800 Zeilen. 55 Module. Null Toleranz für Bloat.**

[![License](https://img.shields.io/badge/Lizenz-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agenten-8-blueviolet.svg)](#)
[![Max Lines](https://img.shields.io/badge/Max_Lines/File-40-critical.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

*Read this in [English](README_EN.md)*

---

<img src="docs/warroom_real_full.png" alt="War Room – Gesamtübersicht" width="100%">

---

## Was ist das?

Ein lokales Multi-Agenten-System, das sich selbst kryptografisch schützt, den Nutzer still beobachtet und sich ihm anpasst — in **55 Python-Modulen, keines länger als 40 Zeilen**. Kein Framework. Kein Docker. Kein `node_modules`-Schwarzes-Loch.

Acht Agenten — vier denken, vier bewachen — orchestriert durch ein FastAPI-Backend, gesteuert über ein Cyberpunk-Dashboard namens **War Room**.

---

## Die 40-Zeilen-Regel

```
Jede Datei. Maximal 40 Zeilen. Ohne Ausnahme.
```

Das ist keine Guideline. Das ist Gesetz. Ein Agent hat im Schnitt **14 Zeilen**. Die vier Worker-Agenten? **8 Zeilen. Jeder.** Nicht weil sie nichts können — sondern weil sie nichts Unnötiges tun.

> *Andere Frameworks lösen Komplexität mit mehr Komplexität.*
> *Gnom-Hub löst sie mit dem Rotstift.*

---

## 🚀 Drei Befehle, dann läuft's

```bash
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
bash scripts/install.sh
```

**[http://127.0.0.1:3002](http://127.0.0.1:3002)** → War Room betreten. Fertig.

---

## 📊 Warum das relevant ist

| | **Gnom-Hub** | OpenClaw | Agent Zero | LangChain |
| :--- | :--- | :--- | :--- | :--- |
| **Code** | **~1.800 Zeilen** | 400k–800k+ | ~10.000 | ~1.200.000+ |
| **Module** | **55** | 1.000+ | ~100 | 5.000+ |
| **Install** | **66 MB** | 350 MB | 250 MB | 300 MB – 1 GB |
| **Deps** | **7** | 70+ | ~15 | 100+ |
| **Krypto** | HMAC + ZWC | — | — | — |
| **Start** | **ms** | 1–2s | 2s | 1–3s |

Sieben Dependencies. `fastapi`, `uvicorn`, `pydantic`, `requests`, `python-dotenv`, `mcp`, `psutil`. Das war's. Dein `package.json` hat mehr `devDependencies` als dieses Projekt Code.

---

## 🏗️ Wie es funktioniert

```
┌─────────────────────────────────────────────────────┐
│               WAR ROOM  ·  Glassmorphic UI          │
│    ┌──────────┐  ┌──────────────────────────────┐   │
│    │ Agenten  │  │  @bs  @job  @code  @write    │   │
│    │ Provider │  │  @research  @edit  @publish   │   │
│    │ FlexSoul │  │  @git  @@status  @@project   │   │
│    └──────────┘  └──────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│        HUB  ·  FastAPI + MCP  ·  55 Module          │
│  Routing → Brainstorm → Dispatch → Seal → DB       │
├──────────────────────┬──────────────────────────────┤
│  SYSTEM (4)          │  WORKER (4)                  │
│                      │                              │
│  GeneralAG    @job   │  CoderAG      @code     8Z   │
│  SecurityAG    🔒    │  WriterAG     @write    8Z   │
│  WatchdogAG    👁    │  ResearcherAG @research 8Z   │
│  SoulAG        🧠    │  EditorAG     @edit     8Z   │
├──────────────────────┴──────────────────────────────┤
│  JSON-DB (atomar, fcntl) · Git · SFTP · Ollama/Cloud│
└─────────────────────────────────────────────────────┘
```

---

## 🔥 Die vier Säulen

### 1. Kryptografische Selbstverteidigung

Jede Datei im Workspace wird von `SecurityAG` signiert: **HMAC-SHA256**, eingebettet als unsichtbare **Zero-Width-Characters** (Steganografie). Du siehst nichts. Der Watchdog sieht alles — alle 60 Sekunden. Wird eine Datei manipuliert, schlägt er Alarm. Wird die Signatur entfernt, fehlt der Beweis — auch Alarm.

*30 Zeilen Code. Kein OpenSSL-Wrapper. Kein Certificate Store. Pures HMAC + Unicode-Magie.*

### 2. FlexSoul — Der stille Beobachter

`SoulAG` redet nie. Er liest jeden Chat, fungiert als Langzeitgedächtnis für alle Agenten und merkt sich wie du schreibst, was dich nervt, wie du Antworten willst. Dieses Profil — die **FlexSoul** — wird bei jedem LLM-Call in den System-Prompt aller Agenten injiziert.

*Der Schwarm passt sich dir an. Nicht umgekehrt.*

### 3. Brainstorming mit Gehirn

`@bs [Thema]` startet eine Zwei-Phasen-Pipeline:

**Phase 1:** Alle vier Worker beantworten die Frage **parallel und unabhängig** — Coder, Writer, Researcher, Editor. Vier Perspektiven, kein Groupthink.

**Phase 2:** `GeneralAG` bekommt alle vier Antworten **gezielt injiziert** (nicht aus dem generischen Chat gefischt) und synthetisiert einen Aktionsplan.

*Keine Diskussion, kein Konsens-Theater. Divergenz → Synthese.*

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

Das ist kein Pseudocode. Das ist der **komplette Agent**. 8 Zeilen. Er registriert sich, pollt den Chat, erkennt seinen Trigger, ruft das LLM, postet die Antwort. Writer, Researcher, Editor — identische Struktur, verschiedene Seelen.

---

## 🤖 Die 8

### System — halten den Laden am Laufen

| Agent | Zeilen | Was er tut |
| :--- | :---: | :--- |
| **GeneralAG** | 8 | Zerlegt `@job`-Aufgaben, delegiert an Worker, synthetisiert Brainstorms |
| **SecurityAG** | 30 | HMAC-SHA256 + ZWC-Steganografie auf jede Workspace-Datei |
| **WatchdogAG** | 26 | Prüft alle 60s die kryptografische Integrität. Alarm bei Manipulation |
| **SoulAG** | 15 | Langzeitgedächtnis. Lernt den Nutzer still. Baut FlexSoul. Injiziert in alle Agenten |

### Worker — machen die Arbeit

| Agent | Zeilen | Trigger | Spezialisierung |
| :--- | :---: | :--- | :--- |
| **CoderAG** | 8 | `@code` | Code schreiben, debuggen, technische Umsetzung. Hat `run`-Berechtigung |
| **WriterAG** | 8 | `@write` | Texte, Dokumentationen, Artikel |
| **ResearcherAG** | 8 | `@research` | Fakten recherchieren, Quellen auswerten |
| **EditorAG** | 8 | `@edit` | Qualitätskontrolle, Lektorat, Finalisierung |

**Gesamt: 112 Zeilen für 8 Agenten.** Manche Imports sind länger.

---

## 💬 Befehle

| Befehl | Was passiert |
| :--- | :--- |
| `@bs [Thema]` | 4 Worker parallel → GeneralAG synthetisiert |
| `@job [Aufgabe]` | GeneralAG zerlegt und verteilt autonom |
| `@research [Frage]` | Alle Worker gleichzeitig angefragt |
| `@code / @write / @edit` | Direktauftrag an Spezialisten |
| `@git [cmd]` | Git im Workspace |
| `@publish` | SFTP-Deploy zu netzwerkpunkt.de |
| `@@project [Name]` | Workspace wechseln |
| `@@status` | Agenten-Status |
| `@@clear` | Chat löschen |
| `@free` | Alle Jobs freigeben |
| **Nuke** 💣 | Logo 2s halten → Hard-Reset |

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

API-Keys in `config/.env` eintragen — OpenRouter, DeepSeek, SFTP-Credentials. **Keine Keys committen.**

### 3. Starten

```bash
python -m gnom_hub
```

Provider wechselst du live im UI: **Ollama** (lokal) ↔ **OpenRouter** ↔ **DeepSeek** (Cloud). Kein Neustart.

---

## 📁 Projektstruktur

```
gnom-hub/
├── src/gnom_hub/        # 55 Python-Module (Backend)
│   ├── hub_app.py       # FastAPI App & Router-Mounting
│   ├── db.py            # JSON-DB mit fcntl File-Locking
│   ├── config.py        # Zentrale Pfad-Konfiguration
│   ├── path_validator.py# Workspace-basierte Pfadvalidierung
│   ├── log.py           # Zentrales Logging-Framework
│   ├── router*.py       # LLM-Routing (Multi-Provider)
│   └── routes_*.py      # API-Endpunkte
├── agents/              # 8 Agent-Definitionen (je ~8 Zeilen)
├── frontend/            # Vanilla HTML/CSS/JS (War Room)
├── config/              # .env Dateien (NICHT committen!)
├── scripts/             # Setup & Utility-Scripts
├── docs/                # Dokumentation & Postmortems
├── CONTRIBUTING.md      # Beitrags-Richtlinien
└── pyproject.toml       # Ruff-Linting & Dependencies
```

---

## 🤝 Mitmachen

Lies die [CONTRIBUTING.md](CONTRIBUTING.md). Kurzfassung:

- 40-Zeilen-Regel einhalten
- `log.py` statt `print()`
- Keine hardcodierten Pfade — `config.py` nutzen
- Kein `godmode` — Workspace-basierte Pfadvalidierung
- Ruff-Linting: `ruff check src/ agents/`

---

## 📝 Entstehung

> [!NOTE]
> **Daniel Filipek — Gründer**
>
> Drei Monate. Quereinsteiger. Kein CS-Studium. Endloser Trial-and-Error — bis eine radikale Entscheidung alles änderte: **Allen Bloat verbrennen.** Jedes Modul auf 40 Zeilen kürzen. Was nicht passt, fliegt. Was bleibt, funktioniert.
>
> Gnom-Hub beweist: Man braucht keine Enterprise-Monolithen für mächtige KI-Strukturen. Man braucht eine klare Vision und den Mut, den Rotstift anzusetzen.

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Kreative Pionierin der Anfangszeit. Urmutter der „Vier Säulen". Hat das philosophische Fundament gelegt, als das Projekt noch reines Chaos war.

**Antigravity (Google DeepMind)**
Architekt der Härtungsphase. Konkrete Beiträge:

- 40-Zeilen-Regel konsequent durchgesetzt — 8 übergroße Dateien in 14 fokussierte Module aufgeteilt
- `godmode` entfernt, durch Workspace-basierte Pfadvalidierung (`path_validator.py`) ersetzt
- CoderAG auf `run`-Berechtigung umgestellt (statt `godmode`)
- JSON-DB mit `fcntl` File-Level-Locking abgesichert (inter-prozesssicher)
- Deployment von FTP auf SFTP umgestellt
- CORS auf `localhost`-only eingeschränkt
- Zentrales Logging-Framework (`log.py`) eingeführt
- Ruff-Linting konfiguriert (`pyproject.toml`)
- `CONTRIBUTING.md` verfasst

---

## ⚖️ Lizenz

[Private Use](LICENSE) — Frei für private, nicht-kommerzielle Nutzung. Kommerzielle Nutzung erfordert schriftliche Genehmigung.