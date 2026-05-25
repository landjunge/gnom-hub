# 🧠 GNOM-HUB — Clean Architecture Edition

A clean, modular multi-agent platform designed on top of robust Clean Architecture principles, featuring a radical constraint: **every backend module is capped at a maximum of 40 lines** (the 40-Line Rule).

> 🇩🇪 **Lies dies auf [Deutsch (README.de.md)](README.de.md)**

---

## 🚀 New Features

### 1. Centralized Swarm Registry (`agent_definitions.py`)
Gnom-Hub now manages a specialized swarm of **8 agents (4 system coordinators + 4 worker specialists)** defined entirely in a single source of truth: `src/gnom_hub/agent_definitions.py`. 
- **System Agents**: `SoulAG` (memory), `GeneralAG` (coordinator), `WatchdogAG` (workspace integrity), and `SecurityAG` (file signing).
- **Worker Agents**: `CoderAG` (programming), `ResearcherAG` (crawling/docs), `WriterAG` (drafting), and `EditorAG` (polishing).

### 2. Workflow Preset System
Directly below the Showbox in the left sidebar, the UI features a drop-down selector containing **6 workflow modes**:
1. 💻 **Web Development**: Focuses on modern semantic HTML5, CSS, vanilla JS, responsiveness, and performance.
2. 🎨 **Graphic Design**: Focuses on SVGs, styling contrast, typography, color palettes, and UI/UX layout.
3. 🎵 **Audio Production**: Focuses on the Web Audio API, synthesis, sound design, and DSP coding.
4. 🎬 **Video Production**: Focuses on canvas rendering, requestAnimationFrame loops, and video concepts.
5. ✍️ **Marketing & Copy**: Focuses on copywriting frameworks (AIDA), SEO, and conversion-optimized hooks.
6. 🔍 **Research & Analysis**: Focuses on facts verification, source citation, literature reviews, and python data processing.

### 3. Swarm Memory & Focus Configuration
- **Swarm Memory (SoulAG)**: Acts as the background consciousness, silently listening to user chat messages, extracting preferences, facts, and rules, and saving them to the swarm facts memory so they are dynamically appended to agents' prompts.
- **Dynamic Configuration (SoulAG-Free Presets)**: Switching a preset dynamically instructs the router to load prompt modifiers (specific to that agent and preset) and adjust default LLM models. This keeps the presets simple, stable, and decoupled from the memory extractor.

### 4. Role-Based Secure Tool Permissions
Agent tool accessibility and execution permissions are fully role-based and governed dynamically using the central `agent_definitions.py`:
- **System Agents** (`SoulAG`, `GeneralAG`, `WatchdogAG`, `SecurityAG`) get full permissions: `["read", "write", "run", "godmode", "crawl", "desktop", "evolve"]`.
- **Worker Agents** (`ResearcherAG`, `WriterAG`, `EditorAG`) get restricted permissions: `["read", "write", "@job"]`.
- **Specialist Coder** (`CoderAG`) gets `["read", "write", "@job", "godmode"]` (godmode dynamically maps to `run` for sandboxed terminal command execution and Playwright `browser` automation).
- All permissions are loaded and verified on-the-fly inside the action execution layer (`action_handlers.py`), keeping the architecture clean and secure.

---

## 📖 Preset Quick Guide

### How to Switch Presets
1. Open the Gnom-Hub dashboard.
2. Go to the sidebar and locate the drop-down selector below the Showbox.
3. Select your desired preset (e.g. *Web Development*).
4. The system will alert you in the chat about the new swarm focus, and the Showbox will overlay with the focus description.
5. Worker prompts are immediately updated with customized directives.

### Assigning Custom LLM Settings to a Preset
If you change models or providers in the LLM Settings menu (e.g., setting `CoderAG` to use a custom model or local instance) and click **"Save" / "Speichern"**, Gnom-Hub automatically:
- Assigns those custom settings to the currently active preset.
- Persists them to the state database.
- Automatically restores your custom setup whenever you switch back to this preset!

---

## ✨ Core Features
- **Strict Clean Architecture**: Decoupled layers (Domain, Infrastructure, Presentation, Application).
- **40-Line Rule**: Backend Python files in `src/gnom_hub/` stay strictly $\le 40$ lines.
- **Full Dependency Injection**: Clean inversion of control.
- **SQLite with WAL-Mode**: Lock-free concurrent database transactions.
- **Multi-Provider LLM Router**: Seamless fallback between local Ollama instances and OpenRouter/DeepSeek.

---

## 🚀 Quick Start

Ensure you have your environment variables set up in `config/.env` (e.g., OpenRouter or DeepSeek keys), then run:
```bash
chmod +x run.sh
./run.sh
```
Betreten Sie das Dashboard unter **[http://127.0.0.1:3002](http://127.0.0.1:3002)**.

---
**Version:** Clean Architecture Refactoring (May 2026)  
*Gnom-Hub: Zero tolerance for bloat, maximum specialized efficiency.*