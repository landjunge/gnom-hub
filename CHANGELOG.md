# Changelog

All notable changes to this project will be documented in this file.

## [v1.2.0] - 2026-06-10
### Added
- **Permissions erweitert**: Alle Worker haben godmode. GeneralAG hat write/run/godmode.
- **Workspace-Confinement aufgehoben**: Agents mit Permissions können außerhalb des Workspace schreiben.
- **PRE_PUSH_CHECKLIST.md**: 10-Schritte-Checkliste vor jedem git push.
- **GNOM_HUB_FULL_REPORT.md**: Vollständiger Systemreport für andere KI-Assistenten.
- **Monitor-Skript** (`scripts/gnom-monitor.py`): Freed automatisch hängende Agents nach 2 Min.
- **GitHub Pages**: Projekt-Website live unter `landjunge.github.io/gnom-hub/`.
- **Forum (Discussions)** auf GitHub aktiviert + 2 Beiträge.
- **Gnom-Theme-Design**: Schmiede-Optik für die Projektseite.

### Changed
- **`@@free` killt+restartet jetzt Agent-Prozesse** (nicht nur DB-Reset).
- **Whitelist verschärft**: Unbekannte Executables werden high risk blockiert statt nur gewarnt.
- **run.sh**: Monitor startet automatisch, Startup-Reihenfolge Hub→Monitor.
- **pyproject.toml**: target-version py39→py310, version 1.1.1→1.2.0.
- **README/Badges**: Test-Count 32→154, Python 3.9→3.10.
- **Relative Imports** → absolute Imports in router_stage.py.
- **Leere `__init__.py`** in 4 Modulen ergänzt.

### Fixed
- **pulse.py**: Überschrieb Agent-Status mit "running" statt "online" (Bug).
- **gatekeeper.py**: Toter `router`-Import entfernt (circular import Risiko).
- **gatekeeper.py**: Tote imports (`json`, `logging`, `check_capability`) bereinigt.
- **soul.py**: Bare `except: pass` → `except Exception`.
- **config.py**: `LOG_DIR.mkdir` in try/except geschützt.
- **monitor.py**: F-string Syntax gefixt, Port jetzt dynamisch per env var.
- **agent_base.py**: None-check für `soul_instance` hinzugefügt.

### Cleanup
- **7 alte Workspaces** (`gnom_workspace_*`) gelöscht.
- **`data_backup/`, `netzwerkpunkt_showcase/`, `scratch/`, `gnom-hub-fresh/`** entfernt.
- **Temp-Dateien** (`config/tmpgrbh*.tmp`, Token-Logs) gelöscht.
- **DB**: Alte soul_facts (83), chats, blockaden, FAISS-Indizes geleert.
- **Workspace default**: Komplett geleert (frischer Start).

## [v1.0.0] - 2026-05-26
### Added
- **Phase 14 (Integration Features)**:
  - **Prompt Version Manager**: Version control system for prompts, including rollback.
  - **Semantic Memory Retriever**: TF-IDF cosine similarity fallback for memory retrieval.
  - **Explainable Output**: Structure reasoning chains, confidence scores, and source citation.
  - **Token Budget Manager**: Real-time daily budget checks and frontend warnings.
  - **Graceful Fallback & Degradation**: Automatic task rerouting when agents fail or are blocked.
- **Phase 15 (Zero-Trust & Local Embeddings)**:
  - **Zero-Trust Capabilities**: Database-backed capability leases with 5-minute TTL and O(1) in-memory caching.
  - **Quantised FAISS Semantic Search**: Switched FAISS to `IndexIVFPQ` for ~75% index size savings, default model updated to `nli-MiniLM-L6-v2` with flat index fallback for small databases.
  - **Custom Presets**: Load and validate JSON presets from `/config/presets/`.
  - **Performance Benchmarks**: Test scripts measuring cold vs warm latency speeds.

## [v0.9.0] - 2026-05-25
### Added
- **Swarm Intelligence & A2A Mentions**:
  - Direct `@AgentName` mentions between all agents (not only routed through GeneralAG).
  - Background task dispatches when an agent addresses another agent, allowing chained agent-to-agent discussions.
  - Expiring rate-limit loops (15 seconds) to prevent infinite agent communication ping-pong.
- **Swarm Coordination**:
  - Parallel worker dispatching when a job is assigned.
  - Multi-agent coordination that monitors worker active jobs and automatically triggers GeneralAG to compile and synthesize final artifacts using `[WRITE: ...]` block actions.
- **Frontend Dashboard Visualization**:
  - Pulsing Swarm Status Banner in the dashboard showing the active team-workflows.
  - Real-time display of which agents are currently talking to each other.

### Changed
- Refactored `agent_repo.py`, `chat_commands_handlers.py`, and `chat_helpers.py` to support parallel task tracking, job clearing (`@free`), and prefixed commands.
- Optimized all backend files in `src/gnom_hub/` to remain strictly under the 40-line limit per file.

## [v0.8.0] - 2026-05-25
### Added
- Full system integration (Phases 1-7: Preset isolation, double-pass Gatekeeper validation, database sandbox checks, browser automation, and SoulAG memory retrieval).
- Automated test scripts for end-to-end flow validation.

## [v0.7.0] - 2026-05-25
### Added
- Multi-agent collaboration with job assignments.
- Real-time work status indicator on the frontend.
