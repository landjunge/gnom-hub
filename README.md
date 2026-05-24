# 🧠 GNOM-HUB

> **8 agents. ~1,800 lines. 55 modules. Zero tolerance for bloat.**

[![License](https://img.shields.io/badge/License-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agents-8-blueviolet.svg)](#)
[![Max Lines](https://img.shields.io/badge/Max_Lines/File-40-critical.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

> 🇩🇪 **Read this in [German (README.de.md)](README.de.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Overview" width="100%">

---

## What is Gnom-Hub?

Gnom-Hub is a local multi-agent system designed with a radical constraint: **55 Python modules — none longer than 40 lines**. It provides a lightweight, zero-framework orchestrator that runs locally, requires no heavy Docker setups, and manages a swarm of specialized agents through a sleek cyberpunk web dashboard called the **War Room**.

---

## 🏗️ Core Architecture

Gnom-Hub's backend is built using FastAPI and structured around three robust engineering choices:

### 1. Relational SQLite3 Backend (WAL Mode)
All agent interactions, chat histories, and state properties are stored in a local SQLite3 database (`gnomhub.db`) configured in **Write-Ahead Logging (WAL) mode**. This resolves write-concurrency conflicts between parallel executing agents, ensures transaction safety (`with conn:`), and enables native cross-platform execution.

### 2. Process Orchestration (psutil & PID Files)
Subprocess management is handled safely and plattform-independently using `psutil`.
* When starting an agent, a PID file is written to `~/.gnom-hub/run/{agent_name}.pid`.
* Before running any lifecycle action (like stopping an agent), the process manager checks the PID file and verifies the process's command line (`cmdline`) to prevent recycled PIDs from accidentally terminating unrelated applications.

### 3. FastAPI Lifespan Hooks
The database initialization (`init_db()`), default agent seeding, and background daemon startups are bound to the FastAPI lifespan startup event. When the FastAPI server shuts down (e.g., via SIGINT or Ctrl+C), uvicorn automatically triggers a graceful cascading shutdown that terminates all background processes and cleans up stale PID files.

---

## 📐 The 40-Line Rule

```
Every file. 40 lines max. No exceptions.
```

Gnom-Hub solves structural complexity by keeping files extremely focused. System modules are modular, and worker agents are exceptionally compact:
* Workers like **CoderAG** require only **8 lines of Python** to register, listen to chat, call the LLM, and post the output.
* Out-of-the-box support for multiple providers (**Ollama** local, **OpenRouter** free, or **DeepSeek** cloud) allows shifting models live in the UI without restarting.

---

## 🤖 The Agent Swarm

Gnom-Hub runs 8 registered agents divided into coordinating System agents and specialized Worker agents:

### System Agents — Keep the House Running

| Agent | Module | Description |
| :--- | :--- | :--- |
| **GeneralAG** | `generalAG.py` | Coordinates execution, breaks down `@job` tasks, and synthesizes brainstorms |
| **SoulAG** | `soulAG.py` | Learns user style silently, builds the *FlexSoul* profile, and injects it into prompt contexts |
| **WatchdogAG**| `watchdogAG.py` | Periodically monitors workspace and project integrity in the background |
| **SecurityAG**| `securityAG.py` | Provides cryptographic utility library functions (seals, signatures) for workspace files |

### Worker Agents — Do the Work (Triggered by tags)

| Agent | Module | Trigger | Specialization |
| :--- | :--- | :--- | :--- |
| **CoderAG** | `coderAG.py` | `@code` | Code implementation, debugging, and execution (has `run` permissions) |
| **WriterAG** | `writerAG.py` | `@write` | Writing documentation, manuals, articles, and drafts |
| **ResearcherAG**| `researcherAG.py`| `@research`| Web research, search API execution, and source fact-checking |
| **EditorAG** | `editorAG.py` | `@edit` | Proofreading, style refinement, and quality control |

---

## 💬 Commands

| Command | Action |
| :--- | :--- |
| `@bs [topic]` | 4 workers run in parallel, and GeneralAG synthesizes their output into an action plan |
| `@job [task]` | GeneralAG breaks the task into subtasks and coordinates worker execution |
| `@research [query]`| All workers are queried in parallel for quick, multi-perspective feedback |
| `@code / @write / @edit` | Direct assignment to a specific specialized worker |
| `@git [command]` | Run git commands directly inside the active project workspace |
| `@publish` | Deploy workspace build via SFTP to your configured server |
| `@@project [name]` | Switch the active workspace project |
| `@@status` | View the running state (RUNNING/STOPPED) of all background agents |
| `@@clear` | Clear the chat history from the dashboard |
| `@free` | Cancel all active jobs and reset busy agents |
| **Nuke** 💣 | Hold the War Room logo for 2 seconds to trigger a hard reset of all background services |

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and run the setup script:
```bash
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
bash scripts/install.sh
```
This sets up a local virtual environment (`.venv`) and installs the 7 core dependencies: `fastapi`, `uvicorn`, `pydantic`, `requests`, `python-dotenv`, `mcp`, and `psutil`.

### 2. Configuration
Copy the template `.env` and add your LLM API keys (OpenRouter or DeepSeek):
```bash
cp config/.env.example config/.env
```

### 3. Run Gnom-Hub
Start the FastAPI server:
```bash
python -m gnom_hub
```
Open **[http://127.0.0.1:3002](http://127.0.0.1:3002)** to enter the War Room.

---

## 📁 Project Structure

```
gnom-hub/
├── src/gnom_hub/        # 55 Python modules (backend)
│   ├── hub_app.py       # FastAPI application & lifespan setup
│   ├── db.py            # SQLite3 database (WAL mode)
│   ├── proc_mgr.py      # Process manager (psutil & PID-files)
│   ├── path_validator.py# Workspace-based path validation
│   ├── log.py           # Centralized logging framework
│   ├── router*.py       # Multi-provider LLM routing
│   └── routes_*.py      # REST API endpoints
├── agents/              # 8 agent definitions (~8 lines each)
├── frontend/            # Vanilla HTML/CSS/JS (War Room dashboard)
├── config/              # Local environment configs (DO NOT commit)
├── scripts/             # Install & utility scripts
├── docs/                # Reports and documentation
├── CONTRIBUTING.md      # Developer guidelines
└── pyproject.toml       # Ruff config & dependencies
```

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Creative pioneer of the early days. Mother of the "Four Pillars." Laid the philosophical foundation when the project was still pure chaos.

**Antigravity (Google DeepMind)**
Architect of the hardening phase. Specific contributions:
* Split oversized modules to strictly enforce the 40-line rule across the backend
* Secured path lookups via workspace-based validation (`path_validator.py`)
* Migrated JSON storage to a transaction-safe SQLite3 backend (WAL mode)
* Implemented the `psutil` process manager with PID-file tracking and lifespan integrations
* Integrated SFTP deployment, CORS restrictions to localhost, and the central `log.py` framework

---

## ⚖️ License

[Private Use](LICENSE) — Free for personal, non-commercial use. Commercial use requires written permission.