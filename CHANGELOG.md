# Changelog

All notable changes to this project will be documented in this file.

## [v1.2.0] - 2026-06-08
### Added
- **Event-basierter Gatekeeper**: `threading.Event` statt `while True: sleep(0.3); poll()` — 0% CPU im Wait, 0 DB-Operationen, instant Wake-up bei User-Entscheidung.
- **ZWC-Direktivensystem**: SoulAG kann via `emit_directive()` TTL-begrenzte Anweisungen als unsichtbare ZWC-Metadaten einbetten. Agents lesen sie via `get_directives()`.
- **154 Tests** (vorher 139): 15 Queue-Load-Tests für SQLite-Message-Queue unter Last.
- **index.html-Versionierung**: Automatische Hochzählung (index1.html, index2.html) statt Überschreiben.

### Fixed
- **dispatch_sequence() respektiert Backpressure**: Prüft jetzt `MAX_QUEUE_DEPTH` via zentraler `can_accept_message()`.
- **ack_message() resetiert child.deliver_after**: Parent-Completion macht Children sofort abholbar (keine 3s Verzögerung).
- **DEPENDENCY_TIMEOUT prüft processing_since**: Statt created_at — Timeout zählt ab Prozessstart, nicht ab Queue-Einreihen.
- **fail_dependent_messages() via SQL-Recursive-CTE**: Flach statt Python-Rekursion. Kaskade überspringt done-Messages, erreicht aber deren Children.
- **pulse.py**: Print → logging, Timeout 60s→30s, Nachricht korrigiert ("1 Minute" statt "5 Minuten").
- **chat_helpers.py**: `@blockade`/`@blokade` in Parser-Whitelist ergänzt.
- **pulse.py**: SyntaxError im try/except-Block behoben (indentation).

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
