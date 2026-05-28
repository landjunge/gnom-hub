# 🧠 GNOM-HUB

> **8 Agents. ~7500 Lines. 176 Modules. Zero tolerance for bloat.**

[![License](https://img.shields.io/badge/License-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agents-8-blueviolet.svg)](#)
[![Lines of Code](https://img.shields.io/badge/Lines_of_Code-~7500-blue.svg)](#)
[![Modules](https://img.shields.io/badge/Modules-176-blue.svg)](#)
[![40-Lines-Rule Compliance](https://img.shields.io/badge/40--Lines--Rule-~80%25_compliant-orange.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

> 🇩🇪 **Lies dies auf [Deutsch (README.de.md)](README.de.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Overview" width="100%">

---

## What is Gnom-Hub?

Gnom-Hub is a local-first multi-agent system with a clear structure: **176 Python modules — over 80% of which are strictly shorter than 40 lines**. It offers a lightweight, high-performance orchestrator without heavy frameworks, running entirely locally on your Mac. It controls background agents through a web dashboard called the **War Room**.

> [!IMPORTANT]
> **Conscious Minimalism:** Gnom-Hub is designed for simplicity and maximum performance. It is intentionally **not** built to control hundreds of agents, but to efficiently orchestrate a small, highly specialized, and transparent team.

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

## 📐 Code Structure & Readability

Gnom-Hub keeps structural complexity low by keeping code focused and modular.
*   **File Size**: We aim to keep files small and cohesive where it makes sense.
*   **Readability First**: If splitting a file would decrease clarity or readability, we keep the logic within a single file. Thus, files are allowed to be significantly longer than 40 lines.
*   **Top Priority**: Clean, maintainable code is our highest priority, rather than adhering to an arbitrary line count limit.

---

## 🤖 Swarm Topology

All agent configurations, system prompts, and permissions are configured centrally in [agent_definitions.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/agent_definitions.py).

### System Agents (Administrative Permissions)
*   **SoulAG**: Central consciousness and memory. Learns preferences and injects facts.
*   **GeneralAG**: Coordinator and orchestrator. Splits `@job` inputs and delegates tasks.
*   **WatchdogAG**: Monitors codebase rules (40-line compliance) and path integrity.
*   **SecurityAG**: Scans code modifications and shell commands for vulnerabilities.

### Worker Agents (Restricted Workspace Permissions)
*   **CoderAG**: Software development and debugging. Has `godmode` for Playwright browser automation and shell execution.
*   **ResearcherAG**: Gathers facts, parses documentations, and executes web search requests.
*   **WriterAG**: Drafts manuals, Handbooks, reports, and article texts.
*   **EditorAG**: Performs proofreading, styling, code refactoring, and quality assurance.

---

## 📁 Project Structure

```text
gnom-hub/
├── agents/             # Minimalist startup scripts for the 8 background agents
├── config/             # Configuration files (.env, presets, token budgets)
├── data/               # Local FAISS indices, vector database, and cache
├── docs/               # Technical reports and developer documentation
├── gnom_workspace/     # The working directory where worker agents operate
├── logs/               # Log files of background processes and the server
├── scratch/            # Test scripts, demos, and temporary scripts
├── scripts/            # Installation and setup scripts
├── src/                # Source code package
│   └── gnom_hub/       # Core package of Gnom-Hub with 9 functional modules:
│       ├── agents/     # BaseAgent, actions handling, swarm coordination
│       ├── api/        # FastAPI server, routers, and endpoints
│       ├── chat/       # Chat services and brainstorming
│       ├── core/       # Global configuration, logging, security gatekeeper
│       ├── db/         # SQLite database interface and schema
│       ├── frontend/   # Visual Bento-Grid dashboard (War Room index.html, JS, CSS)
│       ├── infrastructure/ # Heartbeat (Pulse), Playwright sandbox, LLM routing
│       ├── memory/     # Local FAISS indexing and semantic search
│       └── soul/       # Steganographic ZWC memory (Zero-Width Characters)
├── gnomhub.db          # Inactive 0-byte SQLite file (live DB is under ~/.gnom-hub/)
├── pyproject.toml      # Package configuration and Python dependencies
└── run.sh              # Startup script for server and background agents
```

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
**Project Status:** May 2026 — Experimental, functional prototype for research and development.