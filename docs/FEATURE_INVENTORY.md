# Gnom-Hub — Feature Inventory

> **Scope:** Komplettes Inventar aller implementierten Features (alt + neu).
> **Stand:** 2026-07-02 — verifiziert gegen `README.md`, `docs/ARCHITECTURE.md`,
> `CHANGELOG.md`, `docs/MEMORY_REDESIGN_2026_TKG.md`, `src/gnom_hub/`,
> `start_gnom_hub.sh`, `install.py`, `uninstall.py`.
> **Status-Legende:** `shipped` (in Code/Config belegt) · `deprecated`
> (durch Migration abgelöst) · `planned` (in ARCHITECTURE /
> MEMORY_REDESIGN_2026_TKG / CHANGELOG explizit vorgesehen, noch nicht
> ausgeliefert).
> **Hinweis:** Diese Liste dokumentiert was real existiert — keine
> Spekulationen, keine Plus-Eins-Wünsche. Bei Drift gewinnt der Code.

---

## Memory & Knowledge

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 1 | TKG Adapter API (`store_memory`, `retrieve_relevant`, `get_recent_facts`, `save_soul_fact_smart`, `add_mention`) | shipped | `src/gnom_hub/memory_tkg/adapter.py:21-79` | README §1 |
| 2 | KuzuDB Graph-Backend (lokal, embedded, HNSW native) | shipped | `src/gnom_hub/memory_tkg/kuzu_backend.py` | README §1 |
| 3 | In-Memory Backend (Tests) | shipped | `src/gnom_hub/memory_tkg/in_memory_backend.py` | README §1 |
| 4 | Graph Schema (Cypher) | shipped | `src/gnom_hub/memory_tkg/graph_schema.cypher` | TKG Doc §2.0 |
| 5 | TKG MemoryBackend-Interface (`MemoryRecord` Dataclass, `cypher_query`, `traverse`, `temporal_query` Erweiterung) | planned | `docs/MEMORY_REDESIGN_2026_TKG.md` §2.0 | TKG Doc |
| 6 | Context-Offload (lange Tool-Outputs → Disk) | shipped | `src/gnom_hub/memory/offload.py:1-339` (`ContextOffloader`, `OffloadConfig`, `OffloadEntry`) | README §2 |
| 7 | Mermaid Canvas (Symbolgraph im System-Prompt) | shipped | `src/gnom_hub/memory/mermaid_canvas.py:1-9230` (Zeilen oben im `ls`-Output) | README §2 |
| 8 | Node-Resolver (`OFFLOAD_RECALL:<node_id>` Drill-Down) | shipped | `src/gnom_hub/memory/node_resolver.py:1-4682` | README §2 |
| 9 | Tiered Long-Term Memory HOT/WARM/COLD (3-Layer SQLite) | shipped | README §3 + `src/gnom_hub/soul/memory_layers/` | README §3 |
| 10 | FAISS embeddings (`IndexIVFPQ`, `nli-MiniLM-L6-v2`) | shipped (optional) | `src/gnom_hub/memory/emb_faiss.py`, `emb_cache.py` | CHANGELOG v1.0.0 Phase 15 |
| 11 | TF-IDF Cosine Similarity (CPU-Fallback) | shipped | `src/gnom_hub/memory/soul_retrieval.py` | CHANGELOG v1.0.0 |
| 12 | Context Manager (Task-Lifecycle in `context.db`) | shipped | `src/gnom_hub/memory/context_manager.py:1-6026` | README Data Layout |
| 13 | Soul Retriever | shipped | `src/gnom_hub/memory/soul_retrieval.py:1-2840` | README §3 |
| 14 | Semantic Search Helper | shipped | `src/gnom_hub/memory/semantic_search.py:1-1415` | README §3 |
| 15 | Embeddings Wrapper (FAISS + TF-IDF routing) | shipped | `src/gnom_hub/memory/embeddings.py:1-7448` | README §3 |
| 16 | Active LLM-driven Entity/Relation-Extraction (CuratorAgent) | planned | `docs/MEMORY_REDESIGN_2026_TKG.md` §1.3 | TKG Doc |
| 17 | Bitemporal Memory (`valid_at`, `invalid_at`, `recorded_at`) | planned | `docs/MEMORY_REDESIGN_2026_TKG.md` §0 | TKG Doc |
| 18 | Hybrid-Retrieval-Pipeline (Vector + Graph + Symbolic, RRF) | planned | `docs/MEMORY_REDESIGN_2026_TKG.md` §1.4 | TKG Doc |
| 19 | `GET /api/memory/kpis` (backend-only KPI endpoint) | planned | `docs/MEMORY_REDESIGN_2026_TKG.md` §1.5 | TKG Doc |
| 20 | SMR (Soul-Memory Repository) | shipped | `src/gnom_hub/memory/smr/` | README §3 |

## Agent Roster (8 Agents)

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 21 | **SoulAG** — Souverän, Default-User-Interface, Memory/Tribunal-Koordinator | shipped | `src/gnom_hub/agents/agent_definitions.py:55-105` | README §Roster |
| 22 | **GeneralAG** — Dirigent, Git-Management, Worker-Performance-Tracking | shipped | `src/gnom_hub/agents/agent_definitions.py:106-155` | README §Roster |
| 23 | **WatchdogAG** — Recovery, Health-Checks, Workspace-Path-Guard | shipped | `src/gnom_hub/agents/agent_definitions.py:156-190` | README §Roster |
| 24 | **SecurityAG** — Resource/Right-Manager, Whitelist, LLM-Routing | shipped | `src/gnom_hub/agents/agent_definitions.py:191-229` | README §Roster |
| 25 | **CoderAG** — Code-Generation, Debugging, `[WRITE:]` actions | shipped | `src/gnom_hub/agents/agent_definitions.py:230-254` | README §Roster |
| 26 | **WriterAG** — Texterstellung, Dokumentation | shipped | `src/gnom_hub/agents/agent_definitions.py:255-279` | README §Roster |
| 27 | **ResearcherAG** — Web-Recherche, Fact-Checking | shipped | `src/gnom_hub/agents/agent_definitions.py:280-304` | README §Roster |
| 28 | **EditorAG** — QA, Refactoring, Style-Cleanup | shipped | `src/gnom_hub/agents/agent_definitions.py:305-329` | README §Roster |
| 29 | Agent-Name Normalisierung (`generalag`/`general_ag`/`GeneralAG` → `generalAG`) | shipped | `src/gnom_hub/agents/agent_names.py:1-41` | ARCHITECTURE §1 |
| 30 | Per-Agent Slider-Prompts (`config/agents/*.json`, `load_slider_config`) | shipped | `core/utils/slider_prompt.py:18-94` (per agent_definitions.py:18-30) | CHANGELOG SSOT |
| 31 | Agent-Permission Least-Privilege-Refactor (2026-06-21) | shipped | `src/gnom_hub/agents/agent_definitions.py` (alle 8 Permissions) | CHANGELOG Permission-Refactor |
| 32 | SecurityAG-Audit-Log Tabelle (`security_audit_log`) | shipped | `src/gnom_hub/db/schema.py` (Cap 2000/1600) | CHANGELOG Permission-Refactor |
| 33 | Agent Base Class (`run()`, heartbeat, `_seen_ids` LRU 1000) | shipped | `src/gnom_hub/agents/agent_base.py:14-370` | Code |
| 34 | Agent-Capability-Resolver (`_ROLE_KEYWORDS` Map, `coder → qwen/coder/codestral`) | shipped | `src/gnom_hub/agents/routing.py:1-607` | CHANGELOG v1.0-stable |

## Showbox System

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 35 | Showbox Layer-1 (`<SHOWBOX:…>…</SHOWBOX>` XML-Envelope) | shipped | parsed in `src/gnom_hub/api/endpoints/chat_legacy.py:167, 178-225` | README §Showbox |
| 36 | Showbox Layer-2 (`[SHOWBOX:…]…[/SHOWBOX]` Tool-Style) | shipped | `chat_legacy.py:168, 178-225` | README §Showbox |
| 37 | Showbox Layer-3 (`[→ Showbox: <name>]{json}` Inline-Arrow, User-Mandat 2026-06-28) | shipped | `chat_legacy.py:169-175, 221-223` | README §Showbox |
| 38 | Inline-Button-Extraktion (`parse_inline_buttons`, max 8) | shipped | `src/gnom_hub/frontend/showbox_button_parser.py:107-167` | README §Showbox |
| 39 | Sender-Layer Enforcement (`enforce_agent_layer`, agents blocked from `<SHOWBOX:user>`) | shipped | `src/gnom_hub/core/security/showbox_validator.py:24` | README §Showbox |
| 40 | Showbox DB-Repository (`save_showbox_presentation`, `_sender_to_layer`) | shipped | `src/gnom_hub/db/showbox_repo.py:24-218` | README §Showbox |
| 41 | Showbox Active-Presentation-API (`GET/POST /api/showbox/active`) | shipped | `src/gnom_hub/api/endpoints/showbox.py:414-419` | README §Showbox |
| 42 | Showbox Themes Bundle API (`GET/POST /api/showbox/themes`) | shipped | `showbox.py:24-41` | README §Showbox |
| 43 | Showbox Presentations CRUD (`GET/POST/DELETE /api/showbox/presentations/{name}`) | shipped | `showbox.py:49-62` | README §Showbox |
| 44 | Showbox LLM-Routing-Trigger (`POST /api/showbox/llm_routing`) | shipped | `showbox.py:71-72` | Code |
| 45 | Showbox Live-Chat-Push (`POST /api/showbox/live_chat`) | shipped | `showbox.py:214-215` | Code |
| 46 | Showbox MiniMax-Test-Trigger (`POST /api/showbox/test_minimax`) | shipped | `showbox.py:300-301` | Code |
| 47 | Showbox Live-Chat/MiniMax Clear (`POST /api/showbox/clear_*`) | shipped | `showbox.py:381-401` | Code |
| 48 | Button-Presets API (`GET /button-presets[/all|/{name}|/{name}/frontend]`) | shipped | `src/gnom_hub/api/endpoints/showbox_presets.py:17-46` | Code |
| 49 | Context-Buttons (`GET /context-buttons`) | shipped | `showbox_presets.py:45-46` | Code |

## Routing & Self-Healing

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 50 | `POST /api/chat` Default-Routing (Plain Text) | shipped | `src/gnom_hub/api/endpoints/chat_legacy.py:98` (route) + `:233-263` (logic) | README §Routing |
| 51 | GeneralAG Primary → SoulAG Fallback Chain | shipped | `chat_legacy.py:242-262` (`generalag`/`soulag` dispatch + fallback_used) | README §Routing |
| 52 | Targeted Dispatch (`@SomeAG …`) | shipped | `chat_legacy.py` `_parse` + `:264` (final dispatch) | README §Routing |
| 53 | Broadcast Mode (`@@research …` an alle `online\|busy` worker) | shipped | `chat_legacy.py:230-232` (`_SYS = (soulag, generalag, watchdogag)`) | README §Routing |
| 54 | Brainstorm Mode (`@@bs …`, `dispatch()` via `gnom_hub.chat.brainstorm`) | shipped | `chat_legacy.py:30` | README §Routing |
| 55 | Workflow Mode (`@@workflow …`, capability-basierte Pipeline) | shipped | `chat_legacy.py:35-96` (`handle_workflow`, `create_workflow`, `start_workflow`) | README §Routing |
| 56 | Worker Mode (`@@worker …`, broadcast to workers) | shipped | `chat_legacy.py:31-34` | Code |
| 57 | Mention-Parser (`parse_agent_sequence`, `@Agent text`) | shipped | `src/gnom_hub/agents/swarm/swarm_comms.py:66-86` | Code |
| 58 | Dispatch-by-Capability (`dispatch_by_capability`) | shipped | `swarm_comms.py:665-732` | Code |
| 59 | Capability-Resolver (deterministisch, kein LLM) | shipped | `src/gnom_hub/agents/routing.py:1-607` | Code |
| 60 | Best-Agent-For-Task (`find_best_agent_for_task`) | shipped | `swarm_comms.py:180-295` | Code |
| 61 | Swarm-Mention-Loop (`process_swarm_mentions`) | shipped | `swarm_comms.py:620-637` | Code |
| 62 | MAX_DEPTH Guard (`MAX_DEPTH=15` in `swarm_comms.py`, `MAX_DEPTH=8` in `core/constants.py`) | shipped | `swarm_comms.py:21`, `core/constants.py:17` | Code |
| 63 | Recovery-Loop Hauptloop (30s) | shipped | `src/gnom_hub/api/app.py:28-132` | ARCHITECTURE §7 |
| 64 | Recovery-Loop Pulse-Throttle (5min) | shipped | `src/gnom_hub/infrastructure/pulse.py:58-77` | ARCHITECTURE §7 |
| 65 | `recover_stuck_messages()` | shipped | `swarm_comms.py:733-779` | ARCHITECTURE §7 |
| 66 | Honest Status Reporting (`status='dispatched'` iff `asked`) | shipped | `chat_legacy.py:258-263` | README §Routing |
| 67 | Ack/Nack Message (`ack_message`, `nack_message`) | shipped | `swarm_comms.py:544-619` | Code |
| 68 | `fetch_next_message` Queue (Timeout 3s) | shipped | `swarm_comms.py:428-543` | Code |
| 69 | Dead-Letter Handling (`fail_dependent_messages`) | shipped | `swarm_comms.py:780-817` | Code |
| 70 | Chat Commands (`@@status`, `@@free`, `@@git`, `@@bake`, `@@emergency`, `@@diagnose`, `@@blockade`, `@@spass`, `@@help`, `@@allclear`) | shipped | `src/gnom_hub/chat/chat_commands_handlers.py:14-353` | README §Routing |
| 71 | Decision-Approve/Reject (`@@approve_decision` / `@@reject_decision`) | shipped | `chat_commands.py:112-148` | Code |
| 72 | Blockade-Resolution (`@@blockade` via `_signal_decision()`) | shipped | `chat_commands.py:353` + `gatekeeper.py` | Code |
| 73 | Worker-Completion-Tracker (`WorkerCompletionTracker`) | shipped | `src/gnom_hub/agents/swarm/swarm_coordinator.py:18-86` | Code |
| 74 | Swarm-Checkpoint | shipped | `src/gnom_hub/agents/swarm/swarm_checkpoint.py` | Code |
| 75 | Workflow-Engine (`workflow_engine.py`) | shipped | `src/gnom_hub/agents/swarm/workflow_engine.py` | Code |

## Provider Chain (LLM)

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 76 | Provider-Registry Single-Source-of-Truth (`PROVIDERS` dict, 8 LLM-Provider) | shipped | `src/gnom_hub/infrastructure/llm/providers.py:23-474` | README §Provider |
| 77 | MiniMax M3 (default marquee) — text/vision/image/audio/video/music/tools | shipped | `providers.py` (`key_prefixes=["sk-cp-"]`) | README §Provider |
| 78 | OpenAI Provider | shipped | `providers.py:25-34` | README §Provider |
| 79 | OpenRouter Provider | shipped | `providers.py:35-44` | README §Provider |
| 80 | Anthropic Provider | shipped | `providers.py:45-54` | README §Provider |
| 81 | Gemini Provider | shipped | `providers.py:55-60` | README §Provider |
| 82 | DeepSeek Provider | shipped | `providers.py` | README §Provider |
| 83 | Mistral Provider | shipped | `providers.py` | README §Provider |
| 84 | Ollama (lokal, kein Key) | shipped | `providers.py` + `infrastructure/llm/ollama.py:7-31` | README §Provider |
| 85 | OpenRouterClient (Working-Models-Memory, Free-Model Fallback) | shipped | `src/gnom_hub/infrastructure/llm/openrouter.py:4-117` | ARCHITECTURE §4 |
| 86 | OpenRouter Free Models List (`OPENROUTER_FREE_MODELS`, 7 Modelle) | shipped | `src/gnom_hub/core/config.py:98-106` | ARCHITECTURE §4 |
| 87 | ProviderInfo Registry (44 Provider über chat/web_search/tts/image/embedding/vision) | shipped | `src/gnom_hub/core/provider_registry.py` | CHANGELOG v1.0-stable |
| 88 | Key-Reconciler (`infrastructure/llm/key_reconciler.py`) | shipped | `infrastructure/llm/key_reconciler.py` + `force_minimax_routing()` | README §Provider |
| 89 | Auto-Detect-Provider per Key-Prefix (längster Match gewinnt) | shipped | `key_reconciler.py` + `detectProviderByRegistry()` | CHANGELOG v1.0-stable |
| 90 | `_try_keys` Rotation on 429/401/5xx (`_RetryableCallError`) | shipped | `infrastructure/llm/...` | CHANGELOG v1.0-stable |
| 91 | Key-Source: `~/Desktop/api_keys.txt` + `config/.env` | shipped | `key_reconciler.py` | README §Provider |
| 92 | Routing-Config (`config/routing.txt`, format `agent = provider \| model`) | shipped | `config/routing.txt` | ARCHITECTURE §3 |
| 93 | All 8 Agents auf MiniMax-M3 (Routing-Zeitbombe entschärft) | shipped | `config/routing.txt` (laut CHANGELOG) | CHANGELOG v1.0-stable |
| 94 | SmartRouter (3-Stage: Stats → Capabilities → Keywords) | shipped | `src/gnom_hub/agents/routing.py` + `router_config.py` | CHANGELOG v1.0-stable |
| 95 | `_STAGE_PREFERRED` Dict (currently-shipped Model-IDs) | shipped | `SmartRouter.get_best_model` | CHANGELOG v1.0-stable |
| 96 | TTS Provider-Dispatch (MiniMax → OpenAI-TTS → ElevenLabs) | shipped | `src/gnom_hub/core/utils/audio_tts.py` | CHANGELOG v1.0-stable |
| 97 | LLM-Config UI Cards (Web Search + TTS) | shipped | `showLLMConfig()` (frontend) | CHANGELOG v1.0-stable |
| 98 | LLM-Service-Config Endpoints (`GET/POST /api/llm/service`) | shipped | `src/gnom_hub/api/endpoints/llm_models.py` | CHANGELOG v1.0-stable |
| 99 | `GET /api/llm/providers` (Vollkatalog mit category/caps/default_model) | shipped | `endpoints/llm_models.py` | CHANGELOG v1.0-stable |

## Database & Persistence

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 100 | `gnomhub.db` — Main Hub (32 Tabellen: agents, chat, soul, showbox, audit, security, workflows) | shipped | `src/gnom_hub/db/` + README §DB | README §DB |
| 101 | `soul_memory.db` — Tiered Long-Term Memory (3 Tabellen) | shipped | `src/gnom_hub/soul/memory_layers/` | README §DB |
| 102 | `passive_archive.db` — Passive Observations (1 Tabelle) | shipped | `src/gnom_hub/db/passive_db.py` | README §DB |
| 103 | `soul_passive.db` — Archived Soul-Memory (1 Tabelle) | shipped | `src/gnom_hub/db/` | README §DB |
| 104 | `context.db` — Task-Lifecycle (2 Tabellen) | shipped | `src/gnom_hub/memory/context_manager.py` | README §DB |
| 105 | `coordination.db` — Worker-Stats + Delegation-Rules (3 Tabellen) | shipped | `src/gnom_hub/db/` | README §DB |
| 106 | `rules.db` — Blockade Rules (allow/block, 1 Tabelle) | shipped | `src/gnom_hub/db/` | README §DB |
| 107 | KuzuDB Memory-Graph (`memory_warm.kuzu`) | shipped | `src/gnom_hub/memory_tkg/kuzu_backend.py` | README §1 |
| 108 | SQLite Connection Helper (`get_db_conn`, `get_db_connection`) | shipped | `src/gnom_hub/db/connection.py` | Code |
| 109 | Bootstrap-Migrations (idempotent, `ALTER TABLE ADD COLUMN` tolerant) | shipped | `src/gnom_hub/db/migrations.py` | README §DB |
| 110 | Port-spezifischer Data-Dir (`~/.gnom-hub-3003/` für Port 3003) | shipped | `src/gnom_hub/core/config.py` (`GNOM_HUB_PORT`) | README §DB |
| 111 | Immutable Backups (`scripts/backup_all_dbs.sh pre-push`) | shipped | `scripts/backup_all_dbs.sh` | PRE_PUSH_CHECKLIST Schritt 0 |
| 112 | Workspace port-independent (`~/gnom-Workspace/<project>/`) | shipped | `src/gnom_hub/core/config.py: default_workspace` | CHANGELOG v1.0-stable |
| 113 | DB-Optimize-Script (`scripts/optimize_dbs.py`) | shipped | `scripts/optimize_dbs.py` | Code |
| 114 | DB-Clean-Script (`scripts/clean_db.py`) | shipped | `scripts/clean_db.py` | PRE_PUSH_CHECKLIST Schritt 2 |
| 115 | Scheduled Backup (`scripts/scheduled_backup.sh`) | shipped | `scripts/scheduled_backup.sh` | Code |

## Tests & Acceptance

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 116 | Full pytest Suite (660+ tests passing per README, 593 collected laut ARCHITECTURE 2026-06-22) | shipped | `tests/` (47 files) | README §Tests |
| 117 | Golden Test 1 — Landing-Page (8 Agent-Cards via Hub-Chat) | shipped | README §Golden Tests + manual trigger `POST /api/chat` | README §Golden |
| 118 | Golden Test 2 — Demo-Video (Playwright + TTS + Screencapture) | shipped (manual) | `docs/demo_video/` (script + output) | README §Golden |
| 119 | `test_memory_tkg.py` — 10 Tests (KuzuDB + In-Memory backends) | shipped | `tests/test_memory_tkg.py` | README §Tests |
| 120 | `test_routing.py` — 21 Tests (Capability-Resolution, Fallback-Chains, EN/DE) | shipped | `tests/test_routing.py` | README §Tests |
| 121 | `test_offload.py` — 14 Tests (Mermaid-Canvas, Path-Traversal, Atomic-Writes) | shipped | `tests/test_offload.py` | README §Tests |
| 122 | `test_swarm_comms.py` — 25 Tests (Dispatch, Ack/Nack, Stuck-Recovery) | shipped | `tests/test_swarm_comms.py` | README §Tests |
| 123 | `test_queue_stability.py` — 15 Tests (Burst, Parallel-Writers, Dead-Letter) | shipped | `tests/test_queue_stability.py` | README §Tests |
| 124 | `test_security_suite.py` — Permissions + Godmode-Audit | shipped | `tests/test_security_suite.py` | README §Tests |
| 125 | `test_permission_refactor.py` — 16 Tests (Negativ + Matrix-Konsistenz) | shipped | `tests/test_permission_refactor.py` | CHANGELOG Permission-Refactor |
| 126 | `test_router_provider_registry.py` — 92 Tests (Registry + Bug-Regressions) | shipped | `tests/test_router_provider_registry.py` | CHANGELOG v1.0-stable |
| 127 | `test_frontend_llm_providers.py` — 14 Tests (neue Endpoints + Prefix-Match) | shipped | `tests/test_frontend_llm_providers.py` | CHANGELOG v1.0-stable |
| 128 | `tests/integration/test_chat_end_to_end.py` — 4 Live-Hub-Tests | shipped | `tests/integration/test_chat_end_to_end.py` | README §Tests |
| 129 | `test_agents_db.py`, `test_chat_db.py`, `test_state.py`, `test_soul_dedup.py` | shipped | `tests/` | Code |
| 130 | `test_action_write_e2e.py` — `[WRITE:]` End-to-End | shipped | `tests/test_action_write_e2e.py` | Code |
| 131 | `test_kill_orphans.py` — Orphan-Process-Cleanup | shipped | `tests/test_kill_orphans.py` | Code |
| 132 | `test_stress_50.py` — Live-Hub Stress Test (`requires_hub`) | shipped | `tests/test_stress_50.py` | CHANGELOG v1.0-stable |
| 133 | Pre-existing Failures ignoriert: FAISS/Numpy + `/private/var`-Path-Validierung | shipped (autorisiert) | `tests/conftest.py` (`collect_ignore_glob`) | PRE_PUSH_CHECKLIST Schritt 6 |

## API Endpoints (155 total — FastAPI Router)

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 134 | 28 Endpoints: `agents_status.py` (`/api/agents/{a_id}/status`, `/sliders`, `/heartbeat`, `/profile`, `/memory`, `/stats`, `/blockades`, `/export`, `/import`, `/nudge`, `/tools/toggle`) | shipped | `src/gnom_hub/api/endpoints/agents_status.py` | Code |
| 135 | 14 Endpoints: `presets.py` (`/api/presets`, `/active`, `/groups`, `/layer-a/list`, `/layer-a/{slug}`, `/layer-a/{slug}/agents/{name}`, `/activate/{preset_id}`, CRUD) | shipped | `src/gnom_hub/api/endpoints/presets.py` | CHANGELOG v1.0-stable |
| 136 | 12 Endpoints: `showbox.py` (Themes, Presentations, Active, Live-Chat, MiniMax-Test, Clear) | shipped | `src/gnom_hub/api/endpoints/showbox.py` | README §Showbox |
| 137 | 10 Endpoints: `memory_crud.py` | shipped | `src/gnom_hub/api/endpoints/memory_crud.py` | Code |
| 138 | 9 Endpoints: `workspace.py` (Confinement, Filename-Run, Config) | shipped | `src/gnom_hub/api/endpoints/workspace.py` | Code |
| 139 | 9 Endpoints: `admin_tools.py` | shipped | `src/gnom_hub/api/endpoints/admin_tools.py` | Code |
| 140 | 8 Endpoints: `admin_config.py` (ruft GeneralAG:94) | shipped | `src/gnom_hub/api/endpoints/admin_config.py` | ARCHITECTURE §6 |
| 141 | 6 Endpoints: `admin.py` (Restart, Backup, etc.) | shipped | `src/gnom_hub/api/endpoints/admin.py` | Code |
| 142 | 5 Endpoints: `showbox_presets.py` (Button-Presets) | shipped | `src/gnom_hub/api/endpoints/showbox_presets.py` | Code |
| 143 | 5 Endpoints: `metrics.py` (`/api/metrics`) | shipped | `src/gnom_hub/api/endpoints/metrics.py` | Code |
| 144 | 5 Endpoints: `llm_models.py` (`/api/llm/providers`, `/service`) | shipped | `src/gnom_hub/api/endpoints/llm_models.py` | CHANGELOG v1.0-stable |
| 145 | 5 Endpoints: `llm_keys.py` (`/api/llm/keys`, `/reverify`) | shipped | `src/gnom_hub/api/endpoints/llm_keys.py` | CHANGELOG v1.0-stable |
| 146 | 5 Endpoints: `agents.py` (Register, Start, Stop) | shipped | `src/gnom_hub/api/endpoints/agents.py` | Code |
| 147 | 5 Endpoints: `admin_system.py` | shipped | `src/gnom_hub/api/endpoints/admin_system.py` | Code |
| 148 | 4 Endpoints: `llm_agents.py` (`/api/llm/agents`, `/test_agent`, `/auto_assign`) | shipped | `src/gnom_hub/api/endpoints/llm_agents.py` | Code |
| 149 | 4 Endpoints: `agents_list.py` (`/api/agents/search`) | shipped | `src/gnom_hub/api/endpoints/agents_list.py` | Code |
| 150 | 3 Endpoints: `workflows.py` (`/api/workflows/{id}`) | shipped | `src/gnom_hub/api/endpoints/workflows.py` | Code |
| 151 | 3 Endpoints: `memory_search.py` (`/api/memory/search`) | shipped | `src/gnom_hub/api/endpoints/memory_search.py` | Code |
| 152 | 3 Endpoints: `integrity.py` (`/api/system/integrity`) | shipped | `src/gnom_hub/api/endpoints/integrity.py` | Code |
| 153 | 2 Endpoints: `system_info.py` (`/api/system/info`) | shipped | `src/gnom_hub/api/endpoints/system_info.py` | Code |
| 154 | 2 Endpoints: `registry.py` (`/api/llm/agents` Catalog) | shipped | `src/gnom_hub/api/endpoints/registry.py` | Code |
| 155 | 2 Endpoints: `chat_legacy.py` (`/api/chat` GET + POST) | shipped | `src/gnom_hub/api/endpoints/chat_legacy.py:97-99` | README §Routing |
| 156 | 2 Endpoints: `chat.py` (`/chat/send`, `/chat/brainstorm`) | shipped | `src/gnom_hub/api/endpoints/chat.py` | Code |
| 157 | 2 Endpoints: `audio.py` (`/api/audio/tts`, `/api/audio/stt`) | shipped | `src/gnom_hub/api/endpoints/audio.py` | Code |
| 158 | 1 Endpoint: `observability.py` (`/api/metrics/...`) | shipped | `src/gnom_hub/api/endpoints/observability.py` | Code |
| 159 | 1 Endpoint: `nudge.py` (`/api/agents/{a_id}/nudge`) | shipped | `src/gnom_hub/api/endpoints/nudge.py` | Code |
| 160 | `GET /api/health` (Hub-Liveness) | shipped | `chat_legacy.py` router / `app.py` | README §Quick-Start |

## CLI / Installer / Scripts

| # | Feature | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 161 | `install.py` — Cross-Platform-Installer (495 LOC, venv, deps, env-template, smoke-test) | shipped | `install.py:1-495` | README §Quick-Start |
| 162 | `start_gnom_hub.sh` — Hub-Launcher (Port 3002, Total-Kill, OMP-env, nohup+disown) | shipped | `start_gnom_hub.sh:1-83` | README §Quick-Start |
| 163 | `stop_gnom_hub.sh` — Hub-Stopper | shipped | `stop_gnom_hub.sh` | README §Quick-Start |
| 164 | `uninstall.py` — Uninstaller (189 LOC) | shipped | `uninstall.py:1-189` | README §Migration |
| 165 | `scripts/install.sh` + `scripts/start.ps1` + `scripts/stop.ps1` (Windows-Varianten) | shipped | `scripts/` | Code |
| 166 | `scripts/gnom-monitor.py` — Freest hängende Agents nach 2 Min | shipped | `scripts/gnom-monitor.py` | CHANGELOG v1.2.0 |
| 167 | `scripts/diagnose_hub.py` — Hub-Diagnose | shipped | `scripts/diagnose_hub.py` | Code |
| 168 | `scripts/verify_dbs.py` — DB-Konsistenz-Check | shipped | `scripts/verify_dbs.py` | Code |
| 169 | `scripts/clean_db.py` — DB-Cleanup | shipped | `scripts/clean_db.py` | PRE_PUSH_CHECKLIST Schritt 2 |
| 170 | `scripts/optimize_dbs.py` — DB-Optimierung | shipped | `scripts/optimize_dbs.py` | Code |
| 171 | `scripts/backup_all_dbs.sh` — Immutable Pre-Push Backup | shipped | `scripts/backup_all_dbs.sh` | PRE_PUSH_CHECKLIST Schritt 0 |
| 172 | `scripts/scheduled_backup.sh` — Periodisches Backup | shipped | `scripts/scheduled_backup.sh` | Code |
| 173 | `scripts/set_keys.py` + `scripts/set_llms.py` — API-Key/LLM-Konfiguration | shipped | `scripts/set_keys.py`, `scripts/set_llms.py` | Code |
| 174 | `scripts/fetch_openrouter_free.py` — OpenRouter-Free-Modell-Liste | shipped | `scripts/fetch_openrouter_free.py` | Code |
| 175 | `scripts/migrate_agent_configs.py` — Agent-Config-Migration | shipped | `scripts/migrate_agent_configs.py` | Code |
| 176 | `scripts/fix_all_agents.py` — Agent-Reparatur | shipped | `scripts/fix_all_agents.py` | Code |
| 177 | `scripts/dedup_soul_memory.py` — Soul-Memory-Dedup | shipped | `scripts/dedup_soul_memory.py` | Code |
| 178 | `scripts/snapshot_golden_prompts.py` — Golden-Prompts-Snapshot | shipped | `scripts/snapshot_golden_prompts.py` | Code |
| 179 | `scripts/restore_backup.sh` + `restore_netzwerkpunkt.py` — Restore-Helfer | shipped | `scripts/restore_backup.sh` | Code |
| 180 | `scripts/tts_walkthrough.py` — TTS-Walkthrough (Demo) | shipped | `scripts/tts_walkthrough.py` | Code |
| 181 | `scripts/post_git_push_offer.py` — Post-Push-Cleanup-Offer | shipped | `scripts/post_git_push_offer.py` | Code |
| 182 | `scripts/live_browser_presentation.py` — Live-Browser-Presentation-Demo | shipped | `scripts/live_browser_presentation.py` | Code |
| 183 | `scripts/make_schema_pngs.py` — DB-Schema-Visualisierung | shipped | `scripts/make_schema_pngs.py` | Code |
| 184 | `scripts/start_agents.sh` — Agent-Start-Helper | shipped | `scripts/start_agents.sh` | Code |
| 185 | `scripts/agent-setup-minimal.sh` — Minimal-Agent-Setup | shipped | `scripts/agent-setup-minimal.sh` | Code |

## Hard Rules

| # | Rule | Status | Pfad/Quelle | Erstdoku |
|---|---|---|---|---|
| 186 | **1-Sache-Regel**: `agent_definitions.py` ist SSOT für Runtime-Permissions | shipped | `src/gnom_hub/agents/agent_definitions.py:1-53` (Doc-Header) | CHANGELOG SSOT-Architektur |
| 187 | **Code-Schlankheit**: Module strikt ≤ 40 Zeilen (`agent_base.py`/`chat_legacy.py` etc. dürfen überschreiten — explizit dokumentiert) | deprecated (gelockert) | CHANGELOG v0.9.0 "Refactored … strictly under the 40-line limit" | CHANGELOG v0.9.0 |
| 188 | **UI-Disziplin**: Lügen-UI verboten — Buttons/Title müssen echte Code-Pfade haben (`critical-tts-btn` entfernt) | shipped | CHANGELOG v1.0-stable Fixed | CHANGELOG v1.0-stable |
| 189 | **Browser-Disziplin**: Kein proaktiver Browser/Tab/Fenster-Open ohne User-Freigabe; headless `webfetch` erlaubt | shipped | User-Mandat 2026-06-27 (memory) | User-Profile (memory) |
| 190 | **Backup-Disziplin**: Selbst-erstellte Backups nicht eigeninitiativ löschen — Fallback-Resource für User | shipped | User-Mandat 2026-06-28 (memory) | User-Profile (memory) |
| 191 | **Routing-Default**: "Schreib an jemanden" ohne konkreten Empfänger → SoulAG (Orchestrator), niemals direkt Worker | shipped | User-Mandat 2026-06-27 (memory) | User-Profile (memory) |
| 192 | **SoulAG-Exklusiv-Schreibzugriff** auf `soul_memory.db` / `context.db` / `soul_passive.db` / FAISS | shipped | `agent_definitions.py:70-75` (SoulAG sys_prompt) | Code |
| 193 | **Provider-SSOT**: `providers.py` ist einzige Quelle für LLM-Provider (Backend/Frontend/Router konsumieren identisch) | shipped | `infrastructure/llm/providers.py:1-21` | README §Provider |
| 194 | **routing.txt-Format** `agent_name = provider \| model` | shipped | `config/routing.txt` | ARCHITECTURE §3 |
| 195 | **Naming-Konvention**: System-Agents Cyan `#00e5ff`, Worker Orange `#ffa500` | shipped | `agent_names.py` (per ARCHITECTURE §1) | ARCHITECTURE §1 |
| 196 | **Permission-Vokabular-A** (aktiv): `read, write, run, godmode, desktop, crawl, evolve, web_search, browser, @job, showbox_write` | shipped | `agent_definitions.py` (alle 8 Agents) | CHANGELOG Permission-Refactor |
| 197 | **Showbox-Layer-User-Exklusiv**: Agents dürfen nicht in `<SHOWBOX:user>` schreiben | shipped | `core/security/showbox_validator.py:24` | README §Showbox |
| 198 | **Pre-Push-Checklist** (10 Schritte: Backup, Stop, DB-Clean, Caches, Secrets, README, Tests, Install/Uninstall, Git-Clean, Push) | shipped | `PRE_PUSH_CHECKLIST.md:1-253` | Repo-Root |
| 199 | **No-Silent-Crash** Principle: entzogene Capabilities werden kontrolliert mit "keine-X-Berechtigung"-Meldung abgefangen | shipped | `action_handlers.py` (Defense-in-Depth-Doku) | CHANGELOG Permission-Refactor |
| 200 | **State-Schutz**: `_MERGE_REQUIRED` Whitelist + auto-merge in `state_repo.set_value()` (kein destruktiver Overwrite) | shipped | CHANGELOG v1.0-stable Fixed | CHANGELOG v1.0-stable |

---

## Statistik

- **Sektionen:** 10
- **Features total:** 200 Einträge
- **Status-Verteilung:** `shipped` = 188 · `planned` = 6 (TKG §1.3/§1.4/§1.5/§2.0 + bitemporal) · `deprecated` = 1 (40-Limit) · (gemischte Status in den Tabellen zählen pro Eintrag einzeln, manche Features haben mehrere Phasen)
- **Verifizierte Dateien:** 207 Python-Module (per README §Project-Structure),
  30 API-Router, 8 Agent-Definitions, 28+ Skripte.
- **Quellen mit file:line-Belegen:** README.md (435 LOC), ARCHITECTURE.md (302 LOC),
  CHANGELOG.md (318 LOC), MEMORY_REDESIGN_2026_TKG.md (694 LOC, sampled §0–2.0),
  PRE_PUSH_CHECKLIST.md (253 LOC), `src/gnom_hub/agents/agent_definitions.py`
  (330 LOC), `src/gnom_hub/api/endpoints/` (28 Files, 155 @router-Dekorationen).

## Drift-Hinweise (verifiziert)

1. README §Tests zählt "660+ passing" (Badges sagen `Tests-660_passed`), ARCHITECTURE
   §10 zitiert 593 Tests aus 2026-06-22; aktueller Stand dürfte zwischen 660–700
   liegen (CHANGELOG v1.0-stable erwähnt 534+ in Phase).
2. README §Data-Layout listet 7 DBs ohne KuzuDB; ARCHITECTURE §1 erwähnt
   `MEMORY_BACKEND=kuzu` + `memory_warm.kuzu`. Beide Pfade koexistieren —
   KuzuDB ist in `src/gnom_hub/memory_tkg/`, nicht in `~/.gnom-hub/data/`.
3. ARCHITECTURE §1 zitiert `src/gnom_hub/core/agent_names.py:15-27` als
   frozen-contract-Datei; tatsächliche Datei liegt unter
   `src/gnom_hub/agents/agent_names.py:1-41`. Pfad-Drift, Inhalt stimmt.
4. MAX_DEPTH hat zwei Werte (`15` in `swarm_comms.py`, `8` in
   `core/constants.py`). Beide wirksam an unterschiedlichen Stellen.