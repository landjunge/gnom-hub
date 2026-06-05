# GNOM-HUB Master Briefing für ausführende KI
# Generiert am 05.06.2026
# Ziel: Vollständiges Systemverständnis für Neu-Implementierung oder Erweiterung

---

## 🧠 SCHRITT 1 — BRAINSTORMING (Ideenbreite)

### Architektur-Ideen
- Hub-and-Spoke: zentraler FastAPI-Server, 8 Subprozess-Agenten per Message-Queue
- Event-Driven: Agenten kommunizieren ausschließlich über SQLite-WAL-Queue, kein direktes IPC
- Plugin-System für neue Agententypen (nicht nur feste 8)
- Multi-Provider-Router mit Fallback-Kette (DeepSeek → OpenRouter → Ollama)
- Hot-Reload der Agenten-Konfiguration ohne Neustart
- Isolierte Workspaces pro Projekt/User mit eigener DB

### Agenten-Rollen
- 4 System-Agenten: GeneralAG (Orchestrator), SoulAG (Memory/RAG), WatchdogAG (File-Guard), SecurityAG (Code-Scanner)
- 4 Worker-Agenten: CoderAG, WriterAG, ResearcherAG, EditorAG
- GeneralAG delegiert via `@AgentName -> task` Syntax
- SoulAG lernt passiv aus Chat-Verlauf, injiziert Kontext in Worker-Prompts
- WatchdogAG schützt Systemdateien (src/gnom_hub/, config/, .env, run.sh, index.html)
- SecurityAG scannt Write-Inhalte auf gefährliche Patterns (eval, subprocess, rm -rf)

### Feature-Ideen
- Brainstorm-Mode: alle 4 Worker parallel mit staggered API-Calls (1.5s delay)
- Workflow-Engine: Task-Sequenzen mit Dependencies, Stuck-Task-Recovery, DLQ-Kaskade
- SuperGNOM-Baking: kompiliert Agenten-Swarm in standalone-Paket (dist/supergnom_*/)
- AGtuning-Seite: 7-Tab-UI (Prompt, Soul, Blockaden, Tools, Verhalten, Presets, Bake)
- Preset-System: JSON-Konfigurationen pro Agent in config/agents/*.json
- ZWC-Steganografie: unsichtbare Agenten-Signaturen in Dateien und Chat
- TTS-Integration: ElevenLabs + Browser SpeechSynthesis
- Nuke-Button: CRT-Animation + Godzilla-Sound + pkill-9 Neustart
- @@allclear000: 1-Klick-Komplett-Reset (DB, Tokens, Workspace, Chat)

### Datenflüsse
- User → Chat-API → dispatch_mention() → agent_messages-Tabelle → Agent-Polling
- Agent → ask_router() → DeepSeek API → process_actions() → [WRITE:]/[SHELL:]/<SHOWBOX:>
- Agent → POST /api/chat → Antwort im Chat sichtbar
- GeneralAG → process_swarm_mentions() → dispatch_sequence() → Sequenz in Queue
- SoulAG → ask_router() → save_soul_fact() → inject_context() → Worker-Prompt

### Risiken
- Zombie-Prozesse: alte Agent-Prozesse konkurrieren um Queue (mit pkill-9 gelöst)
- Token-Verbrauch: GeneralAG 4096, Worker 8192 Output-Tokens
- Prompt-Länge: 340-440 Wörter vor User-Nachricht (gekürzt von 600+)
- Identitäts-Verlust: Agenten geben sich als andere aus (mit stärkerer Identity-Regel gelöst)
- DLQ-Hänger: dependent Tasks warten ewig auf failed Parent (mit 120s-Timeout + Kaskade gelöst)

---

## 🔍 SCHRITT 2 — ANALYSE & STRUKTURIERUNG

### Die 20%-Ideen mit 80%-Wert (Pareto)

| Idee | Nutzen | Komplexität |
|------|--------|-------------|
| Message-Queue (agent_messages) | Kritisch — alle Agenten kommunizieren darüber | Mittel |
| DeepSeek-Routing mit Fallback | Kritisch — ohne LLM kein Agent | Niedrig |
| Process-Manager (Subprozesse) | Kritisch — Agenten müssen laufen | Mittel |
| Gatekeeper (verify_write/verify_cmd) | Kritisch — Schutz vor gefährlichen Aktionen | Niedrig |
| dispatch_sequence() mit Dependencies | Hoch — sequentielle Workflows | Mittel |
| SoulAG Memory (FAISS + Aging) | Hoch — Lernfähigkeit | Hoch |
| AGtuning-Seite (7 Tabs) | Hoch — Benutzbarkeit | Hoch |
| SuperGNOM-Baking | Mittel — Portabilität | Niedrig |

### Redundantes / Schwaches entfernt
- Auto-Routing-Stages (stage_1-4): ersetzt durch direktes Provider-Routing
- wait_for_decision() 5-Minuten-Blockaden: ersetzt durch Instant-Checks
- enable_confirmations-Gating: entfernt, Checks jetzt immer aktiv
- check_and_wait_breakpoint(): komplett entfernt
- Doppelte Agenten-Starts (Install-Skript-Bug): auf Hub-only umgestellt

### Cluster

**Kernsystem:**
- FastAPI-Server (app.py) + lifespan-Management
- 8 Agent-Subprozesse (process_manager.py)
- SQLite-WAL-Message-Queue (swarm_comms.py)
- LLM-Router (router.py, router_call.py)
- Gatekeeper (gatekeeper.py, path_validator.py)

**Erweiterungen:**
- Workflow-Engine (workflow_engine.py)
- Brainstorm-Mode (brainstorm.py)
- SuperGNOM-Compiler (compiler.py)
- TTS/Audio (audio_tts.py)

**Infrastruktur:**
- Pulse-Janitor (pulse.py)
- Watchdog-Recovery (app.py lifespan)
- Token-Tracking (router_tokens.py)
- Structured-Logging (structured_log.py)

**Security/Safety:**
- Path-Validation (_safe, is_worker_blocked, is_security_block)
- SHELL_BLOCK-Regex + Command-Whitelist
- GeneralAG Shell-Verbot
- ZWC-Steganografie (audit trail)

**UX/Interface:**
- War Room Dashboard (index.html + 9 JS-Module)
- AGtuning-Seite (dashboard.js: showAgentTuning + 7 tuningRender_*-Funktionen)
- Worker-Karten mit Status-Puls (worker_dashboard.js)
- Showbox-System (showbox.js)

---

## 🧾 SCHRITT 3 — VERDICHTUNG (Systemdesign)

### Systemarchitektur

```
┌─────────────────────────────────────────────────┐
│                 GNOM-HUB (FastAPI)               │
│  app.py ← lifespan → DB-Init, Agent-Start,      │
│           Watchdog, Pulse-Janitor, OpenRouter-Updater │
├─────────────────────────────────────────────────┤
│  API-Schicht (27+ Endpoints)                     │
│  /api/chat → chat_legacy.py → dispatch()         │
│  /api/agents/* → agents_status.py                │
│  /api/workflows → workflow_engine.py             │
│  /api/admin/bake → compiler.py                   │
│  /api/admin/clean-all → Nuclear Reset            │
├─────────────────────────────────────────────────┤
│  LLM-Router (router.py)                          │
│  routing.txt → _build_sys() → _resolve()         │
│  DeepSeek R1 (Reasoner) → OpenRouter → Ollama   │
├─────────────────────────────────────────────────┤
│  Message Queue (swarm_comms.py)                   │
│  agent_messages (SQLite WAL)                     │
│  fetch_next_message() → dispatch_sequence()      │
│  parent_msg_id-Dependencies → DLQ-Kaskade        │
├─────────────────────────────────────────────────┤
│  8 Agent-Subprozesse (agent_base.py)              │
│  System: GeneralAG, SoulAG, WatchdogAG, SecurityAG│
│  Worker: CoderAG, WriterAG, ResearcherAG, EditorAG│
└─────────────────────────────────────────────────┘
```

### Datenfluss (User → Agent → Response)

```
1. User: "@CoderAG erstelle hi.txt"
2. chat_legacy.py: _parse() → cmd=chat, tgt=coderag
3. dispatch_mention() → INSERT agent_messages
4. CoderAG-Subprozess: fetch_next_message() → msg
5. Status: busy → Karte pulsiert
6. _build_sys() → build_system_prompt() →
   "⚠️ Du bist CoderAG. NUR CoderAG. [Slider-Config] [SEC: ...]"
7. ask_router() → _resolve() → _call("deepseek", key, msgs)
8. process_actions(r.content) → [WRITE:] → handle_write()
9. seal_content() → ZWC-Signatur → Datei gespeichert
10. POST /api/chat → Antwort sichtbar
11. ack_message() → Status: online → Puls stoppt
```

### Agenten-Konfiguration (config/agents/*.json)

Jeder Agent hat eine JSON-Datei mit:
- identity: "CoderAG"
- role: "coder"
- sliders: {personality: {value:3, levels:{1:"Formal",...}}, ...obedience für System-Agenten}
- tools: []
- security: {system_paths_blocked: true, shell_whitelist: true}

---

## 🚀 SCHRITT 4 — MASTER-PROMPT

---

# MASTER-PROMPT: GNOM-HUB System-Implementierung

Du sollst das GNOM-HUB Multi-Agent-System verstehen, warten oder erweitern.

## SYSTEMKONTEXT

GNOM-HUB ist ein local-first Multi-Agent-Orchestrator mit 8 festen Agenten (4 System + 4 Worker), einer FastAPI-Weboberfläche und SQLite-basierter Message-Queue. LLM-Routing nutzt DeepSeek R1 als Primär-Provider mit OpenRouter/Ollama-Fallback.

## ARCHITEKTUR

```
src/gnom_hub/
├── api/          # FastAPI-Endpoints (app.py, router.py, 27+ endpoints)
├── agents/       # Agent-Logik (agent_base.py, agent_definitions.py, actions/, swarm/)
├── infrastructure/ # LLM-Router (router/), Process-Manager (process/), Monitoring
├── core/         # Config, Security (gatekeeper.py, path_validator.py), Utils (compiler.py, slider_prompt.py)
├── db/           # SQLite-Repositories (WAL-Mode, Connection-Pooling)
├── memory/       # FAISS-Embeddings, Semantic Search (embeddings.py, soul_retrieval.py)
├── soul/         # SoulAG (soul.py: Memory, Fact-Extraction, Context-Injection)
├── frontend/     # Vanilla JS/HTML (index.html, core.js, chat.js, dashboard.js, showbox.js, ...)
└── chat/         # Chat-Services, Brainstorm (brainstorm.py), Commands
```

## KOMPONENTEN

### 1. Message Queue (swarm_comms.py)
- Tabelle: agent_messages (SQLite WAL, id, sender, recipient, payload, status, priority, parent_msg_id, depth, ...)
- dispatch_mention(): parst @Mentions, legt Messages in Queue
- dispatch_sequence(): zerlegt @Agent1->task1\n@Agent2->task2 in Sequenzen mit parent_msg_id-Dependencies
- fetch_next_message(): holt nächste pending-Message, prüft parent_msg_id-Abhängigkeiten
- fail_dependent_messages(): rekursive DLQ-Kaskade bei Parent-Failure
- DEPENDENCY_TIMEOUT=120s: wenn Parent nicht fertig → gesamte Sequenz abgebrochen
- parse_agent_sequence(): Regex für @Agent -> task Format

### 2. Agent-Loop (agent_base.py)
```python
while True:
    heartbeat()
    msg = fetch_next_message(timeout=5s)
    if not msg: sleep(1s); continue
    status = busy
    r = ask_router(text, sys_prompt)
    processed = process_actions(r.content, perms)
    POST /api/chat (processed)
    ack_message(msg_id)
    status = online
```

### 3. LLM-Router (router.py)
- _build_sys(n, sys, agent_name): baut System-Prompt aus slider_prompt.py + agent_definitions.py
- build_system_prompt(agent_name, base): Identität → Base-Prompt → Slider → Obedience → Security
- _resolve(pvd, mdl, kdb, n): erzeugt Fallback-Kette (DeepSeek → OpenRouter → Ollama)
- _call(pvd, mdl, key, msgs): HTTP-Request an LLM-API mit Retry (3x)
- Token-Limits: GeneralAG=4096, SoulAG=2000, Security/Watchdog=1000, Worker=8192
- routing.txt: agent_name = provider | model (z.B. coderag = deepseek | deepseek-v4-pro)

### 4. Security (gatekeeper.py + path_validator.py)
- verify_write(agent, fn, content, wd, perms): _safe() → is_worker_blocked() → is_security_block() → Auto-Approve
- verify_cmd(agent, cmd): Whitelist-Prüfung + System-Pfad-Schutz. GeneralAG: IMMER False
- _safe(wd, f, perms): prüft ob Pfad im Workspace/Project-Root liegt
- is_worker_blocked(): blockt System-Pfade (src/gnom_hub/, config/, .env, run.sh, index.html) — IMMER aktiv
- is_security_block(): Regex-basierte Pattern-Erkennung für gefährlichen Code
- SHELL_BLOCK: Regex für rm -rf /, curl|sh, mkfs, etc.
- Keine Warte-Dialoge mehr (wait_for_decision inaktiv)

### 5. SoulAG (soul.py v3)
- MAX_SOUL_FACTS=50, Fact-Aging (High 30d, Medium 14d, Low 7d)
- Score-basiertes Pruning: Score = Priorität + Nutzung - Alter
- Regex-Block-Liste (BLOCKED_RE): erkennt widersprüchliche Fakten
- Min-Länge 15 Zeichen pro Fakt
- _periodic_cleanup(): läuft max 1x/Stunde, löscht überalterte Fakten
- inject_context(): reichert Worker-Prompts mit top_k relevanten Fakten an
- _pulse_status(): macht SoulAG kurz sichtbar (busy→online für 2s)

### 6. Workflow-Engine (workflow_engine.py)
- create_workflow(name, tasks): erstellt Workflow + Tasks in DB
- start_workflow(id): startet Workflow, evaluiert erste Tasks
- evaluate_workflow(id): prüft bereite Tasks, startet sie, erkennt Stuck/Failed
- handle_task_completion(msg_id, result): idempotenter Callback
- dispatch_by_capability(): routet Tasks via agent_capabilities-Tabelle
- interpolate_template(): {task_id} + {task_id:field.path} Variablen
- Stuck-Task-Timeout: 300s (5 Min)
- Error-Summary pro Task: [ERROR], [STUCK], [DISPATCH]

### 7. Frontend (Vanilla JS, kein Framework)
- index.html: ~2870 Zeilen, CSS+HTML, 9 JS-Module
- core.js: API-Discovery, Toast, Nuke-Button, Agent-Colors, cleanAll()
- chat.js: Chat-Rendering, TTS (cleanTextForTTS ohne Think-Blöcke)
- dashboard.js: showAgentTuning() mit 7 Tabs (Prompt, Soul, Blockaden, Tools, Verhalten, Presets, Bake)
- worker_dashboard.js: renderAgentList(), handleWorkerClick() → showAgentTuning()
- system_dashboard.js: handleAgentClick() → showAgentTuning()
- worker_sidebar.js: selectAgent() — Popup-Detail (wird auf Tuning-Seite migriert)
- showbox.js: Multi-Layer-Präsentationen (bis 7 Slides)
- Cache-Buster: ?v=4 auf allen JS/CSS-Dateien

### 8. Baking (compiler.py)
- bake_supergnom(name, template): erzeugt dist/supergnom_<name>/
- Kopiert: src/, agents/, config/, DB (.gnom-hub/), workspace
- Schreibt: keys.txt (API-Key), run.sh/run.bat, supergnom.yaml, manifest.json (SHA-256 Hashes)
- Integrität: Prompt-Hashes in manifest.json, DB-Cleanup (alte Chats löschen)
- SUPERGNOM_MODE=True in .env deaktiviert SoulAG-Learning

## DATENFLUSS

1. User-Chat → _parse() → dispatch_mention/dispatch_sequence → agent_messages
2. Agent holt Message → ask_router() → _build_sys() → DeepSeek API → process_actions()
3. [WRITE:] → verify_write() → _safe() → seal_content() → Datei
4. [SHELL:] → verify_cmd() → run_in_sandbox()
5. <SHOWBOX:> → save_showbox_presentation()
6. Antwort → POST /api/chat → ack_message()

## GEWÜNSCHTES VERHALTEN

- Agenten arbeiten autonom, keine Bestätigungs-Dialoge
- Core-Files IMMER geschützt (auch ohne enable_confirmations)
- GeneralAG delegiert, führt NIE Shell-Befehle aus
- SoulAG lernt passiv, max 50 Fakten, Aging nach 7-30 Tagen
- workflow_tasks mit Dependencies, 5-Min-Stuck-Timeout, DLQ-Kaskade
- git push ist IMMER blockiert für Agenten (nur User via @@git push)
- @@allclear000: kompletter System-Reset mit Neustart
- Alle Tests: 139/139 müssen grün bleiben

## ERWEITERBARKEIT

- Neue Agenten: AGENT_DEFINITIONS dict erweitern + agents/-Ordner + config/agents/*.json
- Neue Provider: router_config.py + _call()-Mapping + routing.txt
- Neue Tabs: dashboard.js tuningRender_<tab>() + tabs-Array erweitern
- Neue Endpoints: api/endpoints/-Datei + router.py registrieren

## OUTPUT-ERWARTUNG

Bei Änderungen:
1. Code-Änderung mit Dateipfad und Line-Nummer
2. Tests laufen lassen: `python3 -m pytest tests/ -q`
3. Hub neustarten: `pkill -9 -f gnorm_hub; python3 -m gnorm_hub`
4. Verhalten verifizieren: 1 Task senden, Antwort prüfen

## WICHTIGE KONSTANTEN

- MAX_SOUL_FACTS=50, DEPENDENCY_TIMEOUT=120, STUCK_TIMEOUT_S=300
- MAX_DEPTH=8, RETRY_MAX=3, DEDUP_THRESHOLD=0.88
- Token-Limits: GeneralAG=4096, Worker=8192, SoulAG=2000, Security/Watchdog=1000
- Brainstorm-Stagger: 1.5s zwischen Worker-Starts
- Pulse-Janitor: 60s Timeout für feststeckende Agenten
- Port: 3002 (default), Fallback via _free()-Scan
- DB: ~/.gnom-hub/data/gnomhub.db (SQLite WAL)
