# 🧠 GNOM-HUB

> **8 Agents. ~7500 Lines. 176 Modules. Zero tolerance for bloat.**
> *A local-first multi-agent orchestration playground with a defensive zero-trust architecture and a modularized War Room dashboard.*

[![License](https://img.shields.io/badge/License-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agents-8-blueviolet.svg)](#)
[![Lines of Code](https://img.shields.io/badge/Lines_of_Code-~7500-blue.svg)](#)
[![Modules](https://img.shields.io/badge/Modules-176-blue.svg)](#)
[![40-Lines-Rule Compliance](https://img.shields.io/badge/40--Lines--Rule-~80%25_compliant-orange.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

---

🇬🇧 **English (README.md)** • 🇩🇪 **[Deutsch (README.de.md)](README.de.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Overview" width="100%">

---

## What is Gnom-Hub?

Gnom-Hub is a local-first multi-agent system with a clear structure: **176 Python modules — over 80% of which are strictly shorter than 40 lines**. It offers a lightweight, high-performance orchestrator without heavy frameworks, running entirely locally on your Mac. It controls background agents through a web dashboard called the **War Room**.

> [!IMPORTANT]
> **Conscious Minimalism:** Gnom-Hub is designed for simplicity and maximum performance. It is intentionally **not** built to control hundreds of agents, but to efficiently orchestrate a small, highly specialized, and transparent team.

---

## 🚀 Key Features

Gnom-Hub combines robust multi-process orchestration with an interactive web interface. Key features include:

*   **Intelligent & Flexible Agent Routing**:
    The central LLM router dynamically routes queries to the most suitable model (e.g., DeepSeek-Reasoner, Claude, GPT). In case of API outages or network limits, it falls back transparently to configured local models (like offline Llama via Ollama) to keep the swarm moving.
*   **Layer-Based Visual Showbox System**:
    The dashboard's Showbox displays work results, text drafts, and UI mockups in real-time across interactive layers. Each layer has a distinct color code and triggers a temporary flash effect (highlighting borders) on the corresponding agent group (Worker sidebar or System top-bar) upon switching, providing immediate visual feedback on the source of the data.
*   **Fully Modularized Frontend**:
    The glassmorphic web dashboard has been refactored from a massive monolithic file into 7 specialized JavaScript modules. This guarantees a clean separation of concerns (decoupling core.js, chat.js, workspace.js, system_dashboard.js, worker_dashboard.js, worker_sidebar.js, dashboard.js) and simplifies codebase maintenance.
*   **Shared Semantic Long-Term Memory**:
    All agents share a persistent SQLite database. SoulAG monitors chats, extracts relevant facts, and dynamically injects the top 8 most relevant entries into worker prompts via FAISS semantic search (falling back to TF-IDF cosine-similarity math if libraries are missing) to prevent repetitive mistakes.
*   **Structured Brainstorming Mode (`@bs`)**:
    The `@bs [topic]` command triggers a coordinated swarm debate. All worker agents analyze the problem in parallel brainstorm states, while GeneralAG consolidates and filters the answers into a single, structured action plan.
*   **Bento-Grid Live Status Dashboard**:
    Provides real-time visibility into swarm health. The glassmorphic Bento-Grid displays active daemon statuses (heartbeats polled via `/api/metrics`), latency charts, token expenditure, and incorporates an interactive user feedback panel.

---

## 🎯 Philosophy

- **Local-First**: Everything runs locally. No cloud orchestration.
- **Fixed Topology**: Exactly 8 defined agents (4 system + 4 worker agents) — no uncontrolled agent explosion.
- **Defensive Architecture**: Clean Architecture + a target limit of 40 lines per module.
- **Pragmatism**: No autonomous infinite loops. Humans retain ultimate control.
- **Security by Design**: System agents monitor and protect, workers operate with restricted capabilities.

---

## ✅ Completed Milestones

Gnom-Hub development phases:

*   **🛡️ Phase 1: Security & Gatekeeper**
    *   Double approval (`WatchdogAG` + `SecurityAG`) for all writes/commands.
    *   Strict path restrictions on core system files.
*   **📊 Phase 2: Observability & Health**
    *   Structured JSON auditing of system events in SQLite.
    *   Bento Grid dashboard for real-time status and health.
*   **🧠 Phase 3 & 6: Memory & Retrieval**
    *   Intelligent fact retrieval (keys weighted 2x vs values).
    *   Dynamic context injection of top 8 relevant facts.
*   **🔄 Phase 4: Recovery & Cleanup**
    *   API failover/rotation and local Ollama model fallbacks.
    *   Auto-deletes old chat histories (>7d) and facts (>30d).
*   **🌐 Phase 5: Browser Sandbox**
    *   Playwright browser automation runs inside isolated Docker container.
    *   Zero-network access by default (offline), Whitelisting-controlled.
*   **🔄 Phase 7 & 8: Collaboration & Hardening**
    *   Task delegation via `@AgentName -> task` mentions.
    *   Simultaneous stress testing & packaging.
*   **🔗 Phase 9 & 10: Swarm Intelligence & Git**
    *   Agent-to-agent direct communications.
    *   Automated Git commits after successful swarm tasks.
*   **🧠 Phase 11-13: Continuous Learning & Feedback**
    *   GeneralAG reviews jobs to inject self-improvement rules (`evolution_*`).
    *   User feedback panel (thumbs up/down) directly shapes agent behaviors.
*   **⚡ Phase 14: Versioning & Graceful Degradation**
    *   Prompt Version Manager with rollbacks for prompt evolution.
    *   Active fallback routing when workers are offline/blocked.
*   **🛡️ Phase 15: Zero-Trust Capabilities & FAISS**
    *   Local FAISS semantic vector search (`sentence-transformers`).
    *   In-memory Capability Leases (TTL cache) to bypass redundant security checks.
*   **🛡️ Phase 16: System Hardening & Guarding**
    *   GeneralAG blocked from writing files/running commands.
    *   Strict 4/4 agent limit and LLM console performance tuning (`Promise.all`).
    *   Automated PyPI API validation and DS-R1 `<think>` block filtering.
*   **🔄 Phase 17: Stability & Loop Prevention**
    *   Cascading mentions restricted to max depth of 3.
    *   `pulse_janitor` automatically resets hanging "busy" agents after 5 mins.
    *   Preset switching wrapped in atomic SQLite transactions.
*   **🎨 Phase 18: Sidebar & Header Layout**
    *   Moved global stats to sidebar with a clean thin font.
    *   Flanked sidebar stats with two fixed 30px placeholders.
    *   Clean logo in left header, uniform 86px buttons in right header.
*   **💾 Phase 19: Global Actions & Clean UI**
    *   Added standard-sized (86px) Back and Save buttons to positions 1 and 6 in the header navigation.
    *   Removed all redundant local "Speichern" / "Apply & Save" buttons.

---

## 📐 The 40-Line Rule

Gnom-Hub keeps structural complexity low by keeping code focused.
*   **Objective**: Originally, all Python files under `src/gnom_hub/` were targeted to be under 40 lines.
*   **Current Compliance**: Over 80% of our 176 Python modules strictly respect this limit. To maintain readability for complex features (e.g., SQLite WAL operations in `db.py`, security audits in `gatekeeper.py`, and multi-tier routing in `router_stage.py`), 35 files have been allowed to grow.
*   **Worker Simplicity**: Background workers remain extremely compact (e.g., CoderAG requires only ~10 lines of code to handle polling, processing, and executing actions).

---

## 🤖 Swarm Topology

All agent configurations, system prompts, and permissions are configured centrally in [agent_definitions.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/agents/agent_definitions.py).

### System Agents (Administrative Permissions)
*   **SoulAG**: Central consciousness and memory. Learns preferences and injects facts.
*   **GeneralAG**: Coordinator and orchestrator. Splits `@job` inputs and delegates tasks.
*   **WatchdogAG**: Monitors codebase rules (40-line compliance), protected system paths, and workspace integrity.
*   **SecurityAG**: Scans code modifications and shell commands for vulnerabilities, malware, or unsafe constructs.

### Worker Agents (Restricted Workspace Permissions)
*   **CoderAG**: Software development and debugging. Has `godmode` for Playwright browser automation and shell execution.
*   **ResearcherAG**: Gathers facts, parses documentations, and executes web search requests.
*   **WriterAG**: Drafts manuals, Handbooks, reports, and article texts.
*   **EditorAG**: Performs proofreading, styling, code refactoring, and quality assurance.

---

## 🛠️ Agent Actions & Tools

Gnom-Hub background agents interact with the system, filesystem, and external APIs by generating specific markdown-like tags in their LLM output. These tags are parsed and executed as secure tools.

> [!TIP]
> **Action Sandbox & Validation:** Every action generated by a worker is intercepted and must pass through double-approval gates (WatchdogAG & SecurityAG) before execution.

| Action / Tag | Description | Restricted to | Example |
| :--- | :--- | :--- | :--- |
| **`[READ: filename]`** | Reads the contents of a file. | All Worker Agents | `[READ: index.html]` |
| **`[WRITE: filename]content[/WRITE]`** | Creates or overwrites a file in the workspace. | CoderAG, WriterAG, EditorAG, ResearcherAG | `[WRITE: hello.py]`<br>`print("Hello")`<br>`[/WRITE]` |
| **`[SHELL: command]`** | Runs terminal commands (like testing or package installation). | CoderAG (`run` cap) | `[SHELL: pytest tests/]` |
| **`[IMAGE: prompt]`** | Generates an image using AI and saves it to the workspace. | WriterAG, CoderAG | `[IMAGE: futuristic dashboard logo]` |
| **`[BROWSER: action_json]`** | Controls a real Playwright browser (visits sites, clicks, types, reads). | CoderAG (`godmode` cap) | `[BROWSER: {"action": "goto", "target": "https://example.com"}]` |
| **`<SHOWBOX:index>html_or_json</SHOWBOX>`** | Renders HTML presentations or UI mockups directly in the War Room. | All Agents | `<SHOWBOX:4>`<br>`<h3>Slide Content</h3>`<br>`</SHOWBOX>` |

---

## 💬 Commands

| Command | Action |
| :--- | :--- |
| `@bs [topic]` | Triggers a parallel brainstorm among workers; GeneralAG consolidates results |
| `@job [task]` | GeneralAG breaks down the task and coordinates the step-by-step execution |
| `@code / @write / @edit` | Direct assignment to a specific worker specialist |
| `@git [command]` | Executes git operations inside the local workspace |
| `@@project [name]` | Switches the active workspace project |
| `@@status` | Displays the active status (RUNNING/STOPPED) of all agent daemons |
| `@@clear` | Clears the chat timeline |
| `@free` | Resets all active background jobs and paused statuses |
| **Nuke** 💣 | Press and hold the War Room logo in the UI for 2 seconds to force-restart all services |

---

## 🚀 Quick Start

1. **Clone & Setup**:
   ```bash
   git clone https://github.com/landjunge/gnom-hub.git
   cd gnom-hub
   bash scripts/install.sh
   ```
2. **Configure Environment**:
   Copy `config/.env.example` to `config/.env` and add your LLM API keys (OpenRouter, DeepSeek, or configure local Ollama).
3. **Run Server**:
   ```bash
   ./run.sh
   ```
4. **Access Web Panel**:
   Open **[http://127.0.0.1:3002](http://127.0.0.1:3002)** in your browser to enter the War Room.

---

## 📁 Project Structure

```text
gnom-hub/
├── src/gnom_hub/        # 176 Python modules (Backend)
│   ├── core/            # Global configuration, logger, and Gatekeeper security
│   │   └── security/    # Path validation (path_validator.py) & Gatekeeper (gatekeeper.py)
│   ├── db/              # SQLite3 database (WAL mode) & repositories (legacy_db.py)
│   ├── memory/          # Local FAISS semantic search & embeddings
│   ├── soul/            # Steganographic memory (ZWC encryption)
│   ├── agents/          # BaseAgent, agent_definitions.py, and tools
│   │   ├── actions/     # Action dispatcher (action_handlers.py) for [WRITE:], [SHELL:], [BROWSER:]
│   │   ├── swarm/       # Multi-agent coordination & A2A swarm communications
│   │   └── explainability/ # Structured reasoning chain (<think> filtering)
│   ├── chat/            # Chat services, system commands & brainstorming
│   ├── api/             # FastAPI app.py, router & API endpoints (endpoints/)
│   ├── infrastructure/  # Process management (psutil_mgr.py), LLM routing, and pulse heartbeat
│   └── frontend/        # Bento-Grid War Room dashboard (HTML, CSS & 7 JS modules)
├── agents/              # Startup scripts for the 8 background agents
├── config/              # Local setups, presets, and token configurations
├── scripts/             # Local installer and shortcut setups
├── docs/                # Architecture sheets and project documentation
├── pyproject.toml       # Ruff configs & dependencies
```

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Creative pioneer and founder. Designed the agent topologies and laid the philosophical foundation of Gnom-Hub.

**Antigravity (Google DeepMind)**
Architect of the hardening phase. Key contributions:
* Refactored and modularized codebase files to respect the backend 40-line rule.
* Secured path traversal risks with dedicated workspace validations ([path_validator.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/core/security/path_validator.py)).
* Migrated JSON storage layers into a transaction-safe local SQLite3 database (WAL mode).
* Implemented the `psutil` process manager with PID files and Lifespan hooks.
* Added SFTP deployments, CORS protections, and custom presets support.
* Implemented Phase 1-16 hardening tasks (Zero-Trust Leases, local FAISS embeddings, prompt version manager, user feedback loop, R1 think blocks filter, and strict 4/4 agent limits).
* Modularized the monolithic web dashboard script into 7 decoupled static JS modules to enforce proper separation of concerns.
* Optimized LLM console dashboard loading latencies by parallelizing backend requests and caching model lookups.

---

## ⚖️ License

[Private Use](LICENSE) — Free for personal, non-commercial research and development. Commercial usage requires written authorization.