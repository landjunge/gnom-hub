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

Gnom-Hub has been developed through a structured hardening process:

### 🛡️ Phase 1: Security & Gatekeeper
*   **Double Approval**: Every file write and command execution by worker agents requires an explicit `APPROVED` from `WatchdogAG` (code integrity & 40-line rule) **and** `SecurityAG` (malware & pattern scans).
*   **Protected System Files**: Core system files (`index.html`, `run.sh`, `.env`, `src/gnom_hub/*`, `config/*`) are strictly off-limits for worker agents.
*   **Escalation Routing**: Ambiguous security scans trigger a manual approval prompt in the dashboard for the user.

### 📊 Phase 2: Observability & Health Dashboard
*   **Structured Auditing**: Every system event and LLM call (latency, tokens, cost) is logged as JSON in an indexed SQLite `audit_log` table.
*   **Health Bento Grid**: A real-time, glassmorphic status grid in the dashboard displays agent health (Green = Alive, Yellow = Heartbeat delay, Red = Offline) along with performance metrics.

### 🧠 Phase 3 & 6: SoulAG Memory & Context Injection
*   **Semantic & Jaccard Retrieval**: Replaced static history limits with an intelligent retrieval system. It weights matching keys twice as high as values.
*   **Dynamic Prompt Injection**: Prior to worker executions, the top 8 most relevant facts from the SQLite memory are automatically injected into the agent system prompt.

### 🔄 Phase 4: Error Recovery & DB Cleanup
*   **Failover & Rotation**: Auto-rotation of LLM keys and graceful degradation fallback to local/alternative models (e.g., offline Llama via Ollama).
*   **Automated Maintenance**: Auto-deletes old chat histories (>7 days) and expired facts (>30 days) while preserving critical settings and rules.

### 🌐 Phase 5: Browser Automation (Playwright Sandbox)
*   **Isolate & Sandboxing**: Workers execute web browser actions inside an isolated Docker container.
*   **Zero-Network by Default**: The container runs offline (`--network=none`) and only switches to bridged network access if the target URL is explicitly whitelisted in `approved_external_urls`.

### 🔄 Phase 7 & 8: Collaboration & Full Swarm Hardening
*   **@mentions Support**: GeneralAG coordinates worker agents using `@AgentName -> task` syntax.
*   **E2E Validation**: Completed end-to-end stress-testing of all features simultaneously (preset switching, capability caching, sandbox operations).

### 🔗 Phase 9 & 10: Swarm Intelligence & A2A Communication
*   **Agent-to-Agent Chats**: Agents can directly address each other via `@mentions` to solve multi-step problems asynchronously.
*   **Git Automation**: Automatically stages and commits workspace changes after successful swarm tasks.

### 🧠 Phase 11, 12 & 13: Continuous Learning & Feedback
*   **Agent Evolution**: GeneralAG reviews job histories to dynamically append self-improvement rules (stored as `evolution_{agent}_{hex}`) to worker prompts.
*   **User Feedback Loop**: Prompts the user to rate jobs via the dashboard panel, modifying agent behaviors based on user ratings and comments.

### ⚡ Phase 14: Version Control & Graceful Degradation
*   **Prompt Version Manager**: Automatic versioning of agent system prompts during evolution, tracking scores and supporting rollbacks if degradation is detected.
*   **Active Fallback Routing**: Reroutes blocked or offline worker tasks dynamically to alternative agents to prevent workflow stalls.

### 🛡️ Phase 15: Zero-Trust Capabilities & FAISS Embeddings
*   **Capability Leases**: An in-memory cache system (TTL-based) that bypasses repeated LLM verification checks for verified files, commands, or browser actions.
*   **Local FAISS Indexing**: Local semantic similarity search using `sentence-transformers` and `faiss-cpu`, falling back to TF-IDF cosine matching if libraries are missing.
*   **Custom Presets**: Dynamically loads custom workspace presets from JSON files in `config/presets/`.

### 🛡️ Phase 16: System Hardening, SoulAG Precision & Guard Autonomy
*   **GeneralAG Orchestration Guard**: Strictly restricts GeneralAG to coordination, completely blocking it from executing shell commands or direct file writes.
*   **Over-Association Prevention**: Implements query length guards and value-only embeddings to stop unrelated facts from injecting on short inputs (like "test" or "neu").
*   **Automated Gatekeeper Approvals**: Automatically approves safe writes within the workspace and whitelisted shell commands (`python3`, `pytest`, `git status`) to speed up execution.
*   **Dynamic PyPI Verification**: Performs real-time validation checks against the PyPI JSON API during package installations to check package legitimacy and active vulnerabilities.
*   **Reasoning Block Filtering**: Automatically strips DeepSeek R1 `<think>...</think>` blocks from machine-parsed outputs to prevent gatekeeper bypasses while keeping the styled details widget in the chat UI.

---

## 📐 The 40-Line Rule

Gnom-Hub keeps structural complexity low by keeping code focused.
*   **Objective**: Originally, all Python files under `src/gnom_hub/` were targeted to be under 40 lines.
*   **Current Compliance**: Over 80% of our 176 Python modules strictly respect this limit. To maintain readability for complex features (e.g., SQLite WAL operations in `db.py`, security audits in `gatekeeper.py`, and multi-tier routing in `router_stage.py`), 35 files have been allowed to grow.
*   **Worker Simplicity**: Background workers remain extremely compact (e.g., CoderAG requires only ~10 lines of code to handle polling, processing, and executing actions).

---

## 🤖 Swarm Topology

All agent configurations, system prompts, and permissions are configured centrally in [agent_definitions.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/agent_definitions.py).

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
├── src/gnom_hub/        # 174 Python modules (Backend)
│   ├── hub_app.py       # FastAPI application and startup hooks
│   ├── db/              # SQLite3 database WAL layers & schemas
│   ├── proc_mgr.py      # Process daemon controller (psutil PIDs)
│   ├── path_validator.py# Path traversal prevention sandboxing
│   ├── log.py           # Structured logger configuration
│   ├── router/          # Multi-tier routing & model selection
│   ├── frontend/        # Glassmorphic dashboard (HTML, CSS, modularized JS scripts)
│   └── routes_*.py      # REST endpoints for chat, metrics, and memory
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
* Secured path traversal risks with dedicated workspace validations (`path_validator.py`).
* Migrated JSON storage layers into a transaction-safe local SQLite3 database (WAL mode).
* Implemented the `psutil` process manager with PID files and Lifespan hooks.
* Added SFTP deployments, CORS protections, and custom presets support.
* Implemented Phase 1-16 hardening tasks (Zero-Trust Leases, local FAISS embeddings, prompt version manager, user feedback loop, and R1 think blocks filter).
* Modularized the monolithic web dashboard script into 7 decoupled static JS modules to enforce proper separation of concerns.

---

## ⚖️ License

[Private Use](LICENSE) — Free for personal, non-commercial research and development. Commercial usage requires written authorization.