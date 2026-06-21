# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- **Presets-Management: Schema v2 + Per-Agent-UI + Layer-A CRUD API**
  (Commits `659a663` + `256296a`). Layer-A-Schema (`presets.json`) erweitert
  von 4 Worker-Agents auf alle 8 (4 System + 4 Worker) mit per-Agent-Feldern
  (`prompt`/`focus`/`target`/`creativity`/`obedience`/`model_override`/
  `enabled`). Schema-Marker (`_schema_version=1`, `_schema_generation=1`,
  `_deprecation_notice`) detektieren Migrationen; alte Top-Level-Keys
  (`prompts`/`focus`/`targets`) bleiben als Layer-A-Fallback erhalten.
  Service-Layer (`preset_service.py`) hat neue Methoden `get_agent_groups`,
  `list_presets`, `get_preset`, `get_preset_agent`, `update_preset_agent`,
  `create_preset`, `clone_preset`, `delete_preset`. API: 7 neue
  Layer-A-Endpoints (`/api/presets/groups`, `/layer-a/list`,
  `/layer-a/{slug}`, `/layer-a/{slug}/agents/{name}` PUT, `/layer-a` POST,
  `/layer-a/{slug}/clone`, `/layer-a/{slug}` DELETE). Frontend: neuer
  "Presets"-Button in Top-Bar, Modal mit System/Worker-Sub-Tabs,
  Per-Agent-Cards mit Save-on-change. Neue Datei
  `src/gnom_hub/frontend/presets_management.js` (329 Zeilen).
  Doku: `docs/presets-management/schema-migration.md`.
- **MiniMax als multimodaler Single-Key**: MiniMax-Caps in
  `infrastructure/llm/providers.py` und `core/provider_registry.py` (beide
  Einträge) auf `["text", "vision", "image", "audio", "video", "music",
  "tools"]` erweitert. Ein einziger `sk-cp-…`-Key deckt jetzt alle
  Feature-Kategorien ab und erscheint in der LLM-Config-UI sowohl im
  Agent-Provider-Dropdown als auch in den Web-Search- und TTS-Karten.
- **TTS Provider-Dispatch**: `core/utils/audio_tts.py` liest die aktive
  TTS-Konfiguration aus `llm_service_tts` und routet entsprechend —
  MiniMax → `api.minimax.io/v1/audio/speech` (OpenAI-kompatibel),
  OpenAI-TTS → `api.openai.com/v1/audio/speech`, alles andere → ElevenLabs.
  Cache ist jetzt provider-scoped, damit Anbieter sich nicht in die Quere
  kommen. Bei jedem Backend-Fehlschlag: Fallback auf ElevenLabs, dann Web
  Speech.
- **LLM-Config UI: Web Search & TTS**: New side-by-side cards on the LLM
  configuration page (`showLLMConfig()`) for Web Search and TTS providers —
  each with provider/model/API-key inputs and a coloured status badge
  (`✓ key loaded` / `⏳ key not tested` / `✗ no key`). 12 web-search providers
  (Brave, Tavily, Serper, Bing, DuckDuckGo, …) and 10 TTS providers
  (ElevenLabs, OpenAI-TTS, Edge-TTS, …) selectable.
- **Erweiterte Provider-Liste**: New canonical registry
  `src/gnom_hub/core/provider_registry.py` with 44 distinct providers across
  `chat` / `web_search` / `tts` / `image` / `embedding` / `vision` capabilities,
  consumed by the smart router and the key verifier. Plus 16 new stubs in
  `infrastructure/llm/providers.py` for previously missing providers.
- **Global Save erweitert**: Single header Save button (`#btn-save` in
  `core.js`/`globalSave()`) now flushes pending LLM-page changes, agent
  routing + agent-tuning settings, then triggers a non-destructive backup via
  the new `POST /api/admin/backup` endpoint. Per-row Save buttons in the agent
  table and the in-modal memory "Speichern" button were removed (memory edits
  now autosave on blur). Pending-changes tracker drives a pulsing orange
  border on the header button.
- **Backend Endpoints**: New routes
  `GET /api/llm/providers` (full provider catalogue with `category`/`caps`/
  `default_model`), `GET /api/llm/service` + `POST /api/llm/service`
  (service config read/write), and `POST /api/admin/backup` (non-destructive
  backup invocation). All backed by 14 fast pytest tests
  (`tests/test_frontend_llm_providers.py`).

### Changed
- **Agent sys_prompts an User-Spec angepasst** (`src/gnom_hub/agents/agent_definitions.py`):
  SoulAG koordiniert jetzt explizit das Security-Tribunal (Analyse, Empfehlung an
  User via Showbox, Entscheidung bleibt beim User). GeneralAG trägt jetzt
  Git-Management + Worker-Performance-Tracking als dokumentierte Rollen (delegiert
  Commits an CoderAG, nutzt `coordination.db`/`find_best_agent_for_task()` für
  Worker-Auswahl). WatchdogAG ist strikter gefasst: prüft Workspace-Pfade,
  kompromisslose Blockade von System-Pfaden (`src/gnom_hub/`, `config/`, `.env`,
  …), `darf nichts freigeben` (Approve bleibt User/SecurityAG-override). SecurityAG
  ist jetzt Ressourcen-/Rechte-Manager mit Whitelist- und LLM-Routing-Verantwortung
  als Hauptrollen; die System-Operator/godmode-Fähigkeiten bleiben als sekundäres
  Sicherheitsnetz. **Keine Code-Logik geändert** — nur Prompt-Verhalten.
- **SmartRouter.get_best_model**: Replaced hardcoded lists containing dead
  model names (`claude-3-5-sonnet-20241022`, `poolside/laguna-xs.2:free`,
  `nemotron-3-nano-omni-30b-a3b-reasoning`, `deepseek-v4-flash`) with a
  `_STAGE_PREFERRED` dict of currently-shipped IDs; added Ollama
  (`qwen2.5-coder:7b`) fallback when nothing else matches.
- **`_try_keys` rotates on 429/401/5xx**: Previously a single 429 silently
  killed the call; `_RetryableCallError` is now raised so the key rotation
  advances to the next key in the pool.
- **Role-keyword matching**: Fragile `poolside / laguna / llama / nemotron /
  glm / liquid` substring matching replaced by a small `_ROLE_KEYWORDS` map
  (`coder → qwen/coder/codestral`, `reasoning → o1/deepseek-r1`,
  `chat → gpt/llama/mistral`, `vision → claude/gpt-4o/gemini`, …).
- **Frontend provider detection**: Hardcoded `pvdOf()` ladder replaced by
  `detectProviderByRegistry()` which sorts matches by prefix length so
  longer distinguishing prefixes (`sk-cp-`, `sk-or-`, `tvly-`, `BSA`) win
  over generic `sk-`.

### Test Coverage
- **`tests/test_router_provider_registry.py`** (new, 92 tests): registry
  contents + capability filter + bug regressions for the router.
- **`tests/test_frontend_llm_providers.py`** (new, 14 tests): new endpoints
  + prefix-matching fix + backup script error handling — runs in ≈1 s.
- Full suite: **534 passed**, 2 pre-existing fails (`test_soul_memory_retrieval`,
  `TestVerifyCmd.test_protected_path_instant_blocked`), 2 skipped — unrelated
  to this change set; verified by re-running them on a clean `git stash`.

## [Unreleased — Permission-Refactor] - 2026-06-21
### Added
- **SecurityAG-Audit-Log (Option B "Strukturiert")**: Dedizierte
  `security_audit_log`-Tabelle (11 Spalten + 2 Indices) in
  `db/schema.py`, Helper `log_security_audit()` mit SHA-256-`content_hash` +
  Cap-Mechanik (2000/1600) in `db/system_repo.py`, Hook in
  `action_handlers.py` für 4 Action-Branches (WRITE×2 / SHELL / CRAWL /
  BROWSER). Trigger: `name=='securityag' AND ('godmode' OR 'run' OR
  'write') in perms`. Severity `high` wenn godmode, sonst `medium`.
  API-Endpoint `GET /api/security-audit-log` mit 6 Filtern
  (agent/action_type/result/severity/since/limit).
- **`docs/refactor-permissions/`** (10 Files): vollständige Audit-Trail
  für den Permission-Refactor (inventory, design-question, owner-decision,
  diff-definitions, dependent-changes, audit-impl, test-report, FINAL_TABLE).

### Changed
- **Agent-Permissions Least-Privilege-Refactor**: Alle 8 Agenten auf
  minimal-nötige Permissions reduziert. Vorher hatten 5/8 Agenten
  `godmode`; jetzt nur noch SecurityAG. Permission-Matrix (de == en
  pro Agent):
  - SoulAG:       [read,write,run,godmode,evolve] → [read, evolve, crawl]
  - GeneralAG:    [read, @job]                    → [read, @job] (unverändert)
  - WatchdogAG:   [read,write,run,godmode,…]      → [read]
  - SecurityAG:   [read,write,run,godmode,…]      → [read, write, run, godmode]
  - CoderAG:      [read,write,run,@job,godmode]   → [read, write, run]
  - WriterAG:     [read, write, crawl]            → [read, write, crawl] (unverändert)
  - ResearcherAG: [read,crawl,web_search,browser] → [read,crawl,web_search,browser] (unverändert)
  - EditorAG:     [read,write,run,@job,godmode]   → [read, write]
- **`action_handlers.py`**: Defense-in-Depth-Doku der Permission-Checks
  (alle entfernten Capabilities werden durch kontrollierte
  "keine-X-Berechtigung"-Fehlermeldungen abgefangen — keine silent
  crashes).
- **`gatekeeper.py`**: Hinweis auf jetzt-tote SoulAG-Bypasses (SoulAG
  verliert godmode, erreicht die Bypasses nicht mehr).

### Test Coverage
- **`tests/test_permission_refactor.py`** (new, 16 tests, 15 PASS + 1 SKIP):
  Negativ-Tests für alle entfernten Capabilities (WatchdogAG [SHELL]+[WRITE],
  EditorAG [SHELL], CoderAG ohne browser-Tool, GeneralAG unverändert) plus
  parametrisierte Matrix-Konsistenz (alle 8 Agents matchen Zielmatrix) plus
  Only-SecurityAG-has-godmode-Assertion.
- SecurityAG-Audit-Hook: 22/22 Runtime-Tests PASS (im
  `docs/refactor-permissions/audit-impl.md` dokumentiert; Migration
  idempotent, 3 Szenarien, Negativ-Test, Cap 2001→1600, API-Endpoint,
  Multi-Action, Sonderfälle Brainstorm-Override/Auto-Approve).
- Full suite: **565 passed** (550 baseline + 15 new), 4 pre-existing fails
  (`test_protected_path_instant_blocked`, 3× `test_workspace_config`
  path-validierung) byte-identisch zur Baseline — keine Regressionen.

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
