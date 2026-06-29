# Gnom-Hub — Vollständige System-Analyse

*Stand: 2026-06-20 · Repository: `/Users/landjunge/gnom-hub` · Version: v1.2.0 → in Entwicklung Richtung v1.3.0*

> **Zweck:** Dieser Bericht ist ein Hand-Over-Dokument für eine andere KI oder einen neuen Mitarbeiter. Er beschreibt den vollständigen Zustand des Gnom-Hub-Codes, der Architektur, der laufenden Arbeiten, der Schmerzpunkte und der nächsten sinnvollen Schritte. Nichts ist weggelassen, was für die Einarbeitung relevant ist.

---

## Inhalt

1. [System-Überblick](#1-system-überblick)
2. [Die 8 Gnomes — Identität, Rollen, Permissions](#2-die-8-gnomes--identität-rollen-permissions)
3. [Prozess-Architektur](#3-prozess-architektur)
4. [Die 5 Kommunikations-Schichten](#4-die-5-kommunikations-schichten)
5. [Datenbank-Schema (komplett)](#5-datenbank-schema-komplett)
6. [LLM-Routing im Detail](#6-llm-routing-im-detail)
7. [Soul-System (Gedächtnis + Beobachter)](#7-soul-system-gedächtnis--beobachter)
8. [Security-Schicht (Gatekeeper)](#8-security-schicht-gatekeeper)
9. [Action-Handler (Tag-Parser)](#9-action-handler-tag-parser)
10. [Frontend (chat.js Architektur)](#10-frontend-chatjs-architektur)
11. [API-Endpoints (Übersicht)](#11-api-endpoints-übersicht)
12. [Test-Coverage](#12-test-coverage)
13. [Tooling & Scripts](#13-tooling--scripts)
14. [Git-Stand: was modifiziert ist, was untracked ist](#14-git-stand-was-modifiziert-ist-was-untracked-ist)
15. [Laufende externe Pläne (Mavis team plan)](#15-laufende-externe-pläne-mavis-team-plan)
16. [Schmerzpunkte (Priorisiert)](#16-schmerzpunkte-priorisiert)
17. [Konkrete Verbesserungs-Roadmap](#17-konkrete-verbesserungs-roadmap)
18. [Quick-Reference: Wo was steht](#18-quick-reference-wo-was-steht)

---

## 1. System-Überblick

**Gnom-Hub** ist ein lokal laufender Multi-Agent-Orchestrator. Die Kernidee: 8 spezialisierte KI-Agenten (genannt "Gnomes") arbeiten zusammen, um User-Aufgaben zu erledigen — koordiniert durch einen "GeneralAG"-Dirigenten, gesteuert von einem "SoulAG"-Souverän, geschützt durch WatchdogAG + SecurityAG.

- **Stack:** FastAPI + SQLite (WAL) + Python 3.10
- **Port:** `3002` (per `GNOM_HUB_PORT` überschreibbar)
- **LLM-Provider:** MiniMax (primär, ein Key deckt Text/Vision/Image/Audio/Video/Music), DeepSeek, OpenRouter Free Models, OpenAI, Anthropic, Gemini, Mistral, Ollama (lokal)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` + FAISS-CPU
- **DB-Pfad:** `~/.gnom-hub/data/gnomhub.db` (Haupt-DB) + 3 separate DBs: `soul_passive.db`, `rules.db`, `coordination.db`
- **Agent-Logs:** `logs/logs_<agent>.txt` (10 MB Rotation: `.1`, `.2`, `.3`)
- **Agent-PIDs:** `~/.gnom-hub/run/<agent>.pid`
- **Workspace:** `gnom_workspace/<active_project>/`
- **Test-Suite:** 534 passed, 2 pre-existing fails (Soul-Memory + Path-Validator), 2 skipped
- **Tests laufen mit:** `PYTHONPATH=src python3.10 -m pytest` (NICHT 3.9 — `python3.9` wirft ImportErrors)
- **Lint:** ruff, line-length 160, Python 3.10
- **GitHub:** https://github.com/landjunge/gnom-hub (public), GitHub Pages: https://landjunge.github.io/gnom-hub/

### User-Modi

Es gibt **drei** Eingabe-Modi vom Frontend (chat.js → `/api/chat` POST):

| Modus | Trigger | Effekt |
|-------|---------|--------|
| **Soul-Chat** | Kein `@`-Mention, kein `@@`-Command | Geht an SoulAG (Souverän), der die Aufgabe analysiert und ggf. delegiert |
| **Direct @Mention** | `@coderag -> Aufgabe` | Geht direkt an den genannten Agenten via `swarm_comms.dispatch_mention` |
| **Command** | `@@clear`, `@@status`, `@@git`, `@@bs`, `@@job`, `@@workflow`, `@@allclear000`, `@@free`, `@@approve_decision`, `@@reject_decision`, `@@bake`, `@@emergency`, `@@diagnose`, `@@confirmations`, `@@spass`, `@@blockade`, `@@help` | Siehe `chat_legacy.py:74` für die volle Liste |
| **Brainstorm** | `@@bs Thema` | `dispatch(topic, target=None)` → GeneralAG analysiert + 4 Worker parallel |
| **Worker-Broadcast** | `@@worker Thema` | `dispatch(topic, target="worker")` → alle 4 Worker parallel |
| **Research** | `@@research Thema` | Skip System-Agents, broadcast to online workers |
| **Workflow** | `@@workflow Aufgabe` | Auto-Derived DAG via `workflow_engine` |

### Sicherheits-Defaults

- `enable_confirmations = false` → alle blockierbaren Aktionen werden **auto-approviert** (Watchdog postet nur "⚡ AUTO-APPROVED"-Hinweis in den Chat)
- Bei `enable_confirmations = true` → `wait_for_decision()` blockiert per `threading.Event` bis User per `@@approve_decision` / `@@reject_decision` (oder `ja`/`nein` im Chat) antwortet, Timeout 5 Min
- `blockade_log`-Tabelle persistiert alle Blockaden
- Prompt-Injection-Check via `injection_validator` läuft **bevor** User-Message in DB landet
- WatchdogAG + SecurityAG haben **read+write+run+godmode** — sie können überall hin (außer SoulAG's exklusive DBs)
- Worker haben **read+write+run+godmode** aber `verify_write`/`verify_cmd` enforced via `path_validator._safe()`

---

## 2. Die 8 Gnomes — Identität, Rollen, Permissions

Quelle: `src/gnom_hub/agents/agent_definitions.py` (218 Zeilen) + `core/agent_names.py` (frozen contract).

### Frozen-Contract (`core/agent_names.py`)

Namen werden auf **kanonische Schreibweise normalisiert**: `generalag`, `general_ag`, `general-ag`, `general` → alle → `generalAG`. Das gilt für **alle 8 Agenten**. Diese Datei ist FROZEN — Änderungen brechen die User-Inputs (User tippt oft `@generalag`, `@general_ag` oder `@GeneralAG`).

### 2.1 SoulAG — Der Souverän 👑 (Cyan)

| Eigenschaft | Wert |
|---|---|
| **Role** | `soul` |
| **Permissions** | `read, godmode, evolve, crawl` |
| **Sys-Prompt-Kern** | "Du bist SoulAG — der SOUVERÄN und der einzige direkte Ansprechpartner des Users. Du denkst laut (TTS). Du hast exklusiven Schreibzugriff auf soul_memory.db, context.db, soul_passive.db, FAISS. Kein anderer Agent darf in diese DBs schreiben. Du kannst direkt Anweisungen an GeneralAG, WatchdogAG und SecurityAG erteilen." |
| **Kommunikation** | **DIREKT mit User**. Andere Agents kommunizieren nicht direkt mit dem User. |
| **Was es tut** | Liest interne Denkprozesse aller Agents (`agent_base.py:179`). Extrahiert Fakten via LLM (nicht pattern-based). Speichert in 3-Layer-Memory. Injiziert relevante Fakten in System-Prompts aller Agents vor jedem Call. Emittiert Direktiven via Zero-Width-Character-Steganographie. |
| **Spawned** | Per `soul_instance` (Singleton in `soul/soul.py:306`). Existiert in **jedem** Agent-Prozess, aber nur SoulAG-Prozess ist "aktiv" — andere laden es nur für `inject_context()`. |

### 2.2 GeneralAG — Der Dirigent 🎯 (Blau)

| Eigenschaft | Wert |
|---|---|
| **Role** | `general` |
| **Permissions** | `read, @job` (TROTZ "keinerlei Schreibrechte" im Sys-Prompt) |
| **Sys-Prompt-Kern** | "Du bist GeneralAG — der DIRIGENT. Du erhältst Aufträge ausschließlich von SoulAG. Du weißt nichts von WatchdogAG und SecurityAG. Du zerlegst die Aufgaben und delegierst sie an die Worker. Du fasst die Ergebnisse zusammen und gibst sie an SoulAG zurück. Du hast keinerlei Schreibrechte." |
| **Capabilities** | `coordination` |
| **Was es tut** | Analysiert User-Aufgabe (via LLM mit `distribute_job()`-System-Prompt), zerlegt in `@Worker -> task` Zeilen, ruft `dispatch()` pro Worker, sammelt Ergebnisse, ruft `run_evolution()` am Ende. |
| **WICHTIG** | Agent-Definitionen widersprechen sich: Definition sagt "keinerlei Schreibrechte" aber `role_tools.py:9` und `swarm_coordinator.py:107` rufen `_eval()` mit `process_actions(ans, ...)` auf, was `verify_write` triggert. Tatsächlich: GeneralAG hat `read, @job` Permissions aber Agent-Definition `de.permissions` ist `["read", "@job"]` — keine `write` Permission. Praxis: GeneralAG **kann nicht schreiben** (gatekeeper blockt). |
| **Workdir** | `swarm_coordinator.py:106` postet sein eigenes Eval-Resultat. |

### 2.3 CoderAG — Der Schmied 🔨 (Orange)

| Eigenschaft | Wert |
|---|---|
| **Role** | `coder` |
| **Permissions** | `read, write, run, godmode` |
| **Capabilities** | `code_generation, code_review, debugging` |
| **LLM-Stage** | `stage_4` (top tier: claude-3-5-sonnet / deepseek-reasoner) |
| **Was es tut** | Schreibt Code, führt Shell aus, debuggt. **NUR in Workspace schreiben** (außer `godmode` löst das). |
| **Auto-Open** | Wenn `index.html` geschrieben wird + `run` perm → `subprocess.Popen(['open', fpath])` öffnet Browser automatisch |
| **Backup** | Existierende Files bekommen `.bak` vor dem Überschreiben (`action_write.py:35`) |

### 2.4 WriterAG — Der Schreiber ✍️ (Grün)

| Eigenschaft | Wert |
|---|---|
| **Role** | `writer` |
| **Permissions** | `read, write, crawl` |
| **Capabilities** | `content_creation, summarization, editing` |
| **LLM-Stage** | `stage_3` (mid tier) |
| **Was es tut** | Texte, Dokumentation, Blog-Posts, Übersetzungen |

### 2.5 ResearcherAG — Der Späher 🔍 (Gelb)

| Eigenschaft | Wert |
|---|---|
| **Role** | `researcher` |
| **Permissions** | `read, crawl, web_search, browser` |
| **Capabilities** | `web_research, fact_checking, summarization` |
| **LLM-Stage** | `stage_4` (reasoning-strong bevorzugt) |
| **Was es tut** | Web-Recherche, Fakten sammeln. KEIN `write` — kann keine Dateien erstellen (nur Crawl + Read). |

### 2.6 EditorAG — Der Prüfer 📋 (Pink)

| Eigenschaft | Wert |
|---|---|
| **Role** | `editor` |
| **Permissions** | `read, write, run, godmode` |
| **Capabilities** | `editing, summarization` |
| **LLM-Stage** | `stage_3` |
| **Was es tut** | Review, Refactoring, QA. Automatischer Review nach CoderAG/WriterAG-Aktionen. |

### 2.7 WatchdogAG — Der Patrouilleur 👁️ (Rot)

| Eigenschaft | Wert |
|---|---|
| **Role** | `watchdog` |
| **Permissions** | `read, run, godmode` |
| **Sys-Prompt-Kern** | "Du überwachst alle Worker auf gefährliche Befehle. Du bist pragmatisch: Du blockst nur bei wirklich gefährlichen Aktionen. Bei Risiken erstellst du eine Showbox an SoulAG mit Approve/Reject Buttons." |
| **Was es tut** | Scannt Code via Pattern-Matching (`_HIGH_RISK_PATTERNS` in `path_validator.py:83`). Schreibt keine Files (nur `read+run+godmode`, kein `write`). Wartet auf `wait_for_decision()` Events für User-Approval. |

### 2.8 SecurityAG — Der Wächter 🛡️ (Lila)

| Eigenschaft | Wert |
|---|---|
| **Role** | `security` |
| **Permissions** | `read, write, run, godmode, desktop, crawl, evolve` |
| **Was es tut** | Code-Scanning, Blockade-Auflösung. Hat **die meisten Permissions** aller Agenten — darf im gesamten Dateisystem schreiben (außer `soul_memory.db, context.db, soul_passive.db`). Scannt Code-Strings via `is_security_block()`. |

### Rollen-Validierung

`agent_repo.py:82-97` `validate_agent_limit_db()`:
- Max **4 System-Agents** (soul, general, watchdog, security)
- Max **4 Worker-Agents** (coder, writer, editor, researcher, plus role='normal')
- Beim Versuch zu überschreiten: `ValidationError` aus `core/exceptions.py`

---

## 3. Prozess-Architektur

Quelle: `infrastructure/process/process_manager.py` (137 Zeilen).

### Startup-Sequenz

`start_background_agents()`:
1. Kill all existing agent processes via PID-Dateien (`_kill_all_agents_by_pid_files()`)
2. Auch Orphan-Kill via cmdline-Scan (`_kill_orphans_by_cmdline()`)
3. Sleep `PROCESS_KILL_SLEEP` Sekunden
4. **DB-Reset**: `UPDATE agents SET status='online', circuit_state='CLOSED', consecutive_failures=0`
5. **Queue-Reset**: `UPDATE agent_messages SET status='done', completed_at=? WHERE status IN ('processing','pending')` (!!! ALLE laufenden Messages werden zu `done`!)
6. Für jeden der 8 Agents: `subprocess.Popen([sys.executable, "-u", "-m", "agents.run_agent", "--name", agent_name], cwd=PROJECT_ROOT, env={PYTHONPATH: src})`
7. PID-Datei schreiben nach `~/.gnom-hub/run/<agent>.pid`
8. Log-File `logs/logs_<agent>.txt` mit 10MB-Rotation (`.1`, `.2`, `.3`)

### Was beim Start passiert (in jedem Agent-Prozess)

`agents/run_agent.py` → `agents/agent_base.py:BaseAgent.__init__` → `BaseAgent.run()`:
1. Endlos-`while not self._req("post", "/api/agents/register", {...})` mit 5s reconnect bei Hub-down
2. `set_agent_status(name, "online")`
3. `_register_capabilities()` löscht `agent_capabilities` für diesen Agent und schreibt die 8 `if/elif`-hardcoded Capabilities neu
4. Loop:
   - Heartbeat POST
   - `fetch_next_message(self.n, DB_PATH, 3.0)` — blockiert bis Message kommt (Threading-Event + DB-Poll)
   - Status auf `busy`
   - Build System-Prompt (siehe unten)
   - `ask_router(text, sys_prompt, agent_name, depth, parent_msg_id)` — EINZIGER LLM-Call-Pfad
   - `process_actions(r.content, agent, perms, False, wd)` — parst Tags, führt Aktionen aus
   - Post to `/api/chat` mit `[💭 Denkprozess]`-Prefix
   - `extract_facts_from_text(thought, self.n)` → SoulAG-Extractor (pattern-based, KEIN LLM)
   - `analyze_agent_thought(self.n, thought)` → Soul-Observer (4 Pattern-Kategorien)
   - `ack_message(msg_id)` → markiert done, weckt Children
   - POST `/api/swarm/complete` → signal_completion für Coordinator/Workflow
   - `record_job()` in coordination.db

### Agent-Prozess-Quellen

Es gibt **zwei** Spawn-Methoden:
- `start_background_agents()`: `python -u -m agents.run_agent --name X`
- `restart_single_agent(X)`: `python -u -m agents.X` (modul-direkt, nicht run_agent)

Inkonsistenz: Beide Pfade führen zu verschiedenen Code-Startpunkten. `agents/run_agent.py` muss `if __name__ == "__main__": ...` haben, das die richtige Agent-Klasse instanziiert.

### Watchdog-Heartbeat-Failover

`/api/swarm/complete` (agents_status.py:547) hat **Circuit-Breaker**:
- 5 consecutive_failures → `circuit_state = 'OPEN'`, `status = 'degraded'`
- Bei nächstem Success (wenn status=degraded): reset auf 0, `circuit_state = 'CLOSED'`, `status = 'online'`

`@@free <agent>` (chat_commands.py:37) killed den Prozess via PID-Datei + restartet via `restart_single_agent()`.

### Process-Isolation

- Jeder Agent hat **eigener Python-Prozess** (kein Threading zwischen Agents)
- Kommunikation: nur via SQLite + HTTP-Loopback (Port 3002) + Threading-Events (in-process only)
- `PYTHONPATH` env wird auf `PROJECT_ROOT/src` gesetzt
- `cwd=PROJECT_ROOT`
- `subprocess.Popen` mit `stdout=open(log_file, "w")` und `stderr=subprocess.STDOUT`

### Sandbox (`infrastructure/process/sandbox.py`, 178 Zeilen)

`run_in_sandbox(cmd, agent, timeout=30)` — wrappt `subprocess.run` mit:
- argv-Parsing (statt `shell=True`)
- Timeout-Kill
- Environment-Isolation (überschreibt PATH, HOME, USER)
- Wird in `action_exec.py:32` aufgerufen für alle `[SHELL:]`-Commands

---

## 4. Die 5 Kommunikations-Schichten

### Layer A — SQLite Message-Bus (Point-to-Point + Sequence)

**Datei:** `agents/swarm/swarm_comms.py` (796 Zeilen) + `db/message_queue.py` (Schema, 54 Zeilen).

**Schema `agent_messages`:**
```
id INTEGER PK
sender TEXT
recipient TEXT
payload TEXT (JSON)
priority INTEGER (0=critical, 5=normal, 7=low, 10)
status TEXT ('pending'|'processing'|'done'|'dead_letter')
retry_count INTEGER
created_at REAL
deliver_after REAL (für Backoff)
context_id TEXT
depth INTEGER (Rekursionstiefe)
parent_msg_id INTEGER (Dependency)
processing_since REAL
completed_at REAL
```

**Kern-API:**

| Funktion | Zweck | Wichtige Details |
|----------|-------|-----------------|
| `dispatch_mention(sender, text, ctx, depth=0, parent_msg_id=None, priority=None)` | Parst `@Agent` aus Text, schreibt 1 Zeile pro Mention | `MAX_DEPTH=15`, strippt `<think>…` vorab, dedupliziert Mentions, kritische Messages bypassen `can_accept_message` |
| `dispatch_sequence(sender, text, ctx, depth=0)` | Parst `@A -> task` Zeilen, baut Lineare Kette via `parent_msg_id` | `MAX_DEPTH=15`, kaskadiert nicht, schreibt `prev_msg_id` als parent |
| `dispatch_by_capability(sender, task_type, text, ctx, ...)` | Findet besten Agent via 3-Stufen-Routing, schreibt 1 Zeile | Wird von `workflow_engine` genutzt |
| `fetch_next_message(agent, db_path, timeout=30.0)` | Blockiert bis Message da | Prüft `parent_msg_id`-Tree, kaskadiert Parent-DLQ→Child-DLQ, timeoutet nach 120s, nutzt `threading.Event` für Wakeup |
| `ack_message(msg_id, db_path)` | `status='done'`, weckt Children via `notify_agent()` | Index-Only-Lookup für Children-Check, single COMMIT |
| `nack_message(msg_id, db_path, reason)` | Exponential-Backoff, `RETRY_MAX=3`, danach DLQ + Kaskade | `RETRY_BACKOFF_BASE=3.0` (war 5.0) |
| `recover_stuck_messages(db_path, timeout=300)` | Findet blockierte Messages, retry oder DLQ | **Wird von Watchdog periodisch aufgerufen — wo? NICHT GEFUNDEN IM CODE. Vermutlich geplant, aber nicht implementiert oder in einer Route versteckt.** |
| `fail_dependent_messages(msg_id, reason, conn)` | Rekursiver CTE → markiert ganze Dep-Tree als DLQ | Effizient: 1 Query statt N |
| `notify_agent(agent)` | Setzt Threading-Event | **Nur in-process wirksam!** Cross-process fehlt |
| `get_agent_event(agent)` | Lazy-creates Event | |

**Konstanten (oben in swarm_comms.py):**
```
MAX_DEPTH = 15
MAX_CONCURRENT = 8
RETRY_MAX = 3
RETRY_BACKOFF_BASE = 3.0
MAX_QUEUE_DEPTH = 100
DEPENDENCY_TIMEOUT = 120.0
DEPENDENCY_POLL_S = 1.0
PRIORITY_MAPPING = {"critical":1, "high":3, "normal":5, "low":7}
```

**Routing-Auswahl (`find_best_agent_for_task`, 3-stufig):**
1. `coordination.db.worker_stats` — Agenten mit ≥2 Jobs in letzten 7 Tagen, sortiert nach `success_rate DESC, total_jobs DESC`, Filter <40% bei ≥5 Jobs
2. `agent_capabilities` JOIN `agents WHERE status IN ('online','busy','running')` ORDER BY queue_depth ASC, confidence DESC
3. Keyword-Heuristik für `coderag/writerag/researcherag/editorag` aus Task-Text

**Mention-Parsing-Regex:**
```python
parse_agent_sequence: r'@(\w+)\s*[-–→>]+\s*(.+)'
dispatch_mention: r'@(\w+)'
```

**Strip-Logik:** `<think>…</think>` wird via `re.sub(r'<think>[\s\S]*?</think>', '', text)` VOR dem Mention-Parsing entfernt. Verhindert, dass interne Gedanken Dispatches auslösen.

### Layer B — Workflow Engine (DAG-Orchestration)

**Datei:** `agents/swarm/workflow_engine.py` (466 Zeilen).

Höhere Abstraktion über Layer A. Tasks werden in `workflows` + `workflow_tasks` (SQLite) als DAG mit `depends_on` gespeichert.

**Schema `workflows`:**
- `id TEXT PK` (UUID)
- `name TEXT`
- `status TEXT` ('pending'|'running'|'completed'|'failed')
- `created_at REAL`, `completed_at REAL`

**Schema `workflow_tasks`:**
- `workflow_id, task_id` (Composite PK)
- `capability TEXT`
- `input_template TEXT` (mit `{var}`-Substitution)
- `depends_on TEXT` (JSON-Array)
- `status TEXT` ('pending'|'running'|'completed'|'failed')
- `msg_id INTEGER` (Link zu `agent_messages.id`)
- `result_json TEXT` (gespeichertes Result)
- `error_summary TEXT`
- `retry_count INTEGER`, `retry_deliver_after REAL`

**Lebenszyklus:**
1. `create_workflow(name, tasks)` → UUID
2. `start_workflow(wf_id)` → status='running' + `evaluate_workflow()`
3. `evaluate_workflow(wf_id)` läuft rekursiv:
   - **Stuck-Detection**: `processing_since` älter als `WORKFLOW_STUCK_TIMEOUT` → Task FAILED
   - **Failed-Detection**: ein Task failed → WF-Abbruch, `_record_wf_result` schreibt in coordination.db
   - **Completion-Detection**: alle Tasks completed → status='completed'
   - **Ready-Tasks**: alle Deps completed → `dispatch_by_capability()` für jeden
4. `handle_task_completion(msg_id, result)` ist der Callback (idempotent!) — wird von `/api/swarm/complete` aufgerufen → schreibt Task-Result + triggert `evaluate_workflow()`
5. **Template-Interpolation:** `{task_id}` = kompletter Output-Text, `{task_id:content}` = content-Feld, `{task_id:status:error}`, `{task_id:data.x.y}` = Nested-Lookup. Unersetzte Platzhalter bleiben erhalten (graceful).

**Konstanten** (`core/constants.py`): `WORKFLOW_MAX_RETRIES`, `WORKFLOW_RETRY_DELAY`, `WORKFLOW_STUCK_TIMEOUT`.

**Recovery:** `recover_stuck_workflows()` wird vom Watchdog periodisch aufgerufen (vermutlich — Implementation der periodischen Invocation nicht eindeutig im Code).

**Eintritt:** Via `chat_legacy.handle_workflow()` (heuristic Task-Derivation) oder direkt via `workflow_engine.create_workflow()`.

### Layer C — Team Coordinator (Event-Based Group Workflow)

**Datei:** `agents/swarm/swarm_coordinator.py` (147 Zeilen).

Iteratives Group-Workflow-Pattern. **Kein DB-Poll** — nutzt in-process `threading.Event`.

**Ablauf (pro Runde, max 4 Runden):**
1. `WorkerCompletionTracker(workers, timeout=180.0)` — In-Process `threading.Event`-basiert
2. `register_tracker(job_id, tracker)` in globale Registry
3. `dispatch()` ruft `dispatch_mention` für jeden Worker
4. Agents rufen beim Finish **`/api/swarm/complete`** auf → ruft `signal_completion(ctx_id, agent, result)` → Tracker markiert done
5. Tracker.wait() — `threading.Event.wait(180.0)` — blockiert bis alle done oder Timeout
6. Wenn alle done: `_eval()` ruft LLM mit GeneralAG-Prompt "Fasse zusammen + nächste @Agent-Zuweisungen" → parst → nächste Runde mit neuem Tracker
7. Nach max 4 Runden: `run_evolution()` + Post "Workflow beendet"

**Tracker-Registry:** Globale `_trackers: Dict[str, WorkerCompletionTracker]` mit `_registry_lock`. Cleanup am Ende jedes Tracker-Lifetimes via `cleanup_tracker()`.

**Eintritt:** `start_coordinator(task, workers, job_id)` — startet als Daemon-Thread. Aufgerufen von `chat_commands_handlers.handle_job()` und `handle_allclear`.

**Unterschied zu Layer B:** Coordinator ist für **iterative User-geführte** Team-Workflows. Workflow-Engine ist für **deklarierte DAGs**.

### Layer D — Chat-Stream (User ↔ System)

**Dateien:** `chat/chat_commands.py`, `chat/chat_commands_handlers.py`, `chat/chat_clear.py`, `api/endpoints/chat_legacy.py`.

**`_post_chat(sender, content)`** (`chat_commands_handlers.py:9`) ist die **EINZIGE** Senke für User-sichtbare Nachrichten → schreibt in `chat`-Tabelle mit `msg_type="role_response"` (oder "chat" / "brainstorm" / "role").

**Eingang:** User tippt im Frontend → `chat.js:375 sendChat()` → `api('POST', '/chat', { content: msg })` → `chat_legacy.post_chat()`.

**Verarbeitung in `post_chat()`:**
1. Wenn `sender=user`: `injection_validator.validate_input(content)` — blockt prompt-injection-Muster
2. Wenn `sender=user` und `@merken` im Text: speichere als `soul_fact` mit `priority=high`
3. `soul_instance.on_message(content, sender)` — triggert Soul-Fakt-Extraktion
4. Wenn `sender=user` und Text ist "ja"/"nein"/etc.: prüfe `pending_decisions` und triggere `handle_approve_decision` / `handle_reject_decision`
5. `_parse(content)` zerlegt in `(q, target, cmd)`:
   - Spezielle Commands (`bs`, `clear`, `status`, etc.) → CMDS-Dict
   - `@target` → Agenten-Name
   - Sonst: `cmd=None, tgt=None` → geht an SoulAG
6. `<SHOWBOX>`-Tags werden aus Agent-Outputs **gefiltert**: in `showbox_presentations` Tabelle gespeichert, im Chat durch `[→ Showbox: Name]` ersetzt
7. `add_chat_message(...)` schreibt in DB
8. Wenn `cmd` in CMDS: return CMDS[cmd](q)
9. Wenn `cmd=="research"`: dispatch to all online workers
10. Wenn kein `cmd` und kein `tgt`: dispatch to SoulAG
11. Wenn `cmd=="bs"`: dispatch via `handle_bs` (Brainstorm-Mode)

**SHOWBOX-Enforcement** (`chat_legacy.py:136`): `enforce_agent_layer()` — Agenten dürfen nicht in `<SHOWBOX:user>` schreiben (Layer-3 reserved for User).

**Architektur-Filter** (`chat_legacy.py:139-163`): Agent-Outputs mit `<SHOWBOX>…</SHOWBOX>` werden in Showbox-Tabelle extrahiert, im Chat-Stream durch Marker ersetzt. Chat bleibt sauber.

### Layer E — Soul-System (Memory + Beobachter)

Siehe [Sektion 7](#7-soul-system-gedächtnis--beobachter) für Details. Wirkt als **Hintergrund-Layer** über allen anderen: extrahiert Fakten, beobachtet Denkprozesse, injiziert Kontext.

---

## 5. Datenbank-Schema (komplett)

Quelle: `db/schema.py` (371 Zeilen, `SCHEMA_SQL` Konstante).

### Hauptdatenbank `gnomhub.db`

| Tabelle | Zweck | Wichtige Spalten |
|---------|-------|------------------|
| `state` | KV-Store für LLM-Keys, Routing, Presets, Active-Project | `key PRIMARY, value` |
| `agents` | 8 Agenten-Definitionen | `name PK, id, port, description, status, capabilities, role, active_job, last_seen, circuit_state, consecutive_failures` |
| `chat` | User-/Agent-Chat-Verlauf | `id, project, sender, agent_id, msg_type, content, timestamp, metadata` (JSON) |
| `soul_memory` | Aktive Fakten | `key UNIQUE, value, timestamp, priority, agent` |
| `audit_log` | Generisches Audit-Log | `id, timestamp, agent, event_type, details, trace_id` |
| `blockade_log` | Alle blockierten Aktionen | `id, timestamp, agent_name, blocked_by, action_type, detail, reason, content_snippet, status` |
| `prompt_versions` | Evolution-Prompt-Versionen | `id, agent, base_prompt, modifications, performance_score, created_at, feedback_count, is_active, parent_id` |
| `capabilities` | Granted Capabilities (TTL-basiert) | `id, agent_name, capability_type, resource, granted_by, expires_at, is_active` |
| `showbox_presentations` | Gespeicherte Showbox-Slides | `id, name UNIQUE, slides (JSON), sender, updated_at, buttons` |
| `explainable_outputs` | LLM-Antwort-Wraps (für UI) | `id, agent, task, data, timestamp` |
| `graceful_degradation_failures` | Fallback-Tracking | `id, agent, failure_type, fallback_agent, task, timestamp` |
| `token_budget_logs` | Token-Tracking pro Operation | `operation_id, agent, operation_type, input_tokens, output_tokens, model, cost, timestamp` |
| `token_budget_alerts` | Budget-Warnungen | `id, message, timestamp, acknowledged` |
| `agent_messages` | **Kern: Inter-Agent Queue** | siehe Layer A |
| `swarm_callbacks` | Idempotenz für `/api/swarm/complete` | `idempotency_key PK, context_id, agent_name, result_json, received_at, http_status` |
| `agent_capabilities` | Agent→Capability-Mapping | `(agent_name, capability) PK, confidence` |
| `workflows` | **Layer B: Workflows** | `id PK, name, status, created_at, completed_at` |
| `workflow_tasks` | **Layer B: Tasks** | `(workflow_id, task_id) PK, capability, input_template, depends_on, status, msg_id, result_json, error_summary, retry_count, retry_deliver_after` |

**Indizes:**
- `idx_aq_recipient_status` auf `agent_messages(recipient, status, deliver_after)` — KRITISCH für Hot-Path
- `idx_aq_context` auf `agent_messages(context_id, depth)`
- `idx_cb_context` auf `swarm_callbacks(context_id)`
- `idx_chat_project_ts` auf `chat(project, timestamp DESC)`
- `idx_chat_project_agent` auf `chat(project, agent_id)`
- `idx_agent_event` auf `audit_log(agent, event_type)`
- `idx_soul_memory_key`, `idx_soul_memory_timestamp`
- `idx_timestamp` auf `audit_log(timestamp DESC)`

**Connection-Layer (`db/connection.py`):**
- PRAGMA `journal_mode=WAL` — WAL-Mode für Concurrent-Reads
- PRAGMA `synchronous=NORMAL` — Balance zwischen Safety und Speed
- PRAGMA `cache_size=-20000` — ~20MB Cache
- PRAGMA `foreign_keys=ON`
- `timeout=15.0` für Connection-Acquire
- `sqlite3.Row` als row_factory

**Migrations:** In `init_database()` werden ALTER TABLE für neue Spalten versucht; `OperationalError` abgefangen → idempotent. Bisherige Migrationen: `processing_since`, `completed_at`, `circuit_state`, `consecutive_failures`, `parent_msg_id`, `buttons`, `workflows` (Phase 5), `workflow_tasks` (Phase 5), `retry_count`, `retry_deliver_after`, `error_summary`.

### Separate Datenbanken

| Datei | Inhalt |
|-------|--------|
| `soul_passive.db` | Tabelle `soul_archive` — Langzeit-Archiv, nur Lesezugriff für Agenten, SoulAG schreibt |
| `rules.db` | Tabelle `rules` — User-Regeln (allow_path, block_path, allow_cmd, block_cmd, user_decision) für WatchdogAG + SecurityAG. Bootstrap mit Default-Regeln (siehe `memory_layers.py:325-340`) |
| `coordination.db` | Tabellen `worker_stats` (Agent-Erfolgsraten), `job_history` (Job-Records), `context` (Session-Context) — für GeneralAG-Routing |

**Multi-DB-Architektur:** SoulAG's exklusive DBs sind technisch separate SQLite-Dateien. Andere Agenten können `soul_passive.db` lesen (keyword-search), `rules.db` lesen (WatchdogAG/SecurityAG), `coordination.db` lesen (GeneralAG-Routing-Entscheidungen).

---

## 6. LLM-Routing im Detail

Quelle: `infrastructure/router/router.py` (272 Zeilen), `router_call.py` (HTTP-Calls), `router_stage.py` (SmartRouter), `router_config.py` (Keys), `llm_orchestrator.py` (52 Zeilen, simpler Wrapper).

### Routing-Konfiguration

- **`config/routing.txt`** — Frozen-ish: `agent_name = provider | model` Format, geladen via `core/utils/routing_override.py:load_routing_from_txt()`. Aktuell: alle 8 Agents auf `minimax | MiniMax-M3`.
- **`state.llm_agents`** — Dynamische DB-Overrides: `{"generalag": {"provider": "auto", "model": "stage_3"}}`
- **Default:** `{"provider": "auto", "model": "stage_3"}` wenn nichts gesetzt ist

### `ask_router(p, sys, agent_name, depth, parent_msg_id)` (router.py:211)

Die **einzige** Routing-Funktion. Alle LLM-Calls laufen hier durch.

**Schritte:**
1. Setze Agent-Status `busy` (in `try/finally` → reset auf `old_status`)
2. `_build_sys(n, sys, agent_name)` — Build System-Prompt mit:
   - `build_system_prompt(identity, name, soul_facts, tools_block, security_block)` aus `core/utils/slider_prompt.py`
   - Obedience-Slider-Instructions (Level 1-5: blind / strong / balanced / cautious / autonomous)
   - Behavioral-Slider-Instructions (Personality, Response-Style, Risk-Tolerance)
   - Custom-Prompt-Suffix
   - Active-Preset-Loading via `get_preset_prompt(active_preset, n)`
   - Evolution-Rules via `get_active_version(agent_name).modifications` ODER DB-Query `evolution_{agent_name}_%`
3. Load `llm_agents` config (state-DB), fall-back zu `routing.txt`, fall-back zu `{provider: "auto", model: "stage_3"}`
4. `_resolve(pvd, mdl, kdb, n)` baut Kandidatenliste:
   - Wenn `provider=="minimax"`: MiniMax M3 → OpenRouter Free → Ollama llama3
   - Wenn `provider=="auto"`: SmartRouter.resolve_stage_candidates(mdl, kdb, n)
   - Wenn `provider=="openrouter"`: working models sortiert, dann konfiguriertes Model
   - Sonst: provider → OpenRouter free → Ollama fallback
5. Für jeden Kandidaten: `_try_keys(cp, cm, kdb, msgs, agent_name)` oder `_try("lokal", ...)` für Ollama
6. Bei Erfolg: 
   - `record_agent_request(n, lat, True)` für Monitoring
   - `logger.log_event("llm_call", provider=cp, model=cm, latency_ms=lat, status="success")`
   - Falls fallback benutzt: `cfg._source` und `cfg[provider/model]` updaten für nächstes Mal
   - **`process_swarm_mentions(agent_name, ans, depth, parent_msg_id)`** — NACH JEDEM erfolgreichen LLM-Call werden `@Mentions` aus der Antwort geparst und dispatcht (lokaler Import, um Zirkular-Import zu vermeiden)
   - `wrap_response(ans, ...)` → ExplainableOutput
7. Bei Failure aller Kandidaten: `wrap_error("[ROUTER-FEHLER] Alle Gleise offline.")`

### SmartRouter (`router_stage.py`, 437 Zeilen)

**4 Stages** (Curated Model-Listen):
- `stage_4` (premium): claude-3-5-sonnet, claude-sonnet-4, claude-3-opus, gpt-4o, o1, deepseek-reasoner, deepseek-chat, gemini-1.5-pro, gemini-2.0-flash, gemini-2.5-pro
- `stage_3` (mid): deepseek-chat, gemini-1.5-flash, gpt-4o-mini, mistral-large-latest, codestral-latest, llama-3.1-8b-instruct
- `stage_2` (free): qwen/qwen3-coder:free, llama-3.3-70b:free, hermes-3-llama-3.1-405b:free, gemma-3-27b-it:free, gpt-oss-120b:free, trinity-large-thinking:free, llama-3.2-3b:free
- `stage_1` (local Ollama): qwen2.5-coder:7b, llama3, mistral, phi3, gemma2, codellama

**Role→Stage-Mapping:**
```python
ROLE_PREFERENCE = {
    "coder": "stage_4",
    "security": "stage_4",
    "researcher": "stage_4",
    "writer": "stage_3",
    "editor": "stage_3",
    "soul": "stage_3",
    "normal": "stage_3",
    "brainstorm": "stage_2",
    "default": "stage_3",
}
```

**Role-Keywords (Substring-Match):**
```python
_ROLE_KEYWORDS = {
    "coder":      ("qwen", "coder", "codestral", "deepseek-coder"),
    "researcher": ("reasoning", "thinking", "trinity", "deepseek-r1"),
    "writer":     ("llama", "gemma", "mistral"),
    "editor":     ("llama", "gemma", "mistral"),
    "soul":       ("llama", "gemma", "liquid"),
}
```

**Stage-Candidate-Resolution:**
- `resolve_stage_candidates(stage, kdb, agent_name)`:
  1. `resolve_role_from_name(name)` — Substring-Match auf agent_name
  2. `get_stage_options(stage, role)` — Liste aller (provider, model)-Tupel
  3. Filter: nur Kandidaten mit validiertem Key
  4. Fallback: `("lokal", "llama3")`

**`get_best_specific_assignment()`** — gibt basierend auf vorhandenen Keys + Role das beste (provider, model)-Paar zurück. **MiniMax hat höchste Priorität** wenn verfügbar.

### MiniMax-Routing (besonderer Pfad in `router.py:179-193`)

```python
elif pvd == "minimax":
    # Reihenfolge: MiniMax M3 → OpenRouter Free Models → Ollama (lokal)
    candidates.append(("minimax", mdl))
    # OpenRouter Fallback mit Free Models
    ...
    # Ollama als letzter Notnagel
    candidates.append(("lokal", "llama3"))
```

### Provider-Registry

`src/gnom_hub/core/provider_registry.py` (neu, 2026-06) — 44 distinct providers mit caps. Konsumiert von SmartRouter und Key-Verifier.

### Key-Verifizierung

`router_config.py` (DS_KEY, OR_KEY) — Hardcoded env-var Lookups als Fallback.

### `_try_keys` Rotation

Bei `429/401/5xx` wird `RetryableCallError` raised → rotiert zum nächsten Key im Pool (nicht der erste 429 kills den Call). Implementation in `router_call.py`.

### LLM-Config UI

`showLLMConfig()` in `frontend/index.html`/JS — Cards für Web Search + TTS Provider, separate von Chat-Provider. Per-Provider/Per-Model/Per-Key-Inputs mit Status-Badges.

### TTS-Routing

`core/utils/audio_tts.py` — liest `llm_service_tts` und routet zu MiniMax / OpenAI-TTS / ElevenLabs / Web Speech. Cache ist provider-scoped.

---

## 7. Soul-System (Gedächtnis + Beobachter)

Quelle: `soul/` (8 Files, 2016 LOC total).

### 7.1 Memory-Layer-System (`soul/memory_layers.py`, 737 Zeilen)

**3-Schichten-Architektur:**

| Layer | Speicherort | Zweck | Zugriff |
|-------|-------------|-------|---------|
| **Layer 1** | In-Memory `SoulCache` (Top-50 Fakten nach Score) | Hot-Path, <1ms Lookup | Alle Agenten via `inject_context()` |
| **Layer 2** | SQLite `soul_memory` (Haupt-DB) | Aktive Fakten | SoulAG schreibt, alle lesen |
| **Layer 3** | Separate `soul_passive.db` `soul_archive` | Langzeit-Archiv, nur Read | Alle lesen, SoulAG schreibt |

**Plus 2 Spezial-DBs:**
- `rules.db` (`RulesDB`) — für WatchdogAG/SecurityAG. Cached für 60s, `check()`, `add_rule()`, `get_rules_for_agent()`. Default-Bootstrap in `_bootstrap_rules()` (memory_layers.py:325).
- `coordination.db` (`CoordinationDB`) — für GeneralAG. `worker_stats` Tabelle, `record_job()`, `get_worker_summary()`.

**SoulCache (`SoulCache`):**
- `MAX_SIZE = 50`
- `_score(priority, timestamp)`: `{"high":30, "medium":15, "low":5}` - `age_days * 0.5`
- `warm_up()` beim Start: lädt Top-100 aus DB, scored, behält Top-50
- `put()`: ersetzt niedrigsten Score wenn voll
- `get_top(n, agent)`: sortiert nach Score, filtert nach Agent (oder "all", "system", "soulag")

**SoulAG-Extractor (`soul/soul.py:_ex`):**
- LLM-basierte Fakt-Extraktion (NICHT pattern-based, im Gegensatz zu `extract_facts_from_text` in `zwc_soul.py`)
- Sampling: User immer, Agent 65% (war 80%)
- Deduplizierung via FAISS `has_similar(threshold=0.85)` (war 0.88)
- Blocklist-Patterns (BLOCKED_RE): `nicht schreib`, `nur showbox`, `vorher frag`, `blockade`, `darf nicht`, etc.
- Speichert in alle 3 Layer via `save_fact_all_layers()`
- Periodischer Cleanup: alle 1h, Aging (high=30d, med=14d, low=7d), dann Pruning auf max 100
- Silent-Rounds-Tracker: postet "👀 Nichts Neues gelernt" nach 5 stillen Runden
- Status: `_pulse_status()` setzt SoulAG auf `busy` während Extraktion (via HTTP), reset nach 2s

**SoulAG-Injection (`soul/soul.py:inject_context`):**
- `top_k` je nach `memory_strength`-Slider: 1→2, 2→4, 3→6, 4→8, 5→12
- Plus IMMER die Top-3 `agent='User' AND priority='high'` Facts vorne
- Format im System-Prompt:
  ```
  === RELEVANTE ERINNERUNGEN ===
  - fact_key: fact_value
  ...
  === ERWÄHNTE AGENTEN ===
  [Ref: @CoderAG - Der Schmied]
  ...
  ```
- `_injections` Dict zählt, wie oft jeder Fakt welchem Agenten injiziert wurde (für `usage_bonus` im Scoring)

**Soul-Passive-DB (`PassiveDB`):**
- Tabelle `soul_archive` (key UNIQUE, value, priority, agent, archived_at, source)
- `archive(key, value, priority, agent)` — nur SoulAG darf
- `search(keywords, limit=5)` — Substring-Match auf ersten 3 Keywords, dedupliziert
- Wird nur als Fallback abgefragt wenn Layer 1+2 leer

**Rules-DB (`RulesDB`):**
- Tabelle `rules` (rule_type, pattern, agent, reason, created_by, created_at, expires_at, active)
- `_cache` mit 60s TTL
- `check(rule_type, pattern, agent)` — Substring-Match
- `add_rule()` — invalidate cache
- Default-Regeln: `block_path src/gnom_hub/`, `block_path config/`, `block_path .env`, `allow_path gnom_workspace/`, `allow_cmd pytest`, `block_cmd rm -rf /`, `block_cmd curl|bash`, etc.

**Coordination-DB (`CoordinationDB`):**
- `worker_stats` (agent_name, total_jobs, successful_jobs, failed_jobs, last_updated)
- `record_job(worker, task_summary, result, duration_s, context_id=None, notes="")` — Speichert in `job_history` und updated `worker_stats`
- `get_worker_summary()` — Text-Format für GeneralAG's System-Prompt
- `get_summary_for_generalag()` — Top offene Contexts für GeneralAG

### 7.2 Soul-Observer (`soul/soul_observer.py`, 198 Zeilen)

**Aufgerufen nach JEDER Agent-Antwort** aus `agent_base.py:198`.

**4 Pattern-Kategorien** (alle Regex-basiert, KEIN LLM):

1. **Injection-Patterns** (KRITISCH):
   - `ignoriere alle ... regeln/anweisungen/richtlinien`
   - `vergiss alle ... regeln/anweisungen`
   - `du bist jetzt ...`
   - `system: ... neue rolle/identität/aufgabe`
   - `schicke ... an https?://`
   - `api[_-]?key|password|passwort|secret :...`
   - `send to ...@...`
   - `exfiltrat|datenleck|leak the`

2. **Tool-Mismatch-Patterns**:
   - `kann nicht schreiben/lesen/zugreifen/ausführen`
   - `tool fehlt|fehlende tool|missing tool`
   - `gatekeeper blockiert/verweigert/lehnt ab`
   - `keine berechtigung/permission/access/rechte/tools`
   - `screencapture|video_record|ffmpeg ... nicht verfügbar`

3. **Failure-Loop-Patterns**:
   - `wieder/schon wieder/erneut/gleiche/immer wieder fehler/problem/error/gescheitert`
   - `im kreis/kreislauf/endlosschleife/schleife`
   - `3/4/5 mal|mehrfach|oftmals versucht/probiert/gescheitert`

4. **Stuck-Patterns**:
   - `weiß nicht mehr/weiter/was/wie`
   - `komme nicht weiter|kein fortschritt`
   - `brauche/benötige hilfe/unterstützung/rückmeldung`
   - `frage|unclear|unklar|missverständnis|verwirrt`

**Alert-Thresholding:** Tool-Mismatch-Count ≥ 2 in letzten 5 Thoughts, Failure-Count ≥ 2, Stuck bei ≥ 3 Thoughts History.

**Cooldown:** Gleicher Alert max alle 5 Min (`_ALERT_COOLDOWN_S = 300`).

**Alert-Dispatch:** Post in `chat` als "🧠 SoulAG-Beobachtung zu @AgentName: ..." mit Counts als Details.

### 7.3 ZWC-Soul (`soul/zwc_soul.py`, 181 Zeilen) — Zero-Width-Character Steganography

**Verwendet U+200B (Zero-Width-Space) und U+200C (Zero-Width-Non-Joiner)** zur unsichtbaren Kodierung von Metadaten im Chat.

- `soul_to_bits(d)` → base64-Encode + JSON + Bits
- `bits_to_zwc(bits)` → jeder Bit wird 3× wiederholt (Triple-Redundancy für ECC)
- `correct_ecc(zb)` → Majority-Vote pro 3-Char-Group
- `decode_soul(text)` → extract + ECC + base64-decode + JSON
- `add_agent_metadata(agent, msg, extra)` → hängt ZWC-kodierte {agent, ts, extra} an msg
- `add_directive(target, msg, ttl)` → ZWC-Direktive
- `get_directives(text)` → extrahiert alle Direktiven (TTL-basiert, default 3600s)

**Verwendung:** `action_write.py:51` — nach jedem File-Write wird ZWC-metadata an die Success-Message gehängt. Andere Agenten können via `decode_soul` die Identität verifizieren.

**WICHTIG:** Direktiven sind unsichtbar — User sieht sie nicht, aber Agents parsen sie. Security-Risiko: ein Agent mit `read`-Zugriff auf Chat kann ZWC-Direktiven lesen.

### 7.4 Thought-Extractor (`zwc_soul.py:extract_facts_from_text`)

**Pattern-basierte** Extraktion (IM GEGENSATZ zum LLM-basierten `_ex()` in soul.py).

**Patterns:** "ich merke/lern[ae]/erkenne/verstehe...", "die beste Strategie...", "ich sollte/man sollte/wir sollten...", "pattern/regel/prinzip:...", "der user mag/will/braucht...".

**Limits:** Max 5 Fakten pro Denkprozess. Min Length 15, max 300. Save als `thought_kind_<uuid8>` mit `agent="SoulAG"`.

**WICHTIG:** Wird im `agent_base.py:179` Loop JEDER Agent-Antwort aufgerufen → 1 LLM-Call-Ersparnis im Hot-Path.

### 7.5 Soul-Actions (`soul/soul_actions.py`, 229 Zeilen)

Soul-spezifische Aktionen: `soul_status`, `soul_forget`, `soul_search`, `soul_inject`, etc.

### 7.6 Soul-Initializer (`soul/soul_initializer.py`, 141 Zeilen)

Bootstrap-Logik für 8 Soul-Definitionen (Lade-Reihenfolge, Default-Facts, etc.).

### 7.7 Agent-Voices (`soul/agent_voices.py`, 149 Zeilen)

TTS-Stimmen-Zuweisung pro Agent. Aktuell: macOS `say` mit `Anna` (deutsch) als Default. MiniMax-TTS wird parallel unterstützt.

---

## 8. Security-Schicht (Gatekeeper)

Quelle: `core/security/gatekeeper.py` (504 Zeilen), `core/security/path_validator.py` (139 Zeilen).

### Drei-Schichten-Sicherheitsmodell

**Layer 1 — User-Regeln** (`blockade_rules` in state-Tabelle):
- Rule-Types: `block_always`, `whitelist`, `allow_once`, `allow_agent`
- `check_blockade_rules(agent, action_type, detail)` — konsumiert `allow_once`-Regeln
- `add_blockade_rule()` / `remove_blockade_rule()`
- Default: leer (keine Regeln)

**Layer 2 — System-Pfade** (`path_validator.SYSTEM_PATHS`):
- Hardcoded: `/etc`, `/usr`, `/bin`, `/sbin`, `/var`, `/boot`, `/proc`, `/sys`, `/lib`, `/private/etc`, `/private/var`
- `is_system_path(path_str)` — realpath-basiert, symlink-sicher

**Layer 3 — Pattern-Matching** (path_validator._HIGH_RISK_PATTERNS):
```python
_HIGH_RISK_PATTERNS = (
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bos\.system\s*\(",
    r"\bsubprocess\.[A-Za-z_]+\(.*shell\s*=\s*True",
    r"curl[^|]*\|\s*(ba)?sh\b",
    r"wget[^|]*\|\s*(ba)?sh\b",
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\bmkfs\b",
    r"\bdd\s+if\s*=",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # Fork-Bombe
)
_MEDIUM_RISK_PATTERNS = (
    r"chmod\s+0?0?0?7",        # world-writable
    r"chmod\s+-R\s+777",
    r"\bpickle\.loads?\s*\(",
    r"\byaml\.load\s*\(",
    r"\binput\s*\(\s*[\"'][^\"']*[\"']\s*\)",  # Python2-style input()
)
```

**Blockade-Level** (`security_blockade_level` in state):
- Level 0/1: nie blocken
- Level 2/3: high-risk blocken
- Level 4: high + medium risk blocken
- Default: 2

### `verify_write(agent, fn, content, wd, perms)` — Gatekeeper für Datei-Schreibaktionen

**Reihenfolge:**
1. SoulAG bypass (User-erlaubt)
2. User-Regeln prüfen
3. `is_worker_blocked(agent, fn, wd, perms)` → System-Pfad-Check
4. `is_security_block(agent, fn, content, wd, perms)` → Pattern-Check (high=block, medium=warn)
5. `request_capability(name, "WRITE", fn, "AutoApprovedSafePath")` — Track für Audit
6. Return True (erlaubt)

**Special Cases:**
- `index.html` → existiert → wird zu `index1.html`, `index2.html`, etc. (kein Overwrite)
- Existierende Files → `.bak`-Backup vor Write
- `index*.html` mit `run` perm → `subprocess.Popen(['open', fpath])` für Auto-Browser-Open

### `verify_cmd(agent, cmd)` — Gatekeeper für Shell-Commands

**Reihenfolge:**
1. SoulAG bypass
2. User-Regeln prüfen
3. `mark_harmless_shell(cmd, name)` — check gegen `HARMLESS_SHELL_PATTERNS` (screencapture, ffmpeg, say, open, pbcopy, pip install, brew install etc.) → wenn match: persist `whitelist`-Regel + auto-allow
4. Realpath-Check auf Workspace-Pfade (`[safe_workspace_path]`-Tokenization)
5. `is_command_safe_and_whitelisted(cmd, agent)` — high-risk block, medium-risk warn

**HARMLESS_SHELL_PATTERNS (Auszug):**
```python
HARMLESS_SHELL_PATTERNS = [
    r"^screencapture\b",
    r"^ffmpeg\b.*-f\s+avfoundation",
    r"^say\s+",
    r"^afplay\s+",
    r"^open\s+",
    r"^pip3?\s+install\b",
    r"^brew\s+install\b",
    ...
]
```

**WICHTIG:** `git` wurde 2026-06-15 komplett aus dem Agenten-Toolset entfernt! `is_command_safe_and_whitelisted`: `exec_name == "git"` → return `False, "high", "git ist nicht verfügbar."` (gatekeeper.py:431-432).

### `wait_for_decision(agent_name, action_type, detail, content, rule)` — User-Approval-Flow

1. Wenn `enable_confirmations = false` (default): auto-approve + post "⚡ AUTO-APPROVED"
2. Sonst: 
   - `threading.Event` pro `decision_id`
   - Save Showbox-presentation mit HTML-Blockade-Card (Approve/Reject-Buttons)
   - Set `active_showbox` zu dieser Präsentation
   - Post in Chat "Soll die Aktion erlaubt werden? (Ja/Nein)"
   - Set agent status `paused`
   - `event.wait(timeout=300)` — 5 Min Timeout
   - Bei Timeout: rejected (default)
   - User antwortet via `@@approve_decision <id>` oder `@@reject_decision <id>` (oder `ja`/`nein` im Chat → handled in `chat_legacy.py:113-130`)
   - `_signal_decision(decision_id, status)` weckt den Event

### Prompt-Injection-Validator

`core/security/injection_validator.py` (nicht vollständig gelesen, aber referenziert in `chat_legacy.py:78`) — wird VOR dem Speichern der User-Message in DB aufgerufen. Bei Treffer: User-Message wird trotzdem gespeichert (für Audit), aber SecurityAG postet Warnung in Chat und der `status="blocked"` wird zurückgegeben.

### Showbox-Validator

`core/security/showbox_validator.py` — `enforce_agent_layer()` verhindert, dass Agents in `<SHOWBOX:user>` schreiben (Layer 3 ist User-reserviert). `sanitize_showboxes()` wird beim GET `/api/chat` angewandt.

### HMAC-Signer für Showbox

`core/security/hmac_signer.py` — `generate_signature("Gnom", json.dumps(d))` — wird an jeden Showbox-Datensatz angehängt, damit das Frontend verifizieren kann, dass die Slides nicht von außen manipuliert wurden.

---

## 9. Action-Handler (Tag-Parser)

Quelle: `agents/actions/action_handlers.py` (57 Zeilen, Dispatcher) + 6 Sub-Module.

### `process_actions(ans, agent, perms, bs_mode, wd)` — Main Dispatcher

**Reihenfolge der Tag-Verarbeitung:**
1. `[WRITE: filename]content[/WRITE]` — Datei schreiben
2. `[WRITE: filename]```\ncode\n```` — alternativer Format (Code-Block nach WRITE)
3. `[READ: filename]` — Datei lesen
4. `[SHELL: command]` — Shell ausführen
5. `[DESKTOP: action]` — Desktop-Steuerung
6. `<SHOWBOX:id>{...}</SHOWBOX>` oder `<SHOWBOX:id>[...]</SHOWBOX>` oder `[SHOWBOX:id]...[/SHOWBOX]` oder `[SHOWBOX: content]` — Showbox rendern
7. `[CRAWL: url]` — Web-Crawling
8. `[VIDEO:SCREEN: ...]`, `[VIDEO:MERGE: ...]`, `[VIDEO:EDIT: ...]` — Video-Tools
9. `[BROWSER:]...[/BROWSER]` — Browser-Steuerung (Playwright)

**Gatekeeper-Integration:** JEDER Action-Tag wird VOR der Ausführung gegen `verify_write()` oder `verify_cmd()` geprüft. Bei Block: Tag wird durch `[System: ... hat keine Schreibberechtigung.]` oder `[Gatekeeper: ... verweigert.]` ersetzt.

### Action-Write (`action_write.py`, 80 Zeilen)

- `_safe(wd, fn, perms)` für Pfad-Validierung
- `seal_content(content)` strippt Whitespace
- `index.html`-Spezialhandling (Counter-Naming)
- `.bak`-Backup für existierende Files
- Auto-Open für `index*.html` mit `run` perm
- ZWC-Metadata an Success-Message

### Action-Exec (`action_exec.py`, 92 Zeilen)

- `is_command_safe_and_whitelisted()` Pre-Check
- `run_in_sandbox()` (sandbox.py, 178 Zeilen) für isolierte Ausführung
- `crawl_data` oder `crawl_smart` je nach Agent-Name
- Showbox: HTML-JSON-Sanitization, Style-Scoping (`.sb-layer-body`), HMAC-Sign

### Action-Browser (`action_browser.py`, 66 Zeilen)

Playwright-basiert. Agent-Output enthält `[BROWSER:]` mit JavaScript-Code. Wird in headless Chromium ausgeführt.

### Action-Desktop (`action_desktop.py`, 147 Zeilen)

Maus/Tastatur-Steuerung via `cliclick` (macOS) + `pyautogui` (cross-platform). Agent muss `desktop`-Permission haben.

### Action-Video (`action_video.py`, 328 Zeilen)

`[VIDEO:SCREEN:]` — Screen-Recording via ffmpeg + avfoundation. `[VIDEO:MERGE:]` — Video-Konkat. `[VIDEO:EDIT:]` — ffmpeg-Editing.

### Adaptive-Decomposition (`adaptive_decomposition.py`, 148 Zeilen)

Teilt komplexe Tasks in Sub-Tasks für sequenzielle Abarbeitung.

---

## 10. Frontend (chat.js Architektur)

Quelle: `src/gnom_hub/frontend/chat.js` (1259 Zeilen) + `showbox.js` (601 Zeilen) + `index.html`.

### `sendChat()` (chat.js:375)

```javascript
async function sendChat() {
  const ta = document.getElementById('chat-input');
  if (!ta) return;
  const msg = ta.value.trim();
  if (!msg) return;
  addToChatHistory(msg);
  if (handleChatCommands(msg, ta)) return;  // @@-Commands VOR API
  ta.value = '';
  
  const res = await api('POST', '/chat', { content: msg });
  // ...toast + refresh
}
```

**`handleChatCommands(msg, ta)`** (chat.js:~330) prüft `@@`-Prefix-Commands LOKAL im Frontend, BEVOR die API gerufen wird. Aus dem Diff: `@@slides` und `@@artshow` wurden ENTFERNT (nicht mehr im Frontend, vermutlich weil sie nicht funktionierten oder unbenutzt waren).

### `api(method, path, body)` — HTTP-Wrapper

Vermutlich ein einfacher `fetch()`-Wrapper. Wird auch von `window.api()` (siehe `gatekeeper.py:234` Showbox-Buttons) genutzt.

### Frontend-Polling

`refreshChat()` wird nach `sendChat()` aufgerufen. Es gibt vermutlich ein `setInterval` für periodische Updates (nicht im gelesenen Abschnitt, aber Standard-Pattern).

### `parseShowboxInMsg(m, overrideId)` (chat.js:411)

- Strippt unsichtbare Unicode-Chars (ZWC!) vom Ende des Content: `[\u200B-\u200D\uFEFF\u2060\u2061\u2062\u2063\u2064\u00AD\u034F\u115F\u1160\u17B4\u17B5\u180E\u2028\u2029\u202A-\u202E\u2066-\u2069\u2800\u3164\uFFA0]+$`
- Extrahiert `<SHOWBOX:id>...</SHOWBOX>`-Match
- Track in `_processedShowboxes` Set (idempotent)
- JSON.parse mit Fallback auf Plain-Text-Slide
- Layer-Mapping: `system→1, worker→2, user→3, 1→1, 2→2, 3→3`

### `cleanNormalChatMessage(safe)` (chat.js:471)

Ersetzt Action-Tags durch HTML-Badges für die Chat-Anzeige:
- `[WRITE: filename]...[/WRITE]` → `<div class="action-summary-badge write-badge">💾 Datei geschrieben: <filename></div>`
- `[SHELL: cmd]` → `💻 Befehl ausgeführt: <cmd>`
- `[READ: fn]` → `📖 Datei gelesen`
- `[BROWSER:]...[/BROWSER]` → `🌐 Browser-Skript`
- `[Browser-Ausgabe: ...]` → `<details>`-Block
- XSS-Schutz: HTML-escape via `[&<>"']` map

### TTS

- `_ttsQ` Queue
- `_ttsAudioCtx` für AutoPlay-Unlock (workaround für Browser-AutoPlay-Policy)
- `unlockAudio()` — leerer AudioBuffer + AudioContext.resume()
- `loadTTSVoices()` — speechSynthesis.voiceschanged-Listener
- `recognition` (webkitSpeechRecognition) — STT, kontinuierlich, Deutsch, füllt chat-input

### `BUILTIN_CMDS`

`['bs', 'research', 'job', 'status', 'clear', 'project', 'git', 'worker', 'spass', 'merken', 'diagnose', 'help']` — wird im Frontend für Autocomplete genutzt.

### showbox.js (601 Zeilen)

Rendert die 3-Layer Showbox (system/worker/user). Buttons-Handling für Gatekeeper-Approve/Reject.

---

## 11. API-Endpoints (Übersicht)

`src/gnom_hub/api/endpoints/` — 28 Endpoint-Module.

### Kern-Endpoints (für die Kommunikation relevant)

| Method | Path | Modul | Zweck |
|--------|------|-------|-------|
| POST | `/api/chat` | `chat_legacy.py` | User-Message-Entry (siehe Layer D) |
| GET | `/api/chat` | `chat_legacy.py` | Chat-Verlauf (limit=50) |
| POST | `/chat/send` | `chat.py` | LLMOrchestrator.process_message |
| POST | `/chat/brainstorm` | `chat.py` | Brainstorm-Roundtrip |
| POST | `/api/swarm/complete` | `agents_status.py:547` | Agent-Completion-Callback (siehe Layer C) |
| GET | `/api/observability/metrics` | `observability.py` | Per-Agent + Per-Capability + Workflow-Stats |
| GET/POST | `/api/workflows` | `workflows.py` | Workflow-CRUD |
| GET | `/api/agents` | `agents.py`, `agents_list.py` | Agent-Liste |
| POST | `/api/agents/{name}/heartbeat` | `agents_status.py` | Agent-Heartbeat |
| PUT | `/api/agents/{name}/status` | `agents_status.py` | Status-Update |
| POST | `/api/agents/register` | `agents_status.py` | Agent-Registrierung |
| GET | `/api/llm/providers` | `llm_models.py` | Provider-Katalog |
| GET/POST | `/api/llm/service` | `llm_models.py` | TTS/WebSearch-Config |
| GET/POST | `/api/llm/keys` | `llm_keys.py` | API-Key-Management |
| GET/POST | `/api/llm/agents` | `llm_agents.py` | Per-Agent-LLM-Config |
| POST | `/api/admin/clean-all` | `admin.py` | Komplett-Reset |
| POST | `/api/admin/backup` | `admin.py` | DB-Backup |
| GET/POST | `/api/admin/*` | `admin_system.py`, `admin_config.py`, `admin_tools.py` | Admin-Funktionen |
| GET/POST | `/api/memory_crud` | `memory_crud.py` | Soul-Memory-CRUD |
| GET | `/api/memory_search` | `memory_search.py` | Soul-Memory-Fuzzy-Search |
| GET | `/api/metrics` | `metrics.py` | System-Metriken (RAM, CPU, etc.) |
| GET | `/api/showbox` | `showbox.py` | Showbox-Liste |
| POST | `/api/audio/tts` | `audio.py` | TTS-Synthese |
| GET | `/api/integrity` | `integrity.py` | File-Hash-Check |
| GET | `/api/auth` | `auth.py` | Auth-Status |
| POST | `/api/nudge` | `nudge.py` | UI-Notification-Trigger |
| GET | `/api/system_info` | `system_info.py` | System-Info |
| GET/POST | `/api/workspace` | `workspace.py` | Workspace-CRUD |
| GET/POST | `/api/presets` | `presets.py` | Preset-Management |
| GET | `/api/router` | `router.py` | Routing-Status |
| GET | `/api/registry` | `registry.py` | Tool-Registry |

### Showbox-Buttons

Buttons in Showbox rufen `window.api('POST', '/chat', {content: '@@approve_decision <id>'})` oder `@@reject_decision <id>` auf — das geht durch `chat_legacy.post_chat()` → `_parse()` → CMDS[cmd] = `handle_approve_decision` / `handle_reject_decision`.

---

## 12. Test-Coverage

**Stand:** 534 Tests passed, 2 pre-existing fails, 2 skipped (siehe CHANGELOG.md `[Unreleased]`).

### Test-Files (`tests/`)

| Datei | Was es testet |
|-------|---------------|
| `test_swarm_comms.py` | Layer A — Message-Bus (dispatch, fetch, ack, nack, recovery, DLQ-Kaskade) |
| `test_queue_stability.py` | Queue-Stabilität unter Last |
| `test_concurrency.py` | Concurrent Agent-Loops |
| `test_workflows_endpoint.py` | Layer B — Workflow-Engine + REST-Endpoint |
| `test_browser_full.py`, `test_browser_workflows.py`, `test_browser_action.py` | Playwright-Browser-Aktionen |
| `test_router.py`, `test_router_provider_registry.py`, `test_routing_persistence.py`, `test_routing_precedence.py`, `test_openrouter.py` | LLM-Router, Provider-Registry, Routing-Persistenz |
| `test_frontend_llm_providers.py` | Frontend-Provider-Endpoints |
| `test_security_suite.py` | Gatekeeper, Path-Validator, Injection-Validator |
| `test_admin_auth.py`, `test_admin_system.py` | Admin-Endpoints |
| `test_sandbox_argv.py` | Sandbox-Argv-Parsing |
| `test_stability.py`, `test_stress_50.py` | Stabilität/Stress |
| `test_chat_db.py`, `test_agents_db.py`, `test_state.py`, `test_connection.py` | DB-Layer |
| `test_agent_names_frozen.py` | **Schützt frozen contract: `agent_names.py`** |
| `test_audit_log_cap.py` | Audit-Log-Größe-Limit |
| `test_default_preset_content.py`, `test_preset_schema_loader.py` | Preset-System |
| `test_workspace_config.py` | Workspace-Config |
| `test_kill_orphans.py` | Orphan-Prozess-Kill |
| `test_faiss_lock.py` | FAISS-Threading |
| `test_gnom_hub.py` | Integration |
| `test_coordination_learning.py` | Coordination-DB-Lern-Mechanik |
| `test_soul_memory_retrieval.py` | **PRE-EXISTING FAIL** (Soul-Retrieval) |
| (in `test_security_suite.py`) `TestVerifyCmd.test_protected_path_instant_blocked` | **PRE-EXISTING FAIL** (Path-Validator) |

### Pre-Existing Failures

Werden **toleriert** (siehe `PRE_PUSH_CHECKLIST.md` und User-Memory):
- `test_soul_memory_retrieval` — Soul-Retrieval-Edge-Case
- `TestVerifyCmd.test_protected_path_instant_blocked` — Path-Validator-Edge-Case (false-positive in der Path-Tokenization-Logik)

### Test-Ausführung

```bash
PYTHONPATH=src python3.10 -m pytest
```

NICHT `python3.9` (ImportError). NICHT `python3.11` (numpy/FAISS-Probleme möglich).

---

## 13. Tooling & Scripts

`scripts/` (27 Scripts):

| Script | Zweck |
|--------|-------|
| `install.sh` | Installer |
| `uninstall.sh` | Uninstaller |
| `start_gnom_hub.sh`, `stop_gnom_hub.sh` | Start/Stop |
| `start_agents.sh` | Startet nur Agenten (ohne Hub) |
| `gnom-monitor.py` | **Auto-Free** hängender Agents nach 2 Min |
| `diagnose_hub.py` | `@@diagnose` Handler |
| `clean_db.py` | DB-Cleanup (PRE_PUSH_CHECKLIST Schritt 2) |
| `optimize_dbs.py` | VACUUM + ANALYZE |
| `verify_dbs.py` | DB-Integrität |
| `backup_all_dbs.sh`, `restore_backup.sh`, `scheduled_backup.sh` | Backup |
| `fetch_openrouter_free.py` | Working-Models-Liste aktualisieren |
| `set_keys.py`, `set_llms.py` | API-Keys + LLM-Config |
| `agent-setup-minimal.sh` | Agent-Setup |
| `live_browser_presentation.py` | Live-Browser-Show |
| `tts_walkthrough.py` | TTS-Test |
| `fix_all_agents.py` | Reparatur-Script |
| `post_git_push_offer.py` | Post-Push-Backup-Offer |
| `restore_netzwerkpunkt.py` | Netzwerkpunkt-Restore |
| `make_schema_pngs.py` | Schema-Diagramme |
| `start.ps1`, `stop.ps1` | Windows-PowerShell-Varianten |

### Root-Scripts

- `run.sh` (root) — Quick-Start (Linux/Mac)
- `setup_macos_shortcut.sh` — macOS-LaunchAgent
- `install.py` — Python-Installer (umfangreich, 18650 bytes)
- `pyproject.toml` — Package-Config
- `opencode.jsonc` — Mavis-Config

### PRE_PUSH_CHECKLIST.md

10-Schritte-Checkliste vor jedem Push (Backup, Hub stoppen, DB leeren, Tests, etc.). MUSS vor jedem `git push` gelesen werden.

---

## 14. Git-Stand: was modifiziert ist, was untracked ist

### `git log --oneline --all`
```
535f241 Icons aus den Agenten-Displays rausgenommen
29a3e54 Custom SVG-Icons + Agent Art Show in Showbox
e28ba60 Initial commit: Gnom-Hub v1.2.0
```

Nur 3 Commits. **Der gesamte [Unreleased]-Block aus CHANGELOG.md ist NOCH NICHT committed** — die TTS-Provider-Dispatch, SmartRouter-Refactor, Provider-Registry, Frontend-Provider-Detection, Global-Save etc. sind alle in Working-Tree aber nicht committed.

### Modified Files
```
M AGENTS.md                      ← MC-707 Section hinzugefügt
M config/agent_tools.json        ← 5 neue mc707_* tools
M pyproject.toml                 ← ?
M src/gnom_hub/frontend/chat.js  ← @@slides/@@artshow entfernt
M src/gnom_hub/frontend/index.html
M src/gnom_hub/frontend/showbox.js
M src/gnom_hub/frontend/system_dashboard.js
M src/gnjome/frontend/worker_dashboard.js
```

### Untracked
```
?? 30                              ← Verwaiste Datei? Größe 5.3 MB
?? docs/mc707-reference/           ← MC-707 Doku
?? docs/mc707_handoff.md           ← MC-707 Handoff
?? src/gnom_hub/infrastructure/audio/  ← Audio-Infrastructure (MC-707-related)
?? src/mc707/                      ← **MC-707 MIDI-Controller Library** (eigenes Sub-Projekt)
```

**WICHTIG:** Diese Mods + Untracked sind alle **MC-707-related**. Der User arbeitet gerade an einer MIDI-Controller-Bibliothek als Side-Quest. NICHT mit dem Gnom-Hub-Kern-Communication-Refactor mischen!

Die `30`-Datei (5.3 MB) ist suspekt — vermutlich `core.py` oder ein Dump. **Sollte vor Push gelöscht werden** (PRE_PUSH_CHECKLIST).

---

## 15. Laufende externe Pläne (Mavis team plan)

Aus dem Scratchpad der Root-Session (`/Users/landjunge/.mavis/scratchpads/mvs_52b1ea94fdae4083a445ee304e28ea3d/scratchpad.md`):

> Active plan: `plan_76a00ade` (MC-707 MIDI-Controller)
> - Cycle 5, phase: producing
> - 4/7 tasks done: foundation, scenes-clips, sounds, patterns
> - 2 producing: effects-arp, sysex-status
> - 1 blocked: integration

**Mavis Team Plan** läuft parallel: 7 Tasks für MC-707-Implementation. Verifizierungs-Disziplin siehe AGENTS.md: "verify_prompt ist der Gate — Methoden müssen tatsächlich dispatchen, auch wenn Task-Text 'stub mit pass-Methoden' sagt."

**Für Gnom-Hub-Communication-Refactor NICHT RELEVANT.** Der Plan erstellt eine separate Library `src/mc707/`.

---

## 16. Schmerzpunkte (Priorisiert)

### 🔴 KRITISCH (Production-Blocker)

1. **Mention-Regex 3× kopiert** an unterschiedlichen Stellen:
   - `swarm_coordinator.py:94` — `r'@(\w+)[\s→>:\-]+(.+)'`
   - `chat_commands_handlers.py:33` — exakt gleich
   - `swarm_comms.py:78` — `r'@(\w+)\s*[-–→>]+\s*(.+)'` (Variante)
   
   Fix: Eine `parse_agent_mentions()`-Funktion in `core/agent_names.py` oder neuem `core/parsing.py`. Bricht beim kleinsten Bugfix überall.

2. **Cross-Process Event-Bus fehlt**: `notify_agent()` in `swarm_comms.py` setzt nur ein in-process `threading.Event`. Bei Multi-Process (jeder Agent ist eigener Prozess!) bringt das NICHTS. **Aktuell funktioniert es nur weil der Server-Prozess die Events setzt und der Agent-Prozess beim nächsten DB-Read sowieso pollt.** Aber: bei `pending` Messages wacht der Agent nur durch `evt.wait()` auf, das nur im Server-Prozess gesetzt wurde. → Agent-Loop wartet 30s timeout.

3. **Dead-Letter-Recovery unimplementiert**: `recover_stuck_messages()` und `recover_stuck_workflows()` sind definiert, aber **niemand ruft sie periodisch auf**. WatchdogAG hat `monitoring`-Capability, aber `agent_base.py` für WatchdogAG macht keinen periodischen Sweep. → Hängende Messages bleiben für immer in `processing` state.

4. **System-Prompt-Doppelung**: `agent_base.py:11-13` baut `sys_prompt` mit `format_tools_prompt()`, `router.py:_build_sys` baut NOCHMAL mit `build_system_prompt()`. → Agenten bekommen **2×** den System-Prompt-Inhalt. Token-Verschwendung, potenzielle Prompt-Injection-Vektoren.

5. **Kein Trace über User-Turns**: `parent_msg_id` ist die einzige Korrelation, aber Messages können auch ohne Parent existieren. → Kein "Was hat User X in den letzten 5 Min getriggert?" möglich.

6. **Chat-History-Inflation**: `agent_base.py:140-150` injiziert letzte 20 Chat-Nachrichten in JEDEN System-Prompt (auch für Worker). Bei Brainstorm mit 4 Workern = 4× identische 20-Nachrichten-Injection. Token-Kosten explodieren.

7. **Kein Auto-Approve-Loop-Protection**: `enable_confirmations=false` (default) → `wait_for_decision` returnt sofort True. Ein Agent kann in einer Endlosschleife blockierbare Aktionen ausführen, weil nichts ihn stoppt.

### 🟡 MITTEL (Wartbarkeit, Performance)

8. **Mention-Routing erlaubt keine Edge-Cases**: Wenn 3 Mentions von User kommen und 2 Worker offline sind, wird der dritte **stillschweigend verworfen**. Kein Feedback an User.

9. **Rollen sind hartcodiert** in `agent_base.py:24-41` — 8 elif-Ketten für CAPABILITIES. Neue Agenten = Code-Edit, nicht Config.

10. **DB-Poll-Last**: 8 Agent-Prozesse + Hub-Prozess = 9 SQLite-Connections. Jeder Agent pollt mit `fetch_next_message(timeout=3.0)` + `evt.wait(1.0)`. Bei 8 schlafenden Agenten = 8 Polls/Sek. Akzeptabel, aber WAL-Locks könnten zum Bottleneck werden.

11. **Hardcoded Constants verteilt**: `MAX_DEPTH`, `MAX_CONCURRENT`, `RETRY_MAX`, etc. in `swarm_comms.py:21-27` — keine zentrale Config. Sollte nach `core/constants.py` (das schon `WORKFLOW_*` definiert).

12. **3 verschiedene `distribute_job`-artige Funktionen**: `role_tools.distribute_job()`, `swarm_coordinator._eval()`, `chat_legacy.handle_job()` — alle machen im Wesentlichen "LLM-Aufruf + parsen @Worker -> task". Sollte 1 Funktion sein.

13. **Chat-Verlauf in `agent_base.py` injected OHNE Filterung**: Alle Agents bekommen den gleichen Chat-Verlauf. Worker bekommen oft irrelevanten Kontext (z.B. SoulAG's TTS-Marker).

14. **Workflow-Template-Lookup ist O(N)**: `workflow_engine.interpolate_template` iteriert für jeden `{var}` durch `re.finditer` über den ganzen Template. Bei komplexen Workflows ineffizient.

15. **`agent_base._register_capabilities` löscht+reinserTIERT bei jedem Start** — kein Idempotenz-Check. Bei parallelem Start Race möglich.

16. **Keine `agent_id` UUID-Validierung** in `chat_repo.save_message` — fängt Exceptions mit `try/except UUID()`, setzt `aid = uuid.NAMESPACE_DNS` (Bug-Maskierung).

17. **`handle_workflow` ist eine 50-Zeilen-Quick-Hack-Heuristik** (`chat_legacy.py:13-73`): Keywords → Capabilities → Tasks. Nicht durchdacht, bricht bei ungewöhnlichen Anfragen.

### 🟢 NIEDRIG (Polish)

18. **ZWC-Steganographie in Chat-Output**: `chat_legacy.py:81` strippt sie nur bei Datei-Writes, nicht überall. User sieht unsichtbare Characters gelegentlich.

19. **`add_agent_metadata` nach JEDEM File-Write**: Kann zu langer ZWC-Trail führen, der UI-Rendering verlangsamt (Frontend `parseShowboxInMsg` muss alle strippen).

20. **Showbox-Sanitization in `chat.js:62-69` ersetzt `body` durch `.sb-layer-body` global** — kann legitime CSS-Selektoren killen.

21. **`agent_definitions.py:14` Sys-Prompt sagt "Du beginnst JEDE deiner Antworten damit..." aber `think_guideline` in `agent_base.py:15-21` sagt das auch** — Doppelung der Think-Anweisung.

22. **Logging-Inkonsistenz**: Manche Module loggen mit `logging.getLogger(__name__)`, andere mit `logging.getLogger("db")`, andere mit `logging.getLogger("soul")`. Schwer zu grep'en.

23. **Frontend `chat.js:424` Regex für ZWC-Strip ist eine 30-Char-Class** — kann andere Unicode-Chars fälschlicherweise killen.

---

## 17. Konkrete Verbesserungs-Roadmap

### Sprint 1: Aufräumen (1-2 Tage, keine Verhaltensänderung)

1. **Mention-Parser deduplizieren** — `parse_agent_mentions()` in `core/parsing.py` (neu), 3 Call-Sites umstellen. Tests: `test_swarm_comms.py` + 2 neue für die Helper.
2. **System-Prompt-Bau zentralisieren** — entweder BaseAgent ODER Router. Saubere Trennung.
3. **Hardcoded Constants nach `core/constants.py`** — `MAX_DEPTH`, `MAX_CONCURRENT`, `RETRY_MAX`, `RETRY_BACKOFF_BASE`, `MAX_QUEUE_DEPTH`, `DEPENDENCY_TIMEOUT`, `DEPENDENCY_POLL_S`, `PRIORITY_MAPPING`.
4. **Cross-Process Event-Bus fixen** — entweder LISTEN/NOTIFY in SQLite, oder per `asyncio.Queue` + Hub-Loop, oder Wechsel auf HTTP-Long-Polling mit Early-Response.

### Sprint 2: Beobachtbarkeit (1 Woche)

5. **Trace-ID einführen** — UUID pro User-Turn, in jede Message + Result, neuer `/api/trace/{trace_id}` Endpoint.
6. **`/api/swarm/queue-depth` Endpoint** + Frontend-Widget.
7. **Periodische Recovery implementieren** — WatchdogAG bekommt periodischen `recover_stuck_messages()` und `recover_stuck_workflows()` Sweep.
8. **Zentrale Logging-Konvention** — `get_logger(name)` Helper, der konsistent `gnom_hub.<module>` formatiert.

### Sprint 3: Robustheit (1-2 Wochen)

9. **Coordinator + distribute_job mergen** — eine Funktion für "User-Task → @Worker-Zuweisungen via LLM".
10. **Chat-History-Injection pro Agent filtern** — Worker bekommen nur die letzten N relevanten Messages (semantisch oder per SENDER-Filter).
11. **Mention-Routing mit Edge-Case-Reporting** — Wenn Agent offline, post System-Message "CoderAG war offline, dein @CoderAG-Task wurde nicht zugestellt."
12. **Capability-Konfiguration aus `config/agent_tools.json`** — kein Hardcoding mehr.
13. **Loop-Protection für Auto-Approve** — Counter für "blockierbare Aktionen pro Agent pro Minute", Threshold → forced confirm.

### Sprint 4: Skalierung (2+ Wochen)

14. **Pub/Sub-Konzept** — `@worker` (Broadcast), `@system` (System-Agents), Topics, Subscribe-Pattern.
15. **Strukturierte Tool-Calls** — Statt `[WRITE: foo]content[/WRITE]` → JSON-Tool-Calls im Agent-Output, parseable mit Pydantic-Schema.
16. **Cross-Process Event-Bus** (Redis/ZeroMQ oder LISTEN/NOTIFY) — für Multi-Process-Fähigkeit.
17. **Dead-Letter-UI** — `/api/admin/dead-letters` Endpoint + Frontend-View + "Replay"-Button.

### Sprint 5: Polish

18. **ZWC-Bereinigung** — sauberer Strip in `chat_legacy.py`.
19. **Logging-Konvention** durchsetzen.
20. **Frontend-Showbox-Scope-Fix** — nicht-globalen `body`/`html`-Replace.
21. **Doppelte Think-Anweisung** im System-Prompt entfernen.

---

## 18. Quick-Reference: Wo was steht

| Was du suchst | Datei | Zeilen |
|---------------|-------|--------|
| 8 Agenten-Definitionen | `src/gnom_hub/agents/agent_definitions.py` | 218 |
| Frozen Name-Mapping | `src/gnom_hub/core/agent_names.py` | 41 |
| Message-Bus (Layer A) | `src/gnom_hub/agents/swarm/swarm_comms.py` | 796 |
| Workflow-Engine (Layer B) | `src/gnom_hub/agents/swarm/workflow_engine.py` | 466 |
| Team-Coordinator (Layer C) | `src/gnom_hub/agents/swarm/swarm_coordinator.py` | 147 |
| Swarm-Checkpoints | `src/gnom_hub/agents/swarm/swarm_checkpoint.py` | 32 |
| Agent-Base-Loop | `src/gnom_hub/agents/agent_base.py` | 285 |
| DB-Schema | `src/gnom_hub/db/schema.py` | 371 |
| DB-Connection | `src/gnom_hub/db/connection.py` | 49 |
| Chat-Repo (OOP + Legacy) | `src/gnom_hub/db/chat_repo.py` | 276 |
| Agent-Repo (OOP + Legacy) | `src/gnom_hub/db/agent_repo.py` | 296 |
| Message-Queue-Schema | `src/gnom_hub/db/message_queue.py` | 54 |
| LLM-Router (Hauptpfad) | `src/gnom_hub/infrastructure/router/router.py` | 272 |
| LLM-Orchestrator (simple) | `src/gnom_hub/infrastructure/router/llm_orchestrator.py` | 52 |
| SmartRouter (4 Stages) | `src/gnom_hub/infrastructure/router/router_stage.py` | 437 |
| Process-Manager | `src/gnom_hub/infrastructure/process/process_manager.py` | 137 |
| Sandbox | `src/gnom_hub/infrastructure/process/sandbox.py` | 178 |
| Soul-Hauptklasse | `src/gnom_hub/soul/soul.py` | 377 |
| Soul-Memory-Layers | `src/gnom_hub/soul/memory_layers.py` | 737 |
| Soul-Observer | `src/gnom_hub/soul/soul_observer.py` | 198 |
| ZWC-Soul | `src/gnom_hub/soul/zwc_soul.py` | 181 |
| Soul-Actions | `src/gnom_hub/soul/soul_actions.py` | 229 |
| Soul-Initializer | `src/gnom_hub/soul/soul_initializer.py` | 141 |
| Agent-Voices (TTS) | `src/gnom_hub/soul/agent_voices.py` | 149 |
| Gatekeeper | `src/gnom_hub/core/security/gatekeeper.py` | 504 |
| Path-Validator | `src/gnom_hub/core/security/path_validator.py` | 139 |
| Action-Dispatcher | `src/gnom_hub/agents/actions/action_handlers.py` | 57 |
| Action-Write | `src/gnom_hub/agents/actions/action_write.py` | 80 |
| Action-Exec | `src/gnom_hub/agents/actions/action_exec.py` | 92 |
| Action-Browser | `src/gnom_hub/agents/actions/action_browser.py` | 66 |
| Action-Desktop | `src/gnom_hub/agents/actions/action_desktop.py` | 147 |
| Action-Video | `src/gnom_hub/agents/actions/action_video.py` | 328 |
| Adaptive-Decomposition | `src/gnom_hub/agents/actions/adaptive_decomposition.py` | 148 |
| Role-Tools (General) | `src/gnom_hub/agents/role_tools.py` | 17 |
| Brainstorm | `src/gnom_hub/chat/brainstorm/brainstorm.py` | 57 |
| Brainstorm-Helpers | `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py` | 32 |
| Chat-Commands | `src/gnom_hub/chat/chat_commands.py` | 410 |
| Chat-Commands-Handlers | `src/gnom_hub/chat/chat_commands_handlers.py` | 39 |
| Chat-Clear | `src/gnom_hub/chat/chat_clear.py` | (klein) |
| Frontend Chat | `src/gnom_hub/frontend/chat.js` | 1259 |
| Frontend Showbox | `src/gnom_hub/frontend/showbox.js` | 601 |
| Chat-Endpoint | `src/gnom_hub/api/endpoints/chat_legacy.py` | 182 |
| Chat-Endpoint (neu) | `src/gnom_hub/api/endpoints/chat.py` | 30 |
| Observability-Endpoint | `src/gnom_hub/api/endpoints/observability.py` | 118 |
| Swarm-Complete-Endpoint | `src/gnom_hub/api/endpoints/agents_status.py:547` | ~100 |
| Workflows-Endpoint | `src/gnom_hub/api/endpoints/workflows.py` | (groß) |
| ExplainableOutput-Class | `src/gnom_hub/agents/explainability/eo_class.py` | 36 |
| ExplainableOutput-Wrap | `src/gnom_hub/agents/explainability/eo_wrap.py` | 40 |
| ExplainableOutput-Builder | `src/gnom_hub/agents/explainability/eo_builder.py` | 26 |
| ExplainableOutput-Store | `src/gnom_hub/agents/explainability/eo_store.py` | (mittel) |
| ExplainableOutput-Formatter | `src/gnom_hub/agents/explainability/eo_formatter.py` | (mittel) |
| Frozen-Tests | `tests/test_agent_names_frozen.py` | - |
| Swarm-Tests | `tests/test_swarm_comms.py` | - |
| Queue-Tests | `tests/test_queue_stability.py` | - |
| Workflow-Tests | `tests/test_workflows_endpoint.py` | - |
| Security-Tests | `tests/test_security_suite.py` | - |
| Router-Tests | `tests/test_router.py` + 4 mehr | - |
| LLM-Frontend-Tests | `tests/test_frontend_llm_providers.py` | 14 Tests |
| Pre-Push-Checklist | `PRE_PUSH_CHECKLIST.md` | - |
| Architektur-Übersicht | `AGENT_DEFINITIONS.md` | 319 |
| Voller System-Report | `GNOM_HUB_FULL_REPORT.md` | - |
| Master-Briefing | `GNOM_HUB_MASTER_BRIEFING.md` | - |
| Status-Update | `GNOM_HUB_STATUS.md` | - |

---

## Anhang: Was diese Analyse NICHT abdeckt

Aus Zeitgründen nicht (vollständig) gelesen:

- `core/utils/slider_prompt.py` — System-Prompt-Builder
- `core/utils/compiler.py` — `@bake` SuperGNOM-Compiler
- `core/utils/evolution_v2.py` — Prompt-Evolution
- `core/utils/routing_override.py` — routing.txt-Loader
- `core/utils/preset_service.py` — Preset-Service
- `core/utils/audio_tts.py` — TTS-Routing (Multi-Provider)
- `core/utils/embeddings.py` — FAISS-Wrapper
- `core/security/injection_validator.py` — Prompt-Injection-Check
- `core/security/showbox_validator.py` — Showbox-Sanitization
- `core/security/hmac_signer.py` — Showbox-HMAC
- `core/json_sanitizer.py` — JSON-Cleanup
- `infrastructure/router/router_call.py` — HTTP-Provider-Calls
- `infrastructure/router/router_config.py` — Keys
- `infrastructure/utils/crawler_engine.py` — Web-Crawler
- `infrastructure/monitoring.py` — `record_agent_request`
- `infrastructure/pulse.py` — Janitor
- `agents/tool_registry.py` — Tool-Registry
- `agents/capability_manager.py` — Capability-Manager
- `agents/specialization_monitor.py` — Specialization-Tracking
- `agents/team_velocity.py` — Team-Metriken
- `memory/soul_retrieval.py` — Soul-Retrieval
- `db/passive_db.py` — Passive-DB-Logic
- `db/showbox_repo.py`, `db/soul_repo.py`, `db/system_repo.py`, `db/state_repo.py`, `db/legacy_db.py`
- 28 API-Endpoints (nur wichtigste gelesen)
- Frontend `index.html`, `showbox.js` (komplett), `system_dashboard.js`, `worker_dashboard.js`, `core.js`
- 25+ weitere Test-Files (Inhalt nicht im Detail, nur Namen)
- docs/ (backlog, concept, postmortem, etc.)
- ARCHITECTURE.md
- README.md / README.de.md

Diese Dateien sind **nicht kritisch** für die Communication-Analyse, aber wichtig für volles Verständnis. Bei Bedarf kann diese Analyse iterativ erweitert werden.

---

**Erstellt am:** 2026-06-20 03:42 Europe/Berlin
**Repository:** `/Users/landjunge/gnom-hub` · Branch: `main` · Working-Tree: 8 modifiziert + 5 untracked
**Autor:** Mavis (claude-sonnet-4-5, Mavis-Orchestrator)
**Für:** Hand-Over an andere KI / neuen Mitarbeiter / zukünftiges Ich
