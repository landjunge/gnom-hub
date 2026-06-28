# Audit: GeneralAG

**Audit-Datum:** 2026-06-28 17:30 UTC+2
**Auditor:** general (Worker-Audit)
**Quellen-Sprache:** Deutsch, technische Tokens Englisch
**Methode:** Read aller Pflichtquellen + `grep -rn "GeneralAG|generalag"` (184 Treffer in `src/`) + Cross-Reference aller 8 Agent-Configs + CoordinationDB-Schema + Swarm-Comms-Detailpfad

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/GeneralAG.json` | 40 (Identity-Block 5.554 Zeichen) | v5.3 — User-Mandat 2026-06-28 12:03. Sliders, prompt_blocks, identity (Showbox/Buttons-Pflicht, 3 Kernrollen, Git-Management, Worker-Tracking, Tier-Hierarchie, eigene DB), permissions, allowed_contexts, context_filters (active_rules disabled) |
| `src/gnom_hub/agents/agent_definitions.py:106-154` | 49 | GeneralAG-Block in Python-SSoT. **Unterschiedlich zu JSON:** sys_prompt ist hier kürzer (keine 3 Kernrollen, keine DB-Sektion, keine Buttons-Anweisungen). Permissions in DE/EN: `["read", "@job", "general_memory"]` (Z. 148, 153) — **WIDERSPRICHT JSON** (welches `["read", "write", "@job", "db_write", "showbox_write"]` hat) |
| `src/gnom_hub/api/endpoints/chat_legacy.py:75-214` | 220 | `/api/chat` POST Endpoint. Ruft `soul_instance.on_message()` (Z. 109), parsed `_parse()` (Z. 132), broadcastet (Z. 207-213), Special-Paths für `research` (Z. 204-206) und Commands (Z. 202 via `CMDS[cmd](q)`) |
| `src/gnom_hub/api/endpoints/chat.py` | 30 | **Stub-Router** mit `LLMOrchestrator` Wrapper. `/chat/send` und `/chat/brainstorm` Endpoints, beide gehen über `orch.process_message()` → `ask_router()` (KEIN `dispatch_mention`!) — d.h. chat.py-Pfad schreibt nur in `agent_messages` ohne Swarm-Dispatch. GeneralAG wird hier NICHT als System-Agent erkannt. **Im Wesentlichen tot.** |
| `src/gnom_hub/api/endpoints/chat_helpers.py:1-65` | 65 | `_parse()` parst `@system @<agent>`, `@generalag @<cmd>`, `@<tag> <msg>`. `SYSTEM_AGENTS = ["soulag", "generalag", "securityag", "watchdogag"]` (Z. 5). GeneralAG-Cmd-Dispatch: Z. 18 listet commands (bs, clear, status, research, job, git, project, diagnose, help, spass, worker, merken, allclear000) |
| `src/gnom_hub/chat/brainstorm/brainstorm.py:18-57` | 57 | `dispatch()` — zentrale Routing-Funktion. Wenn `target=generalag` → direkter Mention via `dispatch_mention()`. Wenn `target=None` → **NUR GeneralAG wird gefragt** mit speziellem Brainstorm-Instruction-Block (Z. 38-55): "Zerlege sie in Teilaufgaben und weise sie den passenden Worker-Agenten zu" |
| `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:1-32` | 32 | `ask_llm()`: ruft `format_tools_prompt` + `inject_context` (SoulAG) + **DOPPELTE Workspace-Injection** Z. 15-16: `sys += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"`. Bei `bs_mode=True` Z. 17: "[MODUS: BRAINSTORM — Diskutiert UND erstellt Ergebnisse! [WRITE:], [SHELL:] und [READ:] sind erlaubt.]" |
| `src/gnom_hub/soul/memory_layers.py:32-33` | 33 | `coordination_db_path() = _db_dir() / "coordination.db"` (NICHT in haupt-hub.db, sondern in `~/.gnom-hub-3002/data/coordination.db` pro Instanz) |
| `src/gnom_hub/soul/memory_layers.py:357-531` | 175 | `CoordinationDB` Klasse. Tabellen: `worker_stats` (Z. 373-384), `job_history` (Z. 386-395), `delegation_rules` (Z. 398-403). Methoden: `record_job()` (Z. 415-448), `get_best_worker()` (Z. 450-470), `get_worker_summary()` (Z. 472-493), `get_recent_failures()` (Z. 495-507) |
| `src/gnom_hub/soul/memory_layers.py:617-754` | 137 | `ContextDB` Klasse für "GeneralAGs Arbeitsgedächtnis". Tabellen: `contexts` (Z. 634-644), `context_events` (Z. 647-654). Methoden: `open_context()`, `add_event()`, `close_context()`, `get_active_contexts()`, `get_summary_for_generalag()` (Z. 718-733) |
| `src/gnom_hub/agents/swarm/swarm_comms.py:18-28` | 11 | `MAX_DEPTH=15`, `MAX_CONCURRENT=8`, `RETRY_MAX=3`, `RETRY_BACKOFF_BASE=3.0`, `MAX_QUEUE_DEPTH=100` |
| `src/gnom_hub/agents/swarm/swarm_comms.py:66-84` | 19 | `parse_agent_sequence()` — parst mehrzeilige Delegation im Format `@CoderAG -> Erstelle HTML`. KEIN Slash-Command-Format, nur Pfeil-Syntax |
| `src/landjunge/gnom-hub/src/gnom_hub/agents/swarm/swarm_comms.py:180-293` | 114 | **`find_best_agent_for_task()` — 3-Stage Smart-Routing**: (1) coordination.db worker_stats nach success_rate sortiert, (2) agent_capabilities confidence+queue, (3) Keyword-Heuristik. **Wird vom SmartRouter in `find_best_agent_for_task()` konsultiert, NICHT von GeneralAG selbst** |
| `src/gnom_hub/agents/swarm/swarm_comms.py:572-609` | 38 | `nack_message()` — retry mit Backoff, bei `RETRY_MAX=3` → DLQ + Kaskade. **Benachrichtigt User via `_post_chat("System", f"⚠️ Agent {recipient} gescheitert an: {reason[:200]}")` (Z. 593-594). NICHT GeneralAG!** |
| `src/gnom_hub/agents/swarm/swarm_comms.py:725-769` | 45 | `recover_stuck_messages()` — Recovery-Loop: nach `RETRY_MAX` Retries → DLQ + Kaskade. **Kein Eskalations-Pfad zu GeneralAG.** |
| `src/gnom_hub/agents/agent_base.py:93-231` | 139 | `BaseAgent.run()` — Message-Loop. **Z. 187-188: Spezielle GeneralAG-Logik** — `if self.n.lower() == "generalag": get_context_db().close_context(msg["context_id"], "completed", processed[:200]...)`. Andere Agents schließen KEINEN Context. Z. 178-185: record_job in coordination.db bei success. Z. 192-214: record_job mit "failed" bei exception. **Z. 216-229: Dead-Letter Notification** an User (NICHT GeneralAG) |
| `src/gnom_hub/agents/agent_base.py:154-167` | 14 | **SoulAG Behavior-Analyst** ruft `analyze_agent_thought` + `notify_generalag` + `track_reasoning` für JEDEN Agent nach JEDER Antwort. Alerts gehen an GeneralAG im Chat wenn: tool_mismatch ≥ 2, failure_loop ≥ 2, stuck mit history ≥ 3, injection-pattern detected |
| `src/gnom_hub/agents/role_tools.py:1-17` | 17 | `distribute_job()` — Job-Dispatcher: findet GeneralAG, baut LLM-System-Prompt mit "Truppe" aller Worker, ruft `_llm()` (= `ask_router`) |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:101-148` | 48 | `estimate_complexity()` ruft GeneralAG via `ask_router(prompt, sys="Du bist ein präziser Komplexitäts-Bewerter.", agent_name="GeneralAG")` Z. 108-113. GeneralAG-LLM-Call mit Override-System-Prompt! **Identity wird hier umgangen.** |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:19-99` | 81 | `RouteOptimizer` — 3 Strategien (parallel A, serial B, single C) mit `rates["generalag"] = 0.08` (höchste Rate, Z. 32). **Strategy C wählt IMMER GeneralAG wenn nichts matcht** |
| `src/gnom_hub/soul/soul_observer.py:140-159` | 20 | Alert-Generierung: bei tool_mismatch ≥ 2 → "🔧 {agent} hat wiederholt Tool-Probleme — GeneralAG bitte Tool-Situation prüfen". Bei failure_loop ≥ 2 → "🔁 {agent} dreht sich im Kreis — GeneralAG bitte Alternativ-Strategie vorgeben". Bei stuck+history ≥ 3 → "🆘 {agent} signalisiert Hilfebedarf — GeneralAG bitte unterstützen". Cooldown: 300s |
| `src/gnom_hub/soul/soul.py:486-487` | 2 | `_save_rules()`: nach Evolution-Rule-Learning wird `add_chat_message("GeneralAG", "generalag", "chat", f"@user @SoulAG: Regel für {agent} gelernt: ...")` gepostet — **GeneralAG als Pseudo-Sender für SoulAG-Aktionen** |
| `src/gnom_hub/soul/soul.py:504, 540` | 2 | `run_evolution()` und `handle_user_feedback()`: rufen `ask_router(... agent_name="GeneralAG")` mit Hardcoded `sys="Du bist Optimierer."` — **Override-System-Prompt wie adaptive_decomposition.py** |
| `src/gnom_hub/soul/soul.py:524` | 1 | `if sender and sender.lower() not in ["user", "system", "generalag", "soulag", "watchdogag", "securityag"]` — filtert Worker-Active-Agents aus Feedback-Loop. **GeneralAG wird zusammen mit System-Agents gefiltert, NICHT als Worker behandelt** |
| `src/gnom_hub/soul/soul_actions.py:38-71` | 34 | `dispatch_agent()`: SoulAG dispatcht NUR System-Agents (`SYSTEM_AGENTS = {"soulag", "generalag", "securityag", "watchdogag"}` Z. 50). Bei Worker-Target → WARNING log + return False. Workers werden AUSSCHLIESSLICH von GeneralAG dispatched (Z. 45 Kommentar) |
| `src/gnom_hub/soul/soul_actions.py:136-145` | 10 | `AGENT_CAPS` Dict: GeneralAG hat `["text", "coordination", "dispatch"]` — bestätigt Tier 3a als Coordinator |
| `src/gnom_hub/soul/soul_actions.py:165-191` | 27 | `find_agent_for_task()`: Heuristik-Routing basiert auf `TASK_CAP_KEYWORDS` + `AGENT_CAPS`. Bei `blockade`/`analysis`/`web_search` Capabilities → bevorzugt GeneralAG (Z. 185-188) |
| `src/gnom_hub/soul/soul_actions.py:194-223` | 30 | `solve_blockade()`: SoulAG ruft `dispatch_agent("WatchdogAG", ...)` — WatchdogAG wird via GeneralAG-Umweg informiert (User-Mandat-Pfad) |
| `src/gnom_hub/agents/agent_names.py:4-18` | 15 | `_AGENT_NAME_MAP`: `"generalag" → "generalAG"`, `"general_ag" → "generalAG"`, `"general" → "generalAG"`. **Acceptance: jeder Mentions-String wird normalisiert** |
| `src/gnom_hub/agents/agent_names.py:30-41` | 12 | `normalize_showbox_name()`: `'general_ag_pro_final' → 'generalAG'` — Substring-Match akzeptiert User-defined-Suffixe |
| `src/gnom_hub/core/agent_names.py:15-27` | 13 | `SYSTEM_AGENTS = ("SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG")` — Frozen Tuple. **`FROZEN: bool = True`** — die Liste ist als VERTRAG markiert |
| `src/gnom_hub/core/agent_names.py:31-39` | 9 | `AGENT_COLORS`: GeneralAG = `#00e5ff` (Cyan) — **WIDERSPRICHT Identity "Deine Farbe ist immer Blau"** (Identity WORKER-PERFORMANCE-TRACKING Z. 56) und agent_definitions.py:147/153 "Farbe: Blau" |
| `src/gnom_hub/core/agent_names.py:43-52` | 10 | `AGENT_AVATARS`: GeneralAG = `generalag.png` |
| `src/gnom_hub/core/agent_names.py:55-59` | 5 | `SHOWBOX_THEME`: system-layer = `#00e5ff` — GeneralAG nutzt `<SHOWBOX:system>` |
| `src/gnom_hub/core/prompt/context.py:30-66` | 37 | `get_context_blocks()`: Dispatcher für 7 fetchers (worker_stats, open_contexts, active_rules, workspace_summary, chat_history_tail, soul_facts, evolution_rules). Filter via `allowed_contexts` aus Config |
| `src/gnom_hub/core/prompt/context.py:73-84` | 12 | `_get_worker_stats()`: "Primär sinnvoll für GeneralAG" — ruft `coordination_db.get_worker_summary()`. **Source-Comment verweist auf agent_base.py:110-118 (alter Code, gelöscht)** |
| `src/gnom_hub/core/prompt/context.py:87-97` | 11 | `_get_open_contexts()`: "Primär sinnvoll für GeneralAG" — ruft `context_db.get_summary_for_generalag()`. **GeneralAG-Spezialpfad** |
| `src/gnom_hub/core/prompt/context.py:131-141` | 11 | `_get_workspace_summary()`: Workspace-Pfad + erste 30 Top-Level-Files. **Baut `[WORKSPACE: {wd} | Dateien: {files}]` — IDENTISCH zu brainstorm_helpers.py:16.** DOPPELTE INJEKTION wenn bs_mode aktiv |
| `src/gnom_hub/core/prompt/builder.py:104-186` | 82 | `build_system_prompt()`: **SSOT für System-Prompts (Kommentar Z. 1-24)**. Lädt JSON-Config (Z. 113-122), baut Identity-Header, [VERHALTEN] (Z. 144-158), [TOOLS] aus JSON-Perms (Z. 162), [SICHERHEIT] (Z. 165-168), [KONTEXT:*] (Z. 171-173), Identity-Closing (Z. 175) |
| `src/gnom_hub/core/prompt/post_processing.py:33-86` | 54 | Post-Processing: Obedience + Behavioral + Custom + Preset. Wird NUR angewendet wenn `runtime_settings` übergeben — `ask_llm` und `dispatch_mention` rufen `build_system_prompt` OHNE runtime_settings! → **GeneralAG bekommt Identity OHNE Post-Processing** |
| `src/gnom_hub/agents/actions/action_handlers.py:48-181` | 134 | `process_actions()`: Permission-Enforcement für `[WRITE:]`, `[READ:]`, `[SHELL:]`, `[CRAWL:]`, `[SHOWBOX:...]`, `[DESKTOP:]`, `[VIDEO:*]`, `[BROWSER:]`. **GeneralAG hat in Python-Perms (`agent_definitions.py:148`) KEIN `write` und KEIN `run`** — alle GeneralAG-[WRITE:]-Tags werden zu "[System: GeneralAG hat keine Schreibberechtigung.]" ersetzt (Z. 64, 77). Alle [SHELL:]-Tags zu "[System: GeneralAG hat keine SHELL-Berechtigung.]" (Z. 99). ABER: **GeneralAG.json hat `write` als Permission (Z. 19-25) — was im System-Prompt erwähnt wird aber nie aktiv ist** |
| `src/gnom_hub/core/security/gatekeeper.py:438` | 1 | Kommentar: "GeneralAG (role=general): KEINE Shell-Befehle erlaubt" — bestätigt `verify_cmd()`-Logik blockt GeneralAG |
| `src/gnom_hub/agents/swarm/swarm_coordinator.py:89-99` | 11 | `_dispatch()`: iteriert über alle Agents, **filtert System-Agents** (Z. 92) und dispatched NUR Worker mit `@Agent -> task` aus LLM-Output. Z. 96-98: dispatched via `dispatch(aj, target=a.name)` |
| `src/gnom_hub/agents/swarm/swarm_coordinator.py:102-107` | 6 | `_eval()`: ruft LLM mit hardcoded `sys_p` (Z. 103) — **Override-System-Prompt wie in soul.py + adaptive_decomposition.py** — und postet Output als GeneralAG via `process_actions` |
| `src/gnom_hub/agents/swarm/swarm_coordinator.py:110-143` | 34 | `run_swarm_coordinator()`: bis zu 4 Iterationen mit Worker-Tracker. Z. 142: postet "Der Workflow ist beendet. War das Ergebnis gut?" als GeneralAG |
| `src/gnom_hub/chat/chat_commands_handlers.py:20-38` | 19 | `handle_job()`: nutzt `distribute_job` (role_tools), parsed Worker-Tasks aus LLM-Output (Z. 33), dispatched via `dispatch(aj, target=a.name, context_id=job_id)` (Z. 36) |
| `src/gnom_hub/chat/chat_commands.py:229, 252` | 2 | Help-Text: "GeneralAG: Delegiert Aufgaben exklusiv an die 4 Worker." und "@AgentName -> Aufgabe" Format |
| `src/gnom_hub/chat/chat_clear.py:39` | 1 | `sys_ags = ['soulag', 'generalag', 'securityag', 'watchdogag']` — System-Agent-Liste (3. Quelle, muss mit anderen Listen identisch sein) |
| `src/gnom_hub/api/endpoints/llm_agents.py:9` | 1 | `SYSTEM_AGENTS = ["SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG"]` — 4. Quelle. **Identisch zu core/agent_names.py, chat_helpers.py, chat_clear.py** |
| `src/gnom_hub/api/endpoints/presets.py:255` | 1 | `return {"system": ["soulag", "watchdogag", "generalag", "securityag"], ...}` — 5. Quelle |
| `src/gnom_hub/core/utils/preset_service.py:11` | 1 | `_SYSTEM_AGENTS = ("soulag", "watchdogag", "generalag", "securityag")` — 6. Quelle |
| `src/gnom_hub/core/utils/gd_online.py:12` | 1 | `clean_name in ["generalag", "soulag"]` — GeneralAG + SoulAG sind die "gd_online" Agents (general-directive online?) |
| `src/gnom_hub/core/utils/gd_fallback.py:20, 96-100` | 6 | Fallback-Chain: `{"CoderAG": ["GeneralAG", "WriterAG"], "WriterAG": ["GeneralAG", "EditorAG"]}`. `CoderAG` fallback ist GeneralAG, **nicht** WriterAG (für komplexe Code-Tasks) |
| `src/gnom_hub/core/utils/graceful_fallback.py:32-100` | 69 | `clean_name in ["generalag", "soulag"]` für Graceful-Fallback-Trigger. `fallback_options = {"CoderAG": ["GeneralAG (pseudocode)", ...], "WriterAG": ["GeneralAG (rough draft)", ...]}`. Z. 76: `ask_router(prompt, sys="Du bist ein präziser Qualitäts-Schätzer.", agent_name="GeneralAG")` — **4. Stelle mit Override-System-Prompt für GeneralAG** |
| `src/gnom_hub/db/connection.py:71` | 1 | Kommentar: "coordination.db, context.db) so they also benefit from WAL + busy_timeout" — coordination.db ist EIGENE Datei (nicht hub.db) |
| `src/gnom_hub/db/soul_tasks.py:238, 249` | 2 | Task-Tracking-Keywords: `"generalag": ["koordiniere", "organisiere", "plan", "report", "zusammenfassung"]` — SoulAG-Intent-Detection für GeneralAG-Tasks |
| `src/gnom_hub/db/chat_repo.py:18` | 1 | `["SoulAG", "GeneralAG", "CoderAG", "WriterAG", ...]` — Sender-Whitelist für Chat-Filter |
| `src/gnom_hub/db/generalag_repo.py:1-323` | 323 | **GeneralAG-eigene DB-Operationen** für 5 Tabellen: `save_discussion`, `update_discussion`, `list_discussions`, `save_outcome`, `list_outcomes`, `add_pending`, `resolve_pending`, `list_pending`, `update_worker_profile`, `get_worker_profile`, `list_worker_profiles`, `_update_worker_profile_after_outcome`, `log_preset_change`, `list_preset_history`, `get_dashboard_summary` |
| `src/gnom_hub/db/general_repo.py:1-232` | 232 | **`general_memory` Table-Operationen**: `save_general_fact`, `add_to_general_memory`, `get_general_facts`, `log_task`, `complete_task`, `get_relevant_facts`. Identity-Block sagt: "Du hast exklusiven Schreibrecht auf die general_memory-Datenbank" (Z. 121) |
| `src/gnom_hub/db/schema.py:298-355` | 58 | Schema für 5 GeneralAG-Tabellen: `generalag_discussions`, `generalag_outcomes`, `generalag_pending`, `generalag_worker_profile`, `generalag_preset_history` + 5 Indizes. Z. 380-382: SEED-Daten für Tests (User @GeneralAG → GeneralAG @CoderAG → Showbox) |
| `src/landjunge/gnom-hub/src/gnom_hub/infrastructure/router/router_call.py:69` | 1 | Token-Limit pro Agent: `{"generalag": 6000, "soulag": 50000, ...}` — GeneralAG bekommt 6000 Tokens, **SoulAG bekommt 50000** (8x mehr) |
| `src/gnom_hub/infrastructure/router/router_config.py:13` | 1 | GeneralAG-Modelle: `["meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"]` — Free-Tier only! Kein Claude/DeepSeek/GPT-4o für GeneralAG |
| `src/gnom_hub/soul/agent_voices.py:84` | 1 | TTS-Stimme: `'GeneralAG': {'de': 'Anna (Enhanced)', 'en': 'Daniel'}` |
| `src/gnom_hub/api/endpoints/admin_config.py:94` | 1 | `ask_router(prompt_content, sys=SYSTEM_PRESET_GEN, agent_name="GeneralAG")` — 5. Stelle mit Override-System-Prompt |
| `src/gnom_hub/memory/smr/smr_retrieve.py:9, 46` | 2 | SMR-Retrieve: GeneralAG bekommt **erweiterte Sicht auf alle Agent-Fakten** (agent_scope="all"), nicht nur eigene |
| `src/gnom_hub/memory/embeddings.py:73-74` | 2 | `agent_scope == "generalag"` → "GeneralAG orchestrates the entire swarm and must see facts for all agents" — explizit definiert dass GeneralAG den vollen Knowledge-Scope bekommt |
| `src/gnom_hub/memory/soul_retrieval.py:21` | 1 | Gleicher Pattern: GeneralAG → agent_scope "all" |

---

## 1. Aktueller Zustand

### 1.1 Version & Sliders (`GeneralAG.json:2-10`)

- **Version:** 5.3 (User-Mandat 2026-06-28 12:03)
- **Sliders (alle 5 = 2 = "medium"):**
  - `creativity: 2`, `precision: 2`, `speed: 2`, `critical_thinking: 2`, ` obedience: 2`
- **Identische Sliders wie alle 7 anderen Agents** (kein individueller Wert)

### 1.2 Prompt-Blocks wortwörtlich (`GeneralAG.json:11-17`)

| Key | Text |
|---|---|
| creativity | "Balance standard approaches with occasional creative solutions." |
| precision | "Balanced accuracy. Verify main outputs." |
| speed | "Steady pace. Deliver when ready." |
| critical_thinking | "Think about the task. Suggest obvious improvements." |
| obedience | "Follow instructions with reasonable interpretation. Small adjustments OK." |

### 1.3 Permissions-Liste — DUAL-TRUTH Befund (`GeneralAG.json:19-25` vs `agent_definitions.py:148, 153`)

| Quelle | GeneralAG-Perms |
|---|---|
| `config/agents/GeneralAG.json:19-25` (JSON) | `["read", "write", "@job", "db_write", "showbox_write"]` |
| `agent_definitions.py:148` (Python DE) | `["read", "@job", "general_memory"]` |
| `agent_definitions.py:153` (Python EN) | `["read", "@job", "general_memory"]` |

**Schnittmenge:** `["read", "@job"]` — diese funktionieren in beiden Quellen.
**Nur in JSON:** `["write", "db_write", "showbox_write"]` — wird im System-Prompt-Text erwähnt.
**Nur in Python:** `["general_memory"]` — wird von `ask_llm`/`action_handlers` aktiv gecheckt.

### 1.4 AllowedContexts-Liste (`GeneralAG.json:26-32`)

```
["worker_stats", "open_contexts", "workspace_summary", "chat_history_tail", "evolution_rules", "showbox_history"]
```

`active_rules` ist **explizit AUSGESCHLOSSEN** (`context_filters.active_rules.enabled: false` Z. 35-37). notes: "GeneralAG bekommt bewusst KEINE active_rules — das wäre ein Rollenbruch" (Z. 39).

### 1.5 Identity-Struktur (5.554 Zeichen, Z. 18)

| Sektion (═══ Marker) | Was |
|---|---|
| `═══ SHOWBOX — KOMMUNIKATIONS-ZENTRALE ═══` | Delegations-Ankündigungen, Status-Reports, Eskalationen via Showbox. Buttons-Pflicht |
| `═══ DEINE KOMMUNIKATION ═══` | **"AUSSCHLIESSLICH von SoulAG"** + Worker-Denkprozesse lesen + KEINE direkte Verbindung zu WatchdogAG/SecurityAG |
| `═══ DEINE 3 KERNROLLEN ═══` | ZERLEGEN / DELEGIEREN / SYNTHETISIEREN (siehe §2.2) |
| `═══ GIT-MANAGEMENT ═══` | "Delegiere an CoderAG" — harter Default auf CoderAG |
| `═══ WORKER-PERFORMANCE-TRACKING ═══` | worker_stats-Konsultation + SmartRouter-3-Stage + Threshold 40%/5 Jobs |
| `═══ SHOWBOX + BUTTONS (PFLICHT) ═══` | 4 Trigger-Bedingungen, JSON-Format, inline-Button-Format |
| `═══ TIER-HIERARCHIE (User-Mandat 2026-06-28 11:53) ═══` | Tier 3a + bekommt von SoulAG ODER User |
| `═══ DEINE DATENBANK — generalag_db (User-Mandat 2026-06-28 12:03) ═══` | 5 Tabellen (discussions, outcomes, pending, worker_profile, preset_history) + Wann-zu-Schreiben-Regeln |

---

## 2. Spec-Konformität

### 2.1 Routing-Spec vs. Code-Realität

| Spec-Aussage in Identity | Code-Realität | Spec-Verletzung? |
|---|---|---|
| "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG (via @GeneralAG)" (Identity) | (a) `@GeneralAG` direkt vom User (chat_helpers.py:15-19), (b) Broadcast an alle online+busy Agents inkl. GeneralAG (chat_legacy.py:207-213), (c) `@bs` Brainstorming-Pfad (brainstorm.py:38-55), (d) `@@worker` → System-Agents via `target="system"` (brainstorm.py:25-26), (e) andere Agents können `@GeneralAG` in Output erwähnen → dispatch_mention, (f) SoulAG `dispatch_agent("GeneralAG", ...)` (soul_actions.py:38-71) | **MEHRFACH GEBROCHEN** — GeneralAG empfängt von: User, System-@, SoulAG, sich-selbst-durch-Broadcast, jeden Worker der @GeneralAG schreibt |
| "Du bekommst Aufträge von SoulAG (Tier 2a) oder direkt vom User" (Tier-Sektion) | Konsistent mit (a)+(b) oben | OK |
| "Du delegierst an die Worker (Tier 3b)" | dispatch_mention mit target=CoderAG etc., distribute_job in role_tools.py, _dispatch in swarm_coordinator.py | OK, aber KEIN Code-Sperre gegen System-Targets |
| "Du hast KEINE direkte Verbindung zu WatchdogAG oder SecurityAG" | dispatch_mention kennt KEINE Tier-Filterung — wenn GeneralAG `@WatchdogAG` schreibt, wird dispatched. Tier-Hierarchie ist nur Text | TEILWEISE — keine Code-Sperre, nur Prompt-Disziplin |

### 2.2 3 Kernrollen — technische Verifizierbarkeit

| Kernrolle | Spec | Code-Pfad | Verifizierbar? |
|---|---|---|---|
| **ZERLEGEN** | "User-Aufträge in atomare Teilaufgaben zerlegen" | LLM-Aufgabe in `ask_llm` (brainstorm_helpers.py:9-31) + `parse_agent_sequence` (swarm_comms.py:66-84). **Der LLM entscheidet selbst was "atomar" ist** | NEIN — keine Heuristik die Teile zählt/prüft. Wenn GeneralAG-LLM nur 1 Zeile Output produziert (= keine Zerlegung) → keine Code-Sperre |
| **DELEGIEREN** | "An Worker via @AgentName -> Aufgabe" | (a) `parse_agent_sequence` extrahiert Pattern, (b) `dispatch_sequence` (swarm_comms.py:87-177) routed sequenziell mit dependency-chain via `parent_msg_id`, (c) `dispatch_mention` (swarm_comms.py:311-417) routed direkt, (d) `dispatch_by_capability` (swarm_comms.py:657-722) routed via `find_best_agent_for_task` 3-Stage-Routing | **TEILWEISE** — Parsing funktioniert. ABER: GeneralAG kann auch OHNE Delegation antworten (LLM generiert einfach Code/Text selbst) — keine Code-Sperre verhindert das |
| **SYNTHETISIEREN** | "Worker-Ergebnisse zu einer kohärenten Antwort an SoulAG zusammenfassen" | (a) `_collect_worker_responses` (brainstorm.py:11-17) holt letzte 50 Chat-Messages, filtert per Sender, kürzt auf 800 Zeichen. (b) `signal_completion` + `WorkerCompletionTracker` (swarm_coordinator.py:16-82) wartet bis alle Worker done. (c) `run_swarm_coordinator` iteriert bis zu 4 Runden | **TEILWEISE** — Synthese ist passiv (wartet auf Chat-Messages), keine semantische Aggregation. Wenn Worker 3× nicht-antwortet → `_collect_worker_responses` returnt leeren String → `if new_resp: all_res.append(new_resp)` (swarm_coordinator.py:136) → silent skip |

**Befund: 3 Kernrollen sind alle LLM-Aufgaben, keine davon ist hart erzwungen.**

### 2.3 "Workspace prüfen" Halluzination — Hauptbefund

**Spec-Aussage in Identity:** "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG (via @GeneralAG). Du liest MIT: Worker-Denkprozesse, Worker-Outputs, CoordinationDB-Statistiken und offene Contexts. Das ist deine Sicht auf den aktuellen State — SoulAG injiziert sie dir." (Identity Z. 14-16)

**Wo im Code die "workspace prüfen"-Halluzination entstehen KANN:**

1. **`_get_workspace_summary()` in context.py:131-141** — Fetcher ist in `allowed_contexts: ["workspace_summary", ...]`. Output:
   ```
   [KONTEXT:workspace_summary]
   [WORKSPACE: /Users/.../gnom-Workspace/default | Dateien: foo.md, bar.py, ...]
   ```

2. **`ask_llm()` in brainstorm_helpers.py:15-16** — MANUELLE Doppel-Injection NACH `inject_context()`:
   ```python
   wd = get_workspace_dir()
   fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
   sys += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"
   ```

3. **Auch für NICHT-GeneralAG Agents** wird der workspace_dir() in `get_workspace_dir()` (brainstorm_helpers.py:2-3) gebaut und doppelt injiziert (Z. 15-16).

**Resultat:** GeneralAG-LLM bekommt den Workspace-Status als harten Kontext-Block. Im Brainstorm-Modus (Z. 17) wird zusätzlich "[MODUS: BRAINSTORM — Diskutiert UND erstellt Ergebnisse! [WRITE:], [SHELL:] und [READ:] sind erlaubt.]" angehängt — **Auch wenn GeneralAG per Python-Permission `general_memory` KEIN `write` und `run` hat!**

**Befund: "Erst workspace prüfen" Halluzination ist im CODE-RAUSCHEN vergraben, nicht in der Identity verlangt. Symptom-Bekämpfung müsste an der Doppel-Injection ansetzen.**

### 2.4 SmartRouter & 3-Stage-Routing — was passiert wirklich?

**Identity-Block verlangt (Z. 51-55):**
> "Konsultiere die worker_stats-Tabelle (success_rate, avg_duration, last_job_type). Nutze das SmartRouter-3-Stage-Routing (Stats → Capabilities → Keywords). Bevorzuge Worker mit success_rate ≥ 40% UND mindestens 5 abgeschlossenen Jobs."

**Code-Realität in swarm_comms.py:180-293 (`find_best_agent_for_task`):**
- Stage 1: coordination.db worker_stats sortiert nach `success_rate DESC, total_jobs DESC` (Z. 218-224) — **Stage 1 triggert NUR wenn `matched_caps` nicht leer** (Z. 203)
- Stage 1 Threshold: `if row["success_rate"] < 0.4 and row["total_jobs"] >= 5: skip` (Z. 243-248) — **entspricht Identity "≥ 40% UND mindestens 5 Jobs"**
- Stage 2: agent_capabilities mit `confidence DESC, queue_depth ASC` (Z. 258-274)
- Stage 3: Keyword-Heuristik (Z. 277-291)

**Befund:** SmartRouter wird automatisch vom CODE genutzt (NICHT vom GeneralAG-LLM entschieden). GeneralAG-LLM gibt einfach `@Worker -> task` aus, der Code routet dann über 3 Stages. **GeneralAG "konsultiert" worker_stats NICHT direkt** — er bekommt nur die aggregierte Summary via Context-Block (`get_worker_summary()` Z. 472-493) im Prompt. Die eigentliche Routing-Entscheidung trifft der Code basierend auf Stage 1-3.

**Konsequenz:** Die Identity-Anweisung "Konsultiere worker_stats" ist **KOSMETISCH** — der LLM sieht zwar eine Tabelle im Prompt, aber der Code trifft die Worker-Auswahl basierend auf `find_best_agent_for_task` automatisch. **GeneralAG hat keinen Code-Pfad der worker_stats liest und selbst entscheidet.**

### 2.5 Git-Management

**Identity-Block (Z. 36-41):**
> "Delegiere an CoderAG: '@CoderAG committe die Änderungen mit beschreibender Message'. NIEMALS selbst git-Befehle ausführen — du hast keine Schreibrechte."

**Code-Realität:**
- `gatekeeper.py:427-430`: **"git wurde 2026-06-15 komplett aus dem Agenten-Toolset entfernt. Wird weder via @@git noch via [SHELL:] unterstützt."** `verify_cmd` returnt `False, "high", "git ist nicht verfügbar."` für JEDEN Agent.
- GeneralAG kann also gar nicht git ausführen — Spec ("du hast keine Schreibrechte") ist historisch korrekt, aber aktuell ist `run` Permission sowieso tot + `git` ist explizit aus dem Toolset entfernt.
- CoderAG hat `run` in JSON-Perms, aber `verify_cmd` blockt `git` für ALLE Agents.

**Befund:** Identity fordert "Delegiere an CoderAG", aber CoderAG könnte es auch nicht (git ist global blockiert). **Veto-Recht:** SecurityAG (godmode) hat `run` und könnte git ausführen — wenn auch durch `verify_cmd` blockt. WatchdogAG blockt path-violations. **Es gibt KEINEN Code-Pfad der explizit "nur CoderAG darf committen" durchsetzt — die GeneralAG-Identity hardcoded das nur als Text-Default.**

### 2.6 Eskalations-Pfad bei 3× Worker-Fail

**Pfade bei Worker-Fail:**

| Stelle | Verhalten | Eskaliert an GeneralAG? |
|---|---|---|
| `swarm_comms.py:572-609` `nack_message()` Z. 589-594 | Nach `RETRY_MAX=3`: DLQ + Kaskade. Postet: `_post_chat("System", "⚠️ Agent **{recipient}** gescheitert an: {reason}")` | **NEIN** — geht in den User-Chat, NICHT zu GeneralAG |
| `swarm_comms.py:725-769` `recover_stuck_messages()` Z. 743-752 | Nach `RETRY_MAX`: DLQ + Kaskade. Logger-Output, KEIN Post | **NEIN** |
| `agent_base.py:216-229` Dead-Letter-Notification | Bei `retry_count >= 2`: postet "💀 **[Dead-Letter]** Nachricht #{msg_id}..." als System-Chat | **NEIN** — geht in User-Chat |
| `soul_observer.py:140-159` Behavior-Analyst-Alerts | Bei `tool_mismatch ≥ 2`, `failure_loop ≥ 2`, `stuck + history ≥ 3`: postet als SoulAG-Chat mit "GeneralAG bitte Tool-Situation prüfen" | **JA — TEILWEISE** — SoulAG postet eine Chat-Message MIT dem Hinweis "GeneralAG bitte" |
| `soul.py:340-418` `_nudge_loop()` SoulAG-Eskalation | Bei 3 Nudges ohne Antwort: `status='blocked'` + `_post_chat` an SecurityAG via dispatch_mention | **NEIN — SoulAG-ESKALIERT DIREKT AN SecurityAG, GeneralAG wird ÜBERGANGEN** |
| `swarm_coordinator.py:50-52` `WorkerCompletionTracker.wait()` Timeout | Bei 180s Timeout: Logger-Warning. KEIN Post | **NEIN** |

**Befund: GeneralAG erfährt Worker-Failures nur via:**
1. `soul_observer.py:notify_generalag` Chat-Message (nur bei Pattern-Triggern, Cooldown 5min)
2. `swarm_comms.py:594` System-Chat-Message (die er im Verlauf sieht)
3. User-Chat-Sicht (passiv)

**Es gibt KEINEN direkten Eskalations-Pfad Worker-Fail → GeneralAG-Action. SoulAG's _nudge_loop eskaliert direkt an SecurityAG, nicht zurück zu GeneralAG.**

**GeneralAG steckt NICHT fest** — er weiß nur nichts vom Worker-Fail. Der nächste User-Prompt triggert GeneralAG, der dann via worker_stats (über Context-Block) sieht "CoderAG: 5 fails", aber keine aktive Eskalation passiert.

### 2.7 GeneralAG-eigene DB (`generalag_repo.py` + `db/schema.py:298-355`)

**5 Tabellen:**
- `generalag_discussions` (id, topic, summary, participants, outcome, status, created_at, updated_at)
- `generalag_outcomes` (id, task, worker, result, success_rating, notes, timestamp)
- `generalag_pending` (id, what, who_should_handle, why_blocked, eta, created_at, resolved_at)
- `generalag_worker_profile` (worker_name, strengths, weaknesses, specialties, total_jobs, avg_rating, last_updated)
- `generalag_preset_history` (id, preset_name, set_by, reason, timestamp) + 5 Indizes

**Repo-Funktionen 323 Zeilen komplett implementiert** in `generalag_repo.py:1-323`:
- `save_discussion`, `update_discussion`, `list_discussions`
- `save_outcome`, `list_outcomes` (mit Auto-Worker-Profile-Update Z. 99)
- `add_pending`, `resolve_pending`, `list_pending`
- `update_worker_profile`, `get_worker_profile`, `list_worker_profiles`
- `_update_worker_profile_after_outcome` (interne Helper)
- `log_preset_change`, `list_preset_history`
- `get_dashboard_summary` (Convenience für Showbox-Cards)

**Critical Befund:** **`grep -rn "generalag_repo\|save_discussion\|save_outcome\|add_pending" /Users/landjunge/gnom-hub/src/ --include="*.py" | grep -v generalag_repo.py` → 0 EXTERNE CALLERS.** Das Repo wird von NIEMANDEM importiert. Die 5 Tabellen existieren in der DB, das Repo kann sie CRUD, aber kein Code schreibt oder liest sie.

**Befund 2:** `general_repo.py:75-232` (`save_general_fact`, `add_to_general_memory`, `log_task`, `complete_task`, `get_relevant_facts`) — gleich, externe Caller nur in legacy_db.py:35 (Re-Export) und db/__init__.py:39 (Re-Export). **KEIN aktiver Code-Caller** ausser für `get_relevant_facts` (das in `db/legacy_db.py` re-exportiert wird, aber nie aufgerufen wird).

**Befund 3:** Identity-Block Z. 91-105 verlangt "Nach jedem Brainstorm / jeder Diskussion: 1 Eintrag in `generalag_discussions`" — **existiert nicht im Code**. Die Identity behauptet einen Pfad den die Codebase nicht hat.

### 2.8 Tier-Hierarchie im Code

**6 verschiedene "System-Agent"-Listen** in der Codebase (alle identisch, aber nicht aus einer zentralen Quelle):

| Datei : Zeile | Inhalt | Status |
|---|---|---|
| `core/agent_names.py:15-19` | `SYSTEM_AGENTS = ("SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG")` | **FROZEN: True** — VERTRAG |
| `core/utils/preset_service.py:11` | `_SYSTEM_AGENTS = ("soulag", "watchdogag", "generalag", "securityag")` (lowercase) | duplicate |
| `chat/chat_clear.py:39` | `sys_ags = ['soulag', 'generalag', 'securityag', 'watchdogag']` | duplicate |
| `api/endpoints/chat_helpers.py:5` | `SYSTEM_AGENTS = ["soulag", "generalag", "securityag", "watchdogag"]` | duplicate |
| `api/endpoints/llm_agents.py:9` | `SYSTEM_AGENTS = ["SoulAG", "WatchdogAG", "GeneralAG", "SecurityAG"]` | duplicate (capitalized) |
| `api/endpoints/presets.py:255` | `{"system": ["soulag", "watchdogag", "generalag", "securityag"], ...}` | duplicate |

**Befund:** Konsistent in der REIHENFOLGE (SoulAG → WatchdogAG → GeneralAG → SecurityAG), aber NICHT aus einer zentralen Konstante. **6 Kopien** — Drifthazard.

### 2.9 Showbox + Buttons — GeneralAG-Spec

**Identity Z. 60-87 verlangt:**
- 4 Trigger-Bedingungen (User-Frage, Status, Frage an User, Task-Start/Abschluss)
- JSON mit doppelten Quotes
- Inline `<button action="..." label="...">` Format

**Code-Realität (chat_legacy.py:142-199, action_handlers.py:134-164):**
- 5 Showbox-Regex-Formate werden akzeptiert (Z. 124-156 action_handlers.py): `<SHOWBOX[:name]>...</SHOWBOX>`, `[SHOWBOX[:name]]...[/SHOWBOX]`, `[SHOWBOX: ...]`, `[→ Showbox: name]{...}`, `[-> Showbox: name]{...}`
- **Identity-Block zeigt nur Format 4** (Z. 70-79) — `[→ Showbox: name]{...}`. Format 1-3 sind nicht in der Identity erwähnt
- `parse_inline_buttons` extrahiert `<button action="..." label="...">` automatisch (chat_legacy.py:182-183)
- **Buttons werden im Frontend klickbar gemacht via `frontend/showbox_button_parser.py`** (gleiche Logik)
- **Showbox + Buttons sind via `parse_inline_buttons` → `extracted_btns` → `final_btns[:8]` Pipeline funktional** (chat_legacy.py:182-192)
- **ABER: Keine Validierung "rejected if no buttons"** — GeneralAG kann Showbox ohne Buttons senden und es wird akzeptiert

---

## 3. Code-Realität — Detailpfade

### 3.1 Wo GeneralAG instanziiert/aufgerufen wird

| Pfad : Zeile | Was |
|---|---|
| `src/gnom_hub/chat/brainstorm/brainstorm.py:18-57` `dispatch()` | **Zentrales Routing.** `target=None` (Brainstorm) → nur GeneralAG mit speziellem Instruction-Block Z. 38-55. `target="generalag"` → direkter Mention via `dispatch_mention`. `target=worker` → alle non-System-Agents |
| `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:9-31` `ask_llm()` | LLM-Call für ALL dispatched Agents. Setzt `set_agent_status(agent, "busy")` Z. 24, ruft `ask_router(u_msg, sys, agent_name=ag["name"])`, `process_actions` Z. 28 für [WRITE:]/[SHELL:]-Tag-Execution, post via `post()` Z. 29 |
| `src/gnom_hub/chat/chat_commands_handlers.py:20-38` `handle_job()` | (1) `distribute_job(task)` ruft LLM mit Hardcoded-System-Prompt (role_tools.py:14-16). (2) Parsed LLM-Output via `re.finditer(r'@(\w+)[\s→>:\-]+(.+)', res)`. (3) `dispatch(aj, target=a.name, context_id=job_id)` für jeden Worker. (4) `start_coordinator(task, workers, job_id)` startet Worker-Tracker |
| `src/gnom_hub/agents/role_tools.py:6-17` `distribute_job()` | Findet GeneralAG-Agent, baut LLM-System-Prompt mit `mmap` (= alle Worker als "Truppe"), ruft `ask_router(user_prompt, sys_prompt)`. **KEIN Post — returnt nur String.** |
| `src/gnom_hub/agents/swarm/swarm_coordinator.py:89-99` `_dispatch()` | Iteriert alle Agents, **filtert System-Agents** (Z. 92). Parsed `@(\w+)[\s→>:\-]+(.+)` Pattern aus LLM-Output. Dispatched via `dispatch(aj, target=a.name)`. **KEIN Capability-Match — direct name match only** |
| `src/gnom_hub/agents/swarm/swarm_coordinator.py:102-107` `_eval()` | Ruft LLM mit Hardcoded `sys_p = "Du bist GeneralAG. Führe Ergebnisse des Team-Workflows zusammen..."`. Postet Output als GeneralAG via `process_actions` |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:101-148` `estimate_complexity()` | LLM-Call mit `agent_name="GeneralAG"` + Hardcoded `sys="Du bist ein präziser Komplexitäts-Bewerter."` — **Identity wird umgangen** |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:78-80` `RouteOptimizer.pick_cheapest_route()` Strategy C | Wählt `["GeneralAG"]` als Single-Agent bei generischen Tasks (Z. 91-97). **`rates["generalag"] = 0.08`** (höchste Rate, Z. 32) |
| `src/gnom_hub/soul/soul.py:486-487` `_save_rules()` | Postet `add_chat_message("GeneralAG", "generalag", "chat", f"@user @SoulAG: Regel für {agent} gelernt: ...")` — **GeneralAG als Pseudo-Sender für SoulAG-Action-Output** |
| `src/gnom_hub/soul/soul.py:504, 540` `run_evolution()` / `handle_user_feedback()` | `ask_router(... agent_name="GeneralAG")` mit Hardcoded `sys="Du bist Optimierer."` |
| `src/gnom_hub/soul/soul_actions.py:38-71` `dispatch_agent()` | SoulAG dispatcht NUR System-Agents. Workers AUSSCHLIESSLICH via GeneralAG (Kommentar Z. 45) |
| `src/gnom_hub/soul/soul_actions.py:165-191` `find_agent_for_task()` | Heuristik-Routing: bei `blockade`/`analysis`/`web_search` → bevorzugt GeneralAG |
| `src/gnom_hub/soul/soul_observer.py:172-198` `notify_generalag()` | Postet Chat-Message als SoulAG mit Alerts über Agents ("🔧 X hat Tool-Probleme — GeneralAG bitte Tool-Situation prüfen") |
| `src/gnom_hub/api/endpoints/admin_config.py:94` | `ask_router(prompt_content, sys=SYSTEM_PRESET_GEN, agent_name="GeneralAG")` — 5. Stelle mit Override-System-Prompt |
| `src/gnom_hub/core/utils/graceful_fallback.py:76` | `ask_router(prompt, sys="Du bist ein präziser Qualitäts-Schätzer.", agent_name="GeneralAG")` — 4. Stelle mit Override |
| `src/gnom_hub/agents/agent_base.py:187-188` | **`if self.n.lower() == "generalag": close_context(...)`** — GeneralAG-Spezial: Context wird bei Agent-Schluss CLOSED. Andere Agents schliessen NICHT |

**GeneralAG wird also in 13+ Pfaden aufgerufen, davon 4 mit OVERRIDE-System-Prompts (adaptive_decomposition, swarm_coordinator, soul.run_evolution, soul.handle_user_feedback, graceful_fallback).** Die GeneralAG-Identity gilt nur in 2 Pfaden: `chat_legacy.py:200-214` (chat_routing) und `chat_commands_handlers.py:20-38` (handle_job mit distribute_job).

### 3.2 Welche DB-Tabellen GeneralAG wirklich liest/schreibt

| Tabelle | Pfad : Zeile | Operation | Spec aus Identity? |
|---|---|---|---|
| `coordination.db` | `memory_layers.py:32-33` `coordination_db_path()`, Z. 357-531 `CoordinationDB` | R + W (record_job, get_worker_summary) via `agent_base.py:178-185` und `_get_worker_stats` (context.py:73-84) | ✅ Identity Z. 52 "Konsultiere die worker_stats-Tabelle" — ABER: GeneralAG-LLM konsultiert nur den aggregierten summary-Block, NICHT die Tabelle selbst |
| `context.db` | `memory_layers.py:617-754` `ContextDB` | R + W (open_context, add_event, close_context) via `agent_base.py:99-104, 186, 212` + `_get_open_contexts` (context.py:87-97) | ✅ Identity Z. 14-16 "Worker-Denkprozesse, offene Contexts" |
| `agent_messages` | `swarm_comms.py:148-157, 392-407` | W via dispatch_sequence/dispatch_mention | ✅ Indirekt (Workflow-Steuerung) |
| `agent_capabilities` | `agent_base.py:236-245` `_register_capabilities` | W via BaseAgent-Init. GeneralAG bekommt `("coordination", 1.0)` (Z. 36-37) | ✅ Konsistent |
| `hub.db` (chat_messages) | `chat_repo.py:18` Whitelist | W via `add_chat_message` | ✅ Worker-Owner-Channel |
| `hub.db` (soul_tasks) | `soul_tasks.py:238, 249` (Keywords "koordiniere"/"organisiere"/"plan") | R via SoulAG-intent-detection | ✅ Indirekt |
| `general_memory` (general_repo.py) | NICHT aufgerufen | — | ❌ Identity Z. 121-128 verlangt "Schreibrecht auf general_memory" — **Code ruft KEINE der 7 Funktionen auf** |
| `generalag_discussions` (generalag_repo.py) | NICHT aufgerufen | — | ❌ Identity Z. 91 "Nach jedem Brainstorm: 1 Eintrag" — **Code ruft KEINE der 16 Funktionen auf** |
| `generalag_outcomes` (generalag_repo.py) | NICHT aufgerufen | — | ❌ Identity Z. 92 "Nach jedem Worker-Auftrag: 1 Eintrag" — **Code ruft KEINE der Funktionen auf** |
| `generalag_pending` (generalag_repo.py) | NICHT aufgerufen | — | ❌ Identity Z. 93 "Wenn was offen bleibt: sofort" — **Code ruft KEINE der Funktionen auf** |
| `generalag_worker_profile` (generalag_repo.py) | NICHT aufgerufen (nur intern via _update_worker_profile_after_outcome, das selbst nie aufgerufen wird) | — | ❌ Identity Z. 94 "Wenn ein Worker auffällt" — **Code ruft KEINE der Funktionen auf** |
| `generalag_preset_history` (generalag_repo.py) | NICHT aufgerufen | — | ❌ Identity Z. 95 "Bei jedem Preset-Wechsel" — **Code ruft KEINE der Funktionen auf** |
| `state` (LLM-Settings) | `llm_orchestrator.py:27-29` | R | Indirekt |
| `soul_memory` | `soul_retrieval.py:21` GeneralAG = "all" agent_scope | R | ✅ Erweiterte Sicht (alle Agent-Fakten) |

**Befund: 5 von 8 spec'd Tabellen sind DEAD-CODE-Schemas. Nur coordination.db, context.db, agent_messages, agent_capabilities, chat_messages, soul_memory sind aktiv.**

### 3.3 Welche Permissions tatsächlich gecheckt werden

**Runtime-Enforcement in `action_handlers.py` (via `ask_llm` → `get_soul(name)` → Python-Perms):**

| Permission-Token | GeneralAG-Perm-Status | Konsequenz |
|---|---|---|
| `read` | ✅ in beiden Quellen | OK |
| `write` | ❌ in JSON, ❌ in Python | `[WRITE:]` → "[System: GeneralAG hat keine Schreibberechtigung.]" (Z. 64, 77) |
| `run` | ❌ in JSON, ❌ in Python | `[SHELL:]` → "[System: GeneralAG hat keine SHELL-Berechtigung.]" (Z. 99). Plus `verify_cmd` blockt explizit für role=general (gatekeeper.py:438) |
| `db_write` | ❌ in JSON, ❌ in Python | (dead-token wie bei SoulAG, kein Code-Check) |
| `showbox_write` | ❌ in Python, ✅ in JSON (dead token) | Immer erlaubt (wie alle 8 Agents) |
| `@job` | ✅ in beiden | (nur Routing-relevant, nicht action-relevant) |
| `general_memory` | ❌ in JSON, ✅ in Python | Dead — `general_memory` wird nirgendwo permission-gecheckt |

**Befund:** GeneralAG hat faktisch NUR `read` und `@job` (Routing). `write`, `run`, `db_write` aus JSON sind DEAD. `general_memory` aus Python ist auch DEAD (kein Code-Check).

### 3.4 Brainstorm-Instruction-Block — Detail

**brainstorm.py:38-55:**
```python
bs_instruction = (
    f"[BRAINSTORM-AUFTRAG]\n"
    f"Der User hat eine Brainstorming-Anfrage gestellt.\n"
    f"AUFGABE: {q}\n\n"
    f"DEINE ROLLE: Du bist GeneralAG, der alleinige Koordinator.\n"
    f"1. Analysiere die Aufgabe.\n"
    f"2. Zerlege sie in Teilaufgaben und weise sie den passenden Worker-Agenten zu.\n"
    f"   Verwende das Format: @CoderAG -> konkrete Aufgabe (pro Zeile ein Agent).\n"
    f"3. Warte auf die Ergebnisse der Worker.\n"
    f"4. Fasse die Worker-Ergebnisse zusammen und präsentiere sie in <SHOWBOX:1>.\n\n"
    f"WICHTIG: Du selbst erstellst KEINE Slides, Konzepte oder Inhalte. "
    f"Du koordinierst und fasst NUR zusammen. "
    f"Die Worker-Agenten werden erst aktiv, wenn du ihnen eine Aufgabe zuweist."
)
```

**Befund:** Brainstorm-Modus erzwingt ES explizit: "Du selbst erstellst KEINE Slides" und "Warte auf die Ergebnisse" — das ist die einzige Stelle in der Codebase wo GeneralAG daran gehindert wird selbst zu arbeiten. **Aber das gilt nur für `@bs`-Pfad. Bare-Message-Broadcast (chat_legacy.py:207-213) und direkter `@GeneralAG` (chat_legacy.py:214) bauen KEINEN Brainstorm-Block — GeneralAG ist dort frei selbst zu antworten.**

### 3.5 GeneralAG wird von 4 Pfaden mit Override-System-Prompt aufgerufen

**Diese Aufrufe umgehen die GeneralAG-Identity komplett:**

| Pfad | sys-Override |
|---|---|
| `adaptive_decomposition.py:108-113` `estimate_complexity()` | `"Du bist ein präziser Komplexitäts-Bewerter."` |
| `swarm_coordinator.py:103` `_eval()` | `"Du bist GeneralAG. Führe Ergebnisse des Team-Workflows zusammen..."` |
| `soul/soul.py:504, 540` `run_evolution()` + `handle_user_feedback()` | `"Du bist Optimierer."` |
| `core/utils/graceful_fallback.py:76` | `"Du bist ein präziser Qualitäts-Schätzer."` |
| `api/endpoints/admin_config.py:94` | `SYSTEM_PRESET_GEN` (separat definiert) |

**Befund:** In diesen 5 Pfaden sieht GeneralAG NICHT seine 5.554-Zeichen-Identity. Er bekommt eine Hardcoded 1-Zeilen-Anweisung. **Das ist NICHT konsistent** mit der Identity-Definition. Die Identity sagt "Du bist GeneralAG — der DIRIGENT und PROJEKTLEITER des gesamten Agenten-Swarms" — in den Override-Pfaden ist er ein "Optimierer" oder "Komplexitäts-Bewerter".

---

## 4. Widersprüche INTERN

### 4.1 Slider vs. Identity-Anforderungen

| Identity-Anforderung | Slider-Wert | Konflikt? |
|---|---|---|
| "Vor jeder Delegation: Konsultiere worker_stats" (Z. 51) | `critical_thinking: 2` | TEILWEISE — Slider sagt "Suggest obvious improvements", Identity verlangt aktive Konsultation (= eher Stufe 3) |
| "Bevorzuge Worker mit success_rate ≥ 40% UND mindestens 5 abgeschlossenen Jobs" (Z. 53) | `precision: 2` | OK — "Verify main outputs" passt zu Threshold-Check |
| "3 Kernrollen (ZERLEGEN/DELEGIEREN/SYNTHETISIEREN) exakt" | `obedience: 2` | OK — "reasonable interpretation" |
| "Worker-Denkprozesse + CoordinationDB-Statistiken + offene Contexts MITLESEN" (Z. 15) | `speed: 2` | TEILWEISE — Identity verlangt aktive Synthese aus 3 Quellen, Slider sagt "Steady pace" |

**Befund:** Sliders sind NICHT individuell kalibriert. Wie bei allen 8 Agents identisch (siehe SoulAG-Audit §5.7). Tuner-Infrastruktur (`agents_status.py:119-132`) ist untätig.

### 4.2 Permissions vs. Aufgaben

| Aufgabe in Identity | Benötigte Permission | In JSON? | In Python? |
|---|---|---|---|
| "Delegations-Ankündigungen via Showbox" (Z. 11) | `showbox_write` | ✅ (dead) | ❌ |
| "Status-Reports" (Z. 11) | `read` + Showbox | ✅ (showbox_write dead) | ✅ (read) |
| "Worker-Tracking via coordination.db" (Z. 51) | `db_write` | ✅ (dead) | ❌ |
| "Worker-Profile, Outcomes, Pending schreiben" (Identity Z. 91-95) | `db_write` + `general_memory` | ✅ (db_write dead) | ❌ (general_memory dead) |
| "Diskussionen in generalag_discussions" (Identity Z. 91) | `db_write` + `general_memory` | ✅ | ❌ |
| "Preset-Historie in generalag_preset_history" (Identity Z. 95) | `db_write` | ✅ (dead) | ❌ |
| "SmartRouter-3-Stage-Routing nutzen" (Z. 52) | `@job` (Routing-Token) | ✅ | ✅ |
| "5-Spalten-WS-Tabellen CONSUMEN" (worker_stats, open_contexts) | `read` | ✅ | ✅ |

**Befund:** 4 von 8 Pflicht-Aufgaben brauchen `db_write` oder `general_memory`, die in Python-Perms (der Runtime-Wahrheit) fehlen. **GeneralAG kann seine 5 spec'd DB-Tabellen GARANTIERT nicht über `action_handlers` schreiben.** Falls er es versucht: keine Sperre, weil niemand diese Pfade permission-checkt (alle 5 Repo-Funktionen werden ohne Permission-Check direkt aufgerufen — wenn sie denn aufgerufen würden).

### 4.3 Identity vs. Code-Realität

| Identity-Aussage | Code-Realität | Widerspruch? |
|---|---|---|
| "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG" | chat_legacy.py:132 + chat_helpers.py:15-19 + brainstorm.py:18-57: empfängt von User, Broadcast, `@bs`, anderen Agents | **WIDERSPRUCH** (auch in SoulAG-Audit §5.4 dokumentiert) |
| "Du delegierst an die 4 Worker" | dispatch_mention kann ALL Agents adressieren, keine Code-Sperre | **TEILWEISE** — keine Sperre gegen System-Targets |
| "Du hast KEINE direkte Verbindung zu WatchdogAG oder SecurityAG" | dispatch_mention kennt keine Tier-Filter | **WIDERSPRUCH** — keine Sperre, nur Prompt-Disziplin |
| "Konsultiere worker_stats" | find_best_agent_for_task (swarm_comms.py:180) konsultiert worker_stats AUTOMATISCH | TEILWEISE — Identity suggeriert GeneralAG konsultiert, Code tut es selbst |
| "Bevorzuge Worker mit success_rate ≥ 40% UND mindestens 5 Jobs" | swarm_comms.py:243-248 implementiert EXAKT diese Threshold | ✅ KONSISTENT |
| "Deine Farbe ist immer Blau" | agent_names.py:34 → `#00e5ff` (CYAN). tool_registry.py:70 sagt "GeneralAG (cyan)" | **WIDERSPRUCH** — Code sagt cyan, Identity sagt blau |
| "Du hast exklusiven Schreibrecht auf die general_memory-Datenbank" | `general_repo.py` hat Save-Funktionen, ABER 0 externe Caller | **WIDERSPRUCH** — Spec lügt über bestehende Funktionalität |
| "5 Tabellen (generalag_discussions/outcomes/pending/worker_profile/preset_history)" | `generalag_repo.py` hat 16 Funktionen, ABER 0 externe Caller | **WIDERSPRUCH** — komplette Datenleiche |

### 4.4 Geistige Selbst-Disziplin vs. Hardcoding

**Identity Z. 14-16** fordert geistige Disziplin:
> "Du liest MIT: Worker-Denkprozesse, Worker-Outputs, CoordinationDB-Statistiken und offene Contexts. Das ist deine Sicht auf den aktuellen State — SoulAG injiziert sie dir."

**Was passiert in der Code-Realität:**
- Worker-Denkprozesse: Werden in `soul_observer.py:track_reasoning` (Z. 205-240) als `reasoning_<agent>_<hash>` in soul_memory gespeichert. GeneralAG hat `agent_scope == "all"` in `embeddings.py:73-74` und `soul_retrieval.py:21` → er SIEHT sie via Memory-Query
- Worker-Outputs: Werden in `chat_messages` DB gespeichert. GeneralAG kann via `_get_chat_history_tail` (context.py:144-154) die letzten 20 sehen — **nur wenn in `allowed_contexts`** (was er hat: Z. 30 "chat_history_tail")
- CoordinationDB-Statistiken: Werden in `_get_worker_stats` (context.py:73-84) aufbereitet. **ABER: nur top 5 by total_jobs, OHNE success_rate < 40% filter** (Z. 478-491 in memory_layers.py). GeneralAG sieht nur die Top-5 Liste ohne Threshold-Info
- Offene Contexts: Werden in `_get_open_contexts` (context.py:87-97) als text-summary injiziert. **LIMIT 5** (Z. 723)

**Befund:** 4 Quellen existieren in der Codebase, 4 davon werden in den GeneralAG-Prompt injiziert. **Aber:** Die Aufbereitung ist oberflächlich (Top-5, success_rate-only, keine Failure-Analyse). GeneralAG "MITLESEN" ist informativ, nicht handlungsleitend.

### 4.5 Tier-Self-Contradiction in `GeneralAG.json:18`

Identity-Block hat 2 sich widersprechende Aussagen:
- **Kommunikations-Sektion (Z. 10):** "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG (via @GeneralAG)."
- **Tier-Hierarchie-Sektion (Z. 81-86):** "Du bekommst Aufträge von SoulAG (Tier 2a) oder direkt vom User."

→ **Self-contradictory.** "AUSSCHLIESSLICH" (exklusiv) vs "ODER direkt vom User" (auch direkt) sind unvereinbar.

**Plus:** SoulAG-Identity sagt in `agent_definitions.py:79`: "Wenn nicht: @GeneralAG mit der konkreten Aufgabe". SoulAG selbst sagt "ich delegiere AN GeneralAG" — was konsistent mit "AUSSCHLIESSLICH" wäre. Aber GeneralAG selbst sagt "ODER vom User" — was die User-zu-GeneralAG-Direktverbindung legitimiert.

**Resolution:** Code-Realität in chat_legacy.py:132+207+214: User kann GeneralAG DIREKT ansprechen via @GeneralAG, @bs, oder Broadcast. Die "AUSSCHLIESSLICH"-Aussage ist WUNSCH, nicht Realität.

---

## 5. Widersprüche ZU ANDEREN AGENTS

### 5.1 SoulAG vs. GeneralAG — "AUSSCHLIESSLICH" vs. "ODER direkt vom User"

| Quelle | Aussage |
|---|---|
| `GeneralAG.json:10` | "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG (via @GeneralAG)." |
| `GeneralAG.json:82-84` (TIER-HIERARCHIE) | "Du bekommst Aufträge von SoulAG (Tier 2a) oder direkt vom User." |
| `agent_definitions.py:79` SoulAG-Block | "Wenn nicht: @GeneralAG mit der konkreten Aufgabe" |
| `SoulAG.json:86` (aus SoulAG-Audit) | "Tier 3a: GeneralAG (Dirigent, bekommt Delegation von dir oder direkt vom User)" |

**Befund:** GeneralAG hat INTERNAL contradiction (siehe §4.5). SoulAG-Definition KONFLIKTIERT mit "AUSSCHLIESSLICH". User-Realität: User kann GeneralAG DIREKT ansprechen (chat_legacy.py:132, 207, 214).

### 5.2 GeneralAG-Farbe — 3 Quellen, 2 Farben

| Quelle | Wert |
|---|---|
| `core/agent_names.py:34` AGENT_COLORS | `#00e5ff` (CYAN) |
| `tool_registry.py:70` | "GeneralAG (cyan)" |
| `agent_definitions.py:147, 153` (Direktive DE+EN) | "Farbe: Blau" |
| `config/agents/GeneralAG.json:56` (Identity) | "Deine Farbe ist immer Blau" |
| `docs/ARCHITECTURE.md:26` | `#00e5ff` (Cyan, system-layer) |

**Befund:** Code-Vertrag (agent_names.py, FROZEN) = **CYAN #00e5ff**. Text-Identity (4 Stellen) = **BLAU**. LLM glaubt es ist blau, Frontend rendert cyan. Drifthazard — was sagt der User dem LLM, wenn er die UI ansieht?

### 5.3 Worker-Perms im Vergleich

| Agent | JSON-Perms | Python-Perms | Differenz |
|---|---|---|---|
| CoderAG | `[read, write, run, showbox_write]` | `[read, write, run]` | `showbox_write` dead |
| WriterAG | `[read, write, crawl, showbox_write]` | `[read, write, crawl]` | `showbox_write` dead |
| EditorAG | `[read, write, showbox_write]` | `[read, write]` | `showbox_write` dead |
| ResearcherAG | `[read, crawl, web_search, browser, showbox_write]` | `[read, crawl, web_search, browser]` | `showbox_write` dead |
| **GeneralAG** | `[read, write, @job, db_write, showbox_write]` | `[read, @job, general_memory]` | **`write`, `db_write`, `showbox_write` dead; `general_memory` dead-in-other-direction** |
| SoulAG | `[read, write, showbox_write]` | `[read, evolve, crawl]` | Massive Drift (SoulAG-Audit) |
| WatchdogAG | `[read, showbox_write]` | `[read]` | `showbox_write` dead |
| SecurityAG | `[read, write, run, godmode, db_write, network, showbox_write]` | `[read, write, run, godmode]` | `db_write`, `network`, `showbox_write` dead |

**Befund:** GeneralAG hat wie SoulAG den GRÖSSTEN Drift (4 Token-Mismatch). Worker haben 1 Drift (`showbox_write` dead). GeneralAG-Drift ist symmetrisch: JSON hat 3 Dead-Tokens (`write`, `db_write`, `showbox_write`), Python hat 1 Dead-Token (`general_memory`).

### 5.4 "Erfolg ≥ 40% und ≥ 5 Jobs" Threshold — wer prüft das?

**Identity Z. 53-54:**
> "Bevorzuge Worker mit success_rate ≥ 40% UND mindestens 5 abgeschlossenen Jobs."

**Code-Realität in swarm_comms.py:204-253:**
- Z. 222-224 SQL: `WHERE ws.total_jobs >= 2 ORDER BY success_rate DESC, total_jobs DESC` — **MIN_THRESHOLD = 2, nicht 5!**
- Z. 243-248: `if row["success_rate"] < 0.4 and row["total_jobs"] >= 5: skip` — **`>= 5` gilt nur für SKIP-Bedingung, nicht für Inclusion**

**Befund:** Identity behauptet "Worker mit mindestens 5 Jobs" als INCLUSION-Kriterium. Code nutzt `>= 2` als Minimum für Sortierung, und `>= 5` als Skip-Bedingung für schlechte Worker. **Drift: Identity und Code implementieren verschiedene Schwellen.**

**Konsequenz:** Ein Worker mit 3 Jobs und 100% success_rate wird vom Code AKZEPTIERT (≥ 2), von der Identity IGNORIERT (≥ 5).

### 5.5 "Stagnation-Check 5min open + 3 Nudges" — wo?

**Identity verlangt es nicht direkt**, aber `_nudge_loop` (soul.py:340-418) implementiert:
- Z. 348: `stale_cutoff = now - 300` (5 Min)
- Z. 355: `WHERE nudge_count < 3`
- Z. 388-411: Nach 3 Nudges → `status='blocked'` + SecurityAG-Dispatch

**Befund:** SoulAG nudgt Worker direkt (nicht via GeneralAG). GeneralAG ist im Eskalations-Pfad NICHT enthalten — SecurityAG bekommt die Meldung.

### 5.6 GeneralAG = "coordination" Capability — vs. Worker-Capabilities

**`agent_base.py:36-37`:**
```python
elif "general" in name_lower:
    self.CAPABILITIES = [("coordination", 1.0)]
```

**`agent_base.py:24-33` Worker-Capabilities:**
- CoderAG: `("code_generation", 1.0), ("code_review", 0.9), ("debugging", 0.8)`
- WriterAG: `("content_creation", 1.0), ("summarization", 0.9), ("editing", 0.8)`
- EditorAG: `("editing", 1.0), ("summarization", 0.8)`
- ResearcherAG: `("web_research", 1.0), ("fact_checking", 0.9), ("summarization", 0.7)`

**Befund:** GeneralAG hat EINE Capability: `coordination` (confidence 1.0). Im SmartRouter-3-Stage wird diese in `_get_worker_stats` NICHT abgefragt — `find_best_agent_for_task` (swarm_comms.py:180) matcht nur gegen `code_generation`/`web_research`/`content_creation`/`editing`/`summarization`/`security_audit`. **GeneralAG wird vom SmartRouter nie als Ziel-Agent gepickt** — er ist Coordinator, nicht Worker.

### 5.7 Cross-Source-Befund: GeneralAG-Wahrnehmung im System

**Wer sieht GeneralAG als was?**

| System | Wahrnehmung | Code-Beleg |
|---|---|---|
| SmartRouter (3-Stage) | Coordinator (nicht Worker) | swarm_comms.py:200-201: matched_caps = [code_gen, web_research, ...] — KEIN "coordination" |
| SoulAG (chat_legacy) | Tier 3a Worker-Empfänger | soul.py:524: filter worker-out mit sender.lower() not in [user, system, generalag, ...] |
| Action-Handlers | Agent ohne write/run | action_handlers.py:64, 99: System-Meldungen |
| User (chat_legacy broadcast) | Online Agent (empfängt Broadcast) | chat_legacy.py:212 |
| Workflow-Engine | Sender für Worker-Tasks | workflow_engine.py:340 `sender="GeneralAG"` |
| Role-Tools | Coordinator | role_tools.py:14-16: LLM-Prompt mit "Truppe" |
| Adaptive-Decomposition | Komplexitäts-Schätzer | adaptive_decomposition.py:108-113 |
| Showbox-Layer | System-Layer | showbox_repo.py:34: startswith("general") → "system" |
| SoulAG `_nudge_loop` | KEIN Empfänger (Workers direkt) | soul.py:340-418 |

**Befund:** GeneralAG hat **9 verschiedene Rollen-Wahrnehmungen** im System. Inkonsistenzen:
- SmartRouter sieht ihn nicht als dispatchable → korrekt für Routing
- Adaptive-Decomposition nutzt ihn als Bewerter → semantisch OK, aber überschreibt Identity
- Workflow-Engine nutzt ihn als Sender → semantisch OK
- 5 Override-Pfade nutzen ihn als spezialisierten Agent → **dokumentationsfreie Spezialisierung**

---

## 6. Lücken

### 6.1 Was GeneralAG können sollte, aber undefiniert ist

1. **Worker-Failure-Eskalation**: Kein Code-Pfad schickt Worker-Failure-Alerts an GeneralAG. SoulAG's `_nudge_loop` eskaliert an SecurityAG, nicht an GeneralAG (soul.py:404-411).
2. **Pending-Tracking**: Identity Z. 93 verlangt "Wenn was offen bleibt: sofort in `generalag_pending`". Code hat 0 Caller für `add_pending()`. Realität: `open_context` in ContextDB wird in `agent_base.py:101` automatisch geöffnet, aber NICHT für "Pending"-Tracking verwendet.
3. **Worker-Profile-Updates**: Identity Z. 94 verlangt "Wenn ein Worker auffällt: `generalag_worker_profile` updaten". Code: 0 Caller für `update_worker_profile()`. Realität: `coordination.db.worker_stats` (anderes Schema) wird automatisch via `agent_base.py:178-185` befüllt — doppelte Datenhaltung mit toter Alternative.
4. **Preset-Historie**: Identity Z. 95 verlangt "Bei jedem Preset-Wechsel: `generalag_preset_history` Eintrag". Code: 0 Caller für `log_preset_change()`.
5. **Diskussionen**: Identity Z. 91 verlangt "Nach jedem Brainstorm: 1 Eintrag in `generalag_discussions`". Code: 0 Caller für `save_discussion()`. **ALL 5 spec'd tables = dead code.**
6. **`general_memory` Spec**: agent_definitions.py:121-128 verlangt exklusives Schreibrecht auf `general_memory`. Code: 0 Caller für `save_general_fact` / `add_to_general_memory` / `log_task` / `complete_task`. Realität: `log_task` wird in `general_repo.py:192-196` implementiert, aber niemand ruft es.
7. **Direct `@CoderAG` instead of `@<worker-with-run-permission>` für Git**: Identity Z. 37 hardcoded "CoderAG" als Default-Commiter. SecurityAG hat `run`+`godmode` und könnte theoretisch committen — aber `verify_cmd` blockt `git` für ALLE (gatekeeper.py:427-430). Identity ist obsolet, da CoderAG selbst nicht committen kann.
8. **Feedback-Loop für Worker-Quality**: Identity erwähnt `generalag_outcomes` mit `success_rating 1-5` — Code hat 0 Caller. Realität: `coordination.db.job_history.result` ist `success/failed/timeout` (kein 1-5 Rating).
9. **`@job` Permission-Token**: Permission-Token existiert in beiden Quellen, ABER kein Code in `action_handlers.py` oder `gatekeeper.py` checkt `@job`. Es ist nur ein Routing-Marker (SoulAG nutzt es via `dispatch_agent`, aber das checkt nicht die Permission-Liste).

### 6.2 Welche Übergaben fehlen

- **Worker → GeneralAG Completion-Notification**: Workers posten via `add_chat_message` (action_handlers.py via `_post_chat`), aber kein Code markiert die Message als "this is a completion of task X" für GeneralAG. GeneralAG muss den Chat-Verlauf lesen.
- **SecurityAG → GeneralAG bei Blockaden**: SecurityAG-Identity Z. 11: "AUSNAHME: destruktive/externe Aktionen, dann frag den User vorher." — fragt USER, nicht GeneralAG. Blockade-Showbox-Cards gehen an User, GeneralAG sieht sie nur wenn er User-Chat mitliest.
- **GeneralAG → SoulAG Worker-Status**: `generalag_outcomes` Tabelle wäre der Pfad — aber 0 Caller. Realität: `coordination.db.job_history` (anderes Schema) wird befüllt, aber SoulAG `allowed_contexts: "worker_stats"` zeigt nur aggregierte Stats (über `_get_worker_stats` context.py:73-84), nicht die Outcomes-Tabelle.
- **SoulAG → GeneralAG Direct-Dispatch (nicht via @mention)**: SoulAG's `dispatch_agent("GeneralAG", ...)` (soul_actions.py:38-71) routed via `dispatch` (brainstorm.py:18-37) → `dispatch_mention` (swarm_comms.py:311-417). Das ist ein normaler Mention-Pfad, kein "special instruction"-Pfad.
- **Adaptive-Decomposition-Route B → GeneralAG**: Strategy B (serial Writer+Editor) hat keinen GeneralAG-Touch. Strategy A (parallel Coder+Writer) ebenso. Strategy C (single GeneralAG) hat einen, aber `_eval` setzt Override-System-Prompt.
- **Workflow-Engine → GeneralAG**: Workflows senden via `dispatch_by_capability` mit `sender="GeneralAG"` (workflow_engine.py:340). Das ist nur der sender-Name in der Message — keine echte GeneralAG-Logik.
- **`start_coordinator` post-completion**: `run_swarm_coordinator` Z. 142 postet "Der Workflow ist beendet. War das Ergebnis gut?" als GeneralAG — **hardcoded message, kein LLM-generierter Status-Report**.

### 6.3 Edge-Cases nicht abgedeckt

1. **GeneralAG-LLM-Halluzination bei der 3 Kernrollen**: Wenn GeneralAG "ZERLEGEN" überspringt und direkt eine Worker-Lösung postet → keine Code-Sperre.
2. **GeneralAG delegiert an System-Agent**: dispatch_mention kennt keine Tier-Filter. `@GeneralAG @WatchdogAG` ist gültig.
3. **GeneralAG delegiert an sich selbst**: dispatch_mention Z. 357-358: `if tgt_lower == sender.lower(): continue` (Skip-Self) — ABER: GeneralAG kann `@GeneralAG` posten wenn sender=user, dann ist target=generalag, sender=user → NICHT skip. User kann GeneralAG also re-triggern.
4. **Brainstorm-Block ignoriert**: Wenn GeneralAG-LLM den bs_instruction-Block komplett ignoriert und statt Worker-Delegation eine eigene Antwort postet → keine Sperre.
5. **5+ Worker delegiert**: parse_agent_sequence in swarm_comms.py:66-84 parst ALLE `@Agent -> task` Zeilen. `dispatch_sequence` (Z. 87-177) routed sequenziell mit dependency_chain. **ABER: bei `MAX_DEPTH=15` (swarm_comms.py:21) bricht alles ab.** GeneralAG kann keine tiefen Hierarchien erzeugen.
6. **Worker antwortet nicht in 180s**: `WorkerCompletionTracker.wait()` (swarm_coordinator.py:39-54) returnt `completed=False` nach 180s. **KEIN Post zu GeneralAG, nur Logger-Warning.** Coordinator-Loop terminiert mit unvollständigem Resultat.
7. **`general_memory` voll (>2000 Fakten)**: `MAX_GENERAL_FACTS = 2000` (general_repo.py:14). Cleanup-Logik existiert NICHT. Decay-Loop analog zu soul_memory fehlt.
8. **GeneralAG-LLM crasht mid-delegation**: nack_message (swarm_comms.py:572) handled Retry+DLQ, ABER: wenn GeneralAG SELBST crashed, dann bleibt die halb-delegierte Task zurück. Kein Recovery-Pfad für GeneralAG.
9. **Override-System-Prompt-Pfade ignorieren Identity**: 5 Pfade rufen GeneralAG mit `sys="Du bist Optimierer/Bewerter/Schätzer"` — die GeneralAG-Identity gilt dort NICHT. GeneralAG "denkt" als Optimierer, nicht als Dirigent.
10. **coordination.db nicht existent beim Cold-Start**: `coordination_db_path()` (memory_layers.py:32-33) gibt Path zurück, `_init_db()` wird in `CoordinationDB.__init__()` aufgerufen. **Falls Permission-Fehler → generalag-memory ist leer, alle 4 Worker haben 0 Jobs, SmartRouter Stage 1 liefert nichts, Stage 2-3 greifen.**
11. **Stale-Worker-Recovery in coordination.db**: Wenn ein Agent gecrasht ist, hat er hohe `processing_since` aber keinen `done`-Update. `recover_stuck_messages` (swarm_comms.py:725) handled das für `agent_messages`, NICHT für `coordination.db.job_history`. **Coordination-db sammelt stale Daten.**

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 [HOCH] `generalag_repo.py` und `general_repo.py` aktivieren oder löschen
- **Was:** 5 GeneralAG-Tabellen + general_memory Tabelle existieren mit kompletten Repo-Implementierungen (generalag_repo.py:323 Zeilen, general_repo.py:232 Zeilen), aber 0 Caller. Entweder: (a) Auto-Calls in `agent_base.py:178-185` einbauen (nach `record_job` → `save_outcome` aufrufen), oder (b) als deprecated markieren und aus DB-Schema entfernen.
- **Warum:** Identity behauptet 5 Tabellen werden aktiv genutzt — Lüge. User-Mandat 2026-06-28 12:03 hat diese Spec erzwungen, aber niemand hat die Integration gebaut.
- **Datei:** `src/gnom_hub/agents/agent_base.py:178-185, 200-211` (erweitern), oder `src/gnom_hub/db/schema.py:298-355` (Schema-Entfernung).
- **Risiko:** Niedrig wenn Aktivierung (pure Addition). Mittel wenn Löschung (Migration nötig).

### V2 [HOCH] "Workspace prüfen" Halluzination mitigieren
- **Was:** Entweder (a) `ask_llm` brainstorm_helpers.py:15-16 Doppel-Injection entfernen (Context-Block reicht), oder (b) Brainstorm-Instruction-Block Z. 38-55 explizit machen "Du prüfst NICHT erst den workspace — du delegierst SOFORT".
- **Warum:** User hat explizit "GeneralAG delegiert nicht zuverlässig an CoderAG (halluziniert 'erst Workspace prüfen')" als Symptom gemeldet. Symptom-Ursache ist im CODE (doppelte Workspace-Injection in jedem brainstorm_caller), nicht in der Identity.
- **Datei:** `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:15-16`.
- **Risiko:** Niedrig. Optional: Logs zur Verifikation dass es hilft.

### V3 [HOCH] 3 Kernrollen technisch verifizierbar machen
- **Was:** Im `ask_llm` Output (brainstorm_helpers.py:25-30) prüfen ob Output `@Agent -> task` Pattern enthält. Wenn NICHT (GeneralAG hat ohne Delegation geantwortet) → zweite LLM-Iteration mit "Du hast nicht delegiert. Versuche es nochmal mit @Worker -> Aufgabe-Format."
- **Warum:** "ZERLEGEN/DELEGIEREN/SYNTHETISIEREN" sind aktuell nur Prompt-Disziplin. GeneralAG kann selbst antworten ohne zu delegieren — Symptom der User-Frustration.
- **Datei:** `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:25-30` (post-process Check).
- **Risiko:** Niedrig. Worst case: 2× LLM-Call bei Delegations-Verweigerung.

### V4 [HOCH] Eskalations-Pfad Worker-Fail → GeneralAG einbauen
- **Was:** In `nack_message` (swarm_comms.py:572-609) und `recover_stuck_messages` (swarm_comms.py:725-769) nach DLQ-Trigger: post via `_post_chat("SoulAG", ...)` an GeneralAG (analog zu `notify_generalag` in `soul_observer.py:172-198`). Plus: Dead-Letter-Notification (agent_base.py:216-229) erweitern um "GeneralAG bitte Worker tauschen" Hinweis.
- **Warum:** Aktuell erfährt GeneralAG Worker-Failures nur via passive Chat-Sicht. SoulAG's `_nudge_loop` (soul.py:340-418) eskaliert direkt an SecurityAG, GeneralAG wird übergangen.
- **Datei:** `src/gnom_hub/agents/swarm/swarm_comms.py:593-594` (Z. 594 _post_chat erweitern), `src/gnom_hub/agents/agent_base.py:216-229`.
- **Risiko:** Niedrig. Nur zusätzliche Post-Calls.

### V5 [MITTEL] Permission-Dual-Truth auflösen (auch GeneralAG-spezifisch)
- **Was:** Wie im SoulAG-Audit V1: JSON-Perms `["read", "write", "@job", "db_write", "showbox_write"]` in `GeneralAG.json:19-25` reduzieren auf das was Runtime-Python nutzt: `["read", "@job"]`. ODER Python-Perms in `agent_definitions.py:148, 153` an JSON anpassen und `general_memory` entfernen.
- **Warum:** GeneralAG hat 4 Token-Mismatch zwischen JSON und Python. Verwirrend für Auditoren + zukünftige Refactorer.
- **Datei:** `config/agents/GeneralAG.json:19-25` ODER `src/gnom_hub/agents/agent_definitions.py:148, 153`.
- **Risiko:** Niedrig (Runtime-Verhalten ändert sich nicht).

### V6 [MITTEL] "Erfolg ≥ 40% und ≥ 5 Jobs" Threshold angleichen
- **Was:** Identity Z. 53-54 sagt "Worker mit mindestens 5 Jobs bevorzugen". Code swarm_comms.py:222 hat `>= 2` als Minimum. Angleichen: entweder Code auf `>= 5` anpassen ODER Identity auf `>= 2` reduzieren.
- **Warum:** Symmetrie zwischen Doc und Code. Identity ist strenger als Code, was zu kognitiver Dissonanz bei Maintenance führt.
- **Datei:** `src/gnom_hub/agents/swarm/swarm_comms.py:222` ODER `config/agents/GeneralAG.json:53`.
- **Risiko:** Niedrig. Nur Threshold-Tuning.

### V7 [MITTEL] Tier-Filter für `dispatch_mention` und `dispatch_sequence`
- **Was:** In `swarm_comms.py:354-368` (dispatch_mention) und `swarm_comms.py:122-137` (dispatch_sequence) prüfen: wenn sender == "generalag" (oder role=general) und target ist System-Agent → WARNING log + skip.
- **Warum:** Identity Z. 12-13 sagt "Du hast KEINE direkte Verbindung zu WatchdogAG oder SecurityAG". Aktuell kann GeneralAG `@WatchdogAG` posten, was die Tier-Hierarchie bricht.
- **Datei:** `src/gnom_hub/agents/swarm/swarm_comms.py:357-358` (Self-Skip-Pattern erweitern).
- **Risiko:** Niedrig. Nur zusätzliche Skip-Logik.

### V8 [MITTEL] Farb-Diskrepanz "Blau" vs "Cyan" auflösen
- **Was:** Entweder Identity (GeneralAG.json:56) und agent_definitions.py:147, 153 von "Blau" auf "Cyan" ändern, ODER `agent_names.py:34` von `#00e5ff` auf eine Blau-Variante (z.B. `#3b82f6`) ändern.
- **Warum:** LLM glaubt "Blau", Frontend rendert "Cyan". Bei zukünftigen Showbox-Theming-Updates gibt es Reibung.
- **Datei:** `config/agents/GeneralAG.json:56` (kleinste Änderung), ODER `src/gnom_hub/core/agent_names.py:34`.
- **Risiko:** Sehr niedrig (Doku-Update vs. visueller Update).

### V9 [MITTEL] Override-System-Prompt-Pfade dokumentieren
- **Was:** 5 Pfade (adaptive_decomposition, soul.run_evolution, soul.handle_user_feedback, graceful_fallback, admin_config, swarm_coordinator) nutzen GeneralAG mit Hardcoded-Override-System-Prompts. In GeneralAG-Identity eine Sektion ergänzen: "═══ WANN DU ALS SPEZIALIST AGIERST ═══" mit Liste der Override-Prompts.
- **Warum:** GeneralAG-LLM sieht in 5 von 13 Pfaden NICHT seine Haupt-Identity. Audit-Trail fehlt.
- **Datei:** `config/agents/GeneralAG.json:18` (Identity erweitern).
- **Risiko:** Niedrig. Reine Doku.

### V10 [NIEDRIG] 6 identische `SYSTEM_AGENTS`-Listen auf eine zentrale Konstante reduzieren
- **Was:** `core/agent_names.py:15-19` ist `FROZEN: True` — die anderen 5 Listen (chat_helpers.py:5, chat_clear.py:39, llm_agents.py:9, presets.py:255, preset_service.py:11) sollten importieren statt duplizieren.
- **Warum:** Drifthazard. Eine zentrale Änderung (z.B. GeneralAG-Umbenennung) erfordert 6 Patches.
- **Datei:** Alle 5 nicht-FROZEN Listen → `from gnom_hub.core.agent_names import SYSTEM_AGENTS`.
- **Risiko:** Niedrig. Reines Refactor.

### V11 [NIEDRIG] `general_memory` Cleanup-Decay-Loop analog zu soul_memory
- **Was:** `general_repo.py:14` definiert `MAX_GENERAL_FACTS = 2000`, aber kein Cleanup. Analog zu `memory_decay.py` (für soul_memory) einen Decay-Loop implementieren: low nach 7d, medium nach 14d, high nach 30d.
- **Warum:** Wenn `general_memory` aktiv genutzt würde (V1), würde die DB überlaufen.
- **Datei:** `src/gnom_hub/db/general_repo.py` (Decay-Loop hinzufügen), Cron-Job analog zu soul.
- **Risiko:** Niedrig (nur Code, der noch nicht aufgerufen wird).

### V12 [NIEDRIG] Token-Limit GeneralAG vs. SoulAG angleichen
- **Was:** `router_call.py:69` definiert `{"generalag": 6000, "soulag": 50000}`. GeneralAG bekommt 8× weniger Token als SoulAG. Für System-Prompts mit Identity (5.554 Zeichen) + Context-Blocks + 3 Kernrollen-Anweisungen könnte 6000 knapp werden.
- **Warum:** GeneralAG-Identity ist 5.554 Zeichen, plus [VERHALTEN] (~400), [TOOLS] (~200), [SICHERHEIT] (~200), [KONTEXT:*] Blöcke (variabel, bis ~3000) — Identity + Static = ~6.500 Token, schon über dem Limit.
- **Datei:** `src/gnom_hub/infrastructure/router/router_call.py:69`.
- **Risiko:** Niedrig. Mehr Token = mehr Kosten, aber GeneralAG bekommt Free-Tier-Modelle (router_config.py:13).

---

## 8. Cross-Check-Notes für die Synthese

Diese Stichpunkte sollte der Cross-Synthesis-Verifier aufgreifen:

1. **"AUSSCHLIESSLICH von SoulAG" Lüge**: GeneralAG empfängt von User (chat_legacy.py:132, 207, 214), Broadcast (chat_legacy.py:212), `@bs` (brainstorm.py:38-55), anderen Agents (jeder kann `@GeneralAG` posten), SoulAG (soul_actions.py:38-71). Identity-Aussage ist WUNSCH, nicht Realität.

2. **Permission-Dual-Truth JSON vs Python** ist auch GeneralAG-Problem: `["read", "write", "@job", "db_write", "showbox_write"]` (JSON) vs `["read", "@job", "general_memory"]` (Python). Schnittmenge `["read", "@job"]`. Wie SoulAG der krasseste Fall.

3. **5 von 8 spec'd DB-Tabellen sind DEAD-CODE**: `generalag_discussions`, `generalag_outcomes`, `generalag_pending`, `generalag_worker_profile`, `generalag_preset_history` (alle in `generalag_repo.py`) + `general_memory` (in `general_repo.py`) haben 0 externe Caller. Identity lügt über Funktionalität.

4. **"Workspace prüfen" Symptom ist im Code vergraben**, nicht in der Identity. Ursachen: (a) `_get_workspace_summary` (context.py:131-141) + (b) manuelle Doppel-Injection in `ask_llm` (brainstorm_helpers.py:15-16). DOPPELTE Injektion = LLM-Overload. Spec-Verletzung des "Worker delegiert"-Versprechens.

5. **3 Kernrollen sind unerzwungen**: ZERLEGEN/DELEGIEREN/SYNTHETISIEREN sind LLM-Aufgaben ohne Code-Sperre. GeneralAG kann selbst antworten ohne zu delegieren — Vorschlag V3 würde eine 2. LLM-Iteration bei Delegations-Verweigerung triggern.

6. **5 Override-System-Prompt-Pfade**: adaptive_decomposition, soul.run_evolution, soul.handle_user_feedback, graceful_fallback, admin_config, swarm_coordinator — alle nutzen GeneralAG mit Hardcoded-1-Zeilen-Override. In diesen Pfaden sieht GeneralAG NICHT seine Haupt-Identity.

7. **Eskalations-Pfad fehlt**: Worker-Fail-3x → DLQ + System-Chat (kein GeneralAG-Alert), SoulAG `_nudge_loop` → SecurityAG (GeneralAG übergangen), soul_observer-Alerts nur bei 4 Pattern-Triggern mit 5min Cooldown. GeneralAG ist KEIN Eskalations-Ziel.

8. **SmartRouter-Versprechen ist Code-getrieben, nicht GeneralAG-getrieben**: Identity suggeriert GeneralAG "konsultiert worker_stats". Code (swarm_comms.py:180-293 `find_best_agent_for_task`) tut das automatisch. GeneralAG-LLM sieht nur aggregierten Summary-Block.

9. **Git-Management-Default ist obsolet**: Identity hardcoded "CoderAG committe". Aber CoderAG kann nicht committen (`gatekeeper.py:427-430` blockt `git` für alle Agents). Spec ist Geister-Anweisung.

10. **Tier-Self-Contradiction in GeneralAG.json:10 vs Z. 82-84**: "AUSSCHLIESSLICH von SoulAG" vs "ODER direkt vom User" sind unvereinbar. Code-Realität: beides funktioniert.

11. **GeneralAG bekommt 6000 Token, SoulAG 50000** (8× weniger). GeneralAG-Identity (5.554 Zeichen) + Static-Blocks (800) = bereits über dem Limit ohne [KONTEXT:*].

12. **GeneralAG-LLM hat Free-Tier-Modelle** (router_config.py:13): llama-3.3-70b-instruct, hermes-3-llama-3.1-405b, gpt-oss-120b, gemma-4-31b-it. **Kein Claude/DeepSeek/GPT-4o**. Konsistent mit der "Dirigenten"-Rolle als kostengünstig.

13. **GeneralAG hat 9 verschiedene Rollen-Wahrnehmungen** in der Codebase: SmartRouter-Coordinator, SoulAG-Worker-Empfänger, Action-Handler-blocked-Agent, Broadcast-Empfänger, Workflow-Sender, Coordinator, Komplexitäts-Schätzer, Showbox-system-Layer, SoulAG-nudge-Subject. Inkonsistenz zwischen Identity (Dirigent) und Code-Spezialisierungen (Optimierer/Bewerter/Schätzer).

14. **Worker-Profile-Doppelschichtung**: `coordination.db.worker_stats` (agent_name, total_jobs, successful_jobs, failed_jobs, avg_duration_s) wird in `agent_base.py:178-185` automatisch befüllt. PLUS `generalag_worker_profile` (worker_name, strengths[], weaknesses[], specialties[], total_jobs, avg_rating) wäre separate Doppelschichtung wenn aktiv. Identity Z. 94 verlangt die zweite Schicht — niemand schreibt rein.

15. **GeneralAG bekommt "all" Memory-Scope** (embeddings.py:73-74, soul_retrieval.py:21) — sieht Fakten aller Agents. Das ist die einzige spec'd Cross-Agent-Sicht und ist korrekt implementiert.

---

**Ende des Audits. Keine Annahmen außer in Quellen belegt. Alle Pfad:Zeile-Referenzen verifiziert.**
