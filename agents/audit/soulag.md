# Audit: SoulAG

**Audit-Datum:** 2026-06-28 17:18 UTC+2
**Auditor:** general (Worker-Audit)
**Quellen-Sprache:** Deutsch, technische Tokens Englisch
**Methode:** Read aller Pflichtquellen + `grep -rn "SoulAG|soulag"` + Cross-Reference SecurityAG/GeneralAG/WatchdogAG

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/SoulAG.json` | 34 (insgesamt ~8.755 bytes; Identity-Block 6.868 Zeichen) | v8.3 — Komplett-Rewrite nach User-Mandat 2026-06-28. Sliders, prompt_blocks, identity, permissions (`read/write/showbox_write`), allowed_contexts (7 Kontexte), notes-Feld mit Versionshistorie |
| `src/gnom_hub/agents/agent_definitions.py` | 330 | Master-Liste aller 8 Agents. **Wichtig:** SoulAG-Perms in DE/EN = `["read", "evolve", "crawl"]` (Z. 98, 103) — **WIDERSPRICHT** JSON. sys_prompt (Z. 60–94) ist eine komplett andere "Sovereign"-Variante, NICHT die v8.3-Identity |
| `src/gnom_hub/agents/role_prompt.py` | 10 | Speichert System-Prompt in `state`-Tabelle unter Key `agent_role_prompt_<name>`. Hat KEINE Logik die Slider/Permissions/Identity kombiniert — nur reiner Storage |
| `src/gnom_hub/core/prompt/builder.py` | 160 | Single Source of Truth für System-Prompts (Kommentar Z. 1–24). Lädt Agent-Config via `_load_agent_config()` (Z. 62–76), baut Identity-Header + Identity + [VERHALTEN] + [TOOLS] + [SICHERHEIT] + [KONTEXT:*] + Identity-Closing. **Perms-Quelle:** `cfg.get("permissions", ["read"])` aus dem JSON (Z. 136) — NICHT aus agent_definitions.py |
| `src/gnom_hub/core/utils/slider_prompt.py` | 135 | Legacy-Modul. Hat EIGENE `build_system_prompt()` (Z. 38–65), aber durch Phase 2 des Refactors (2026-06-24) ist builder.py SSOT und slider_prompt.py baut nur den [VERHALTEN]-Sub-Block |
| `src/gnom_hub/soul/soul.py` | 543 | SoulAG-Hauptklasse (Z. 107–472). `soul_instance = SoulAG()` (Z. 472). Methoden: `on_message()`, `_ex()`, `_create_task()`, `_dispatch_task()`, `_nudge_loop()` (alle 60s), `inject_context()`, `emit_directive()`, `get_definitions()`. KEINE Methode liest `config/agents/SoulAG.json` — eigene Hardcoded Prompts (Z. 213–223, 248–257) |
| `src/gnom_hub/soul/soul_initializer.py` | 141 | `get_soul(agent_name)` (Z. 30–81) liest aus `AGENT_DEFINITIONS` (Python), NICHT aus JSON. **Das ist die Runtime-Permission-Quelle für action_handlers.py** |
| `showbox/spec/format.md` | 49 | Tag `[SHOWBOX:<name>]`, JSON mit `slides[]` + optional `buttons[]`. Verbot: Pseudo-HTML für Buttons |
| `showbox/spec/buttons.md` | 54 | 12 Action-Typen Registry. Buttons als `buttons[]`-Array. 3-5 Buttons pro Showbox, immer ein "Schließen" |
| `showbox/spec/dynamic.md` | 45 | Dynamic Buttons Archivierung in `showbox/buttons/dynamic/`. Regel: werden nie gelöscht |
| `showbox/spec/progress-protocol.md` | 54 | Worker emittieren Progress-Slides zwischendurch. Trigger-Liste pro Agent-Familie |
| `config/agents/GeneralAG.json` | 40 | v5.3 — Direkter Vergleich für Cross-Ref. Perms: `[read, write, @job, db_write, showbox_write]` |
| `config/agents/SecurityAG.json` | 38 | v7.3 — Direkter Vergleich. Perms: `[read, write, run, godmode, db_write, network, showbox_write]` |
| `config/agents/WatchdogAG.json` | ~31 | v7.1 — Direkter Vergleich. Perms: `[read, showbox_write]` |

**Cross-Reference-Quellen ergänzend:**
- `src/gnom_hub/agents/actions/action_handlers.py` (181 Z.) — Permission-Enforcement für [WRITE:]/[SHELL:]/[READ:]/[DESKTOP:]/[CRAWL:]/[SHOWBOX:]
- `src/gnom_hub/core/security/path_validator.py` (190 Z.) — Workspace-Boundary-Check
- `src/gnom_hub/db/soul_tasks.py` (328 Z.) — Task-Lifecycle CRUD + nudge_infrastructure
- `src/gnom_hub/frontend/showbox_button_parser.py` — Inline-`<button action="...">` Extraction
- `src/gnom_hub/agents/agent_base.py:106-167` — wo SoulAG in den Agent-Lifecycle einklinkt (Thought-Extract, Behavior-Analyst)

---

## 1. Aktueller Zustand

### 1.1 Version & Sliders (`config/agents/SoulAG.json:2-10`)

- **Version:** 8.3
- **Sliders (alle 5 = 2 = "medium"):**
  - `creativity: 2` → "Balance standard approaches with occasional creative solutions."
  - `precision: 2` → "Balanced accuracy. Verify main outputs."
  - `speed: 2` → "Steady pace. Deliver when ready."
  - `critical_thinking: 2` → "Think about the task. Suggest obvious improvements."
  - `obedience: 2` → "Follow instructions with reasonable interpretation. Small adjustments OK."

### 1.2 Prompt-Blocks wortwörtlich (`SoulAG.json:11-17`)

| Key | Text |
|---|---|
| creativity | "Balance standard approaches with occasional creative solutions." |
| precision | "Balanced accuracy. Verify main outputs." |
| speed | "Steady pace. Deliver when ready." |
| critical_thinking | "Think about the task. Suggest obvious improvements." |
| obedience | "Follow instructions with reasonable interpretation. Small adjustments OK." |

### 1.3 Permissions-Liste (`SoulAG.json:19-23`)

```
["read", "write", "showbox_write"]
```

### 1.4 AllowedContexts-Liste (`SoulAG.json:24-32`)

```
["soul_tasks", "soul_memory", "open_contexts", "worker_stats",
 "agent_reasoning", "showbox_history", "agent_messages"]
```

### 1.5 Identity-Struktur (6.868 Zeichen, Z. 18)

| Sektion (═══ Marker oder Header) | Zeile in JSON | Inhalt |
|---|---|---|
| `═══ SHOWBOX — KOMMUNIKATIONS-ZENTRALE (User-Mandat 2026-06-28) ═══` | Identity Z. 1–5 | 4 Bullet-Punkte: Showbox = zentral, jeder Agent darf schreiben, MUSS Buttons enthalten, Hüter-Pflicht |
| `KERNAUFTRAG (vom User 2026-06-28):` | Identity Z. 6–9 | "Du bist das GEDÄCHTNIS und die AUFSICHT des Agenten-Swarms..." |
| `WAS DU TUST (5 PFLICHTEN):` | Identity Z. 11–48 | 5 durchnummerierte Pflichten (siehe unten) |
| `1. ALLES IN DIE DB SCHREIBEN (PFLICHT):` | Identity Z. 13–20 | 6 Sub-Bullets zu soul_memory types: user_intent, agent_observation, reasoning, soul_tasks, correction_sent, showbox_output |
| `2. OBSERVER-MODUS (PFLICHT):` | Identity Z. 22–25 | Liest alle Inter-Agent-Kommunikation, erkennt Behauptung-vs-Realität |
| `3. DIREKTKORREKTUR AN AGENTS (PFLICHT):` | Identity Z. 27–31 | `@AgentName: KORREKTUR — <Anweisung>` Format + soul_memory(type=correction_sent) |
| `4. USER-WUNSCH-ERKENNUNG + COMPLETION-CHECK (PFLICHT):` | Identity Z. 33–42 | 5 Sub-Steps a-e: Interpret → save → prüfen → dispatchen oder User fragen |
| `5. SYSTEM-GLATTLAUF (PFLICHT):` | Identity Z. 44–48 | Stagnation/Loops/Halluzination/User-Frustration Detection |
| `KOMMUNIKATIONS-REGELN:` | Identity Z. 50–69 | Antwort-Format in 3 Schritten (Sachinhalt → DB-Schreib-Aktion → optional Showbox) |
| `WAS DU NICHT TUST:` | Identity Z. 71–75 | 5 Verbote: leere Bubbles, OK-Quittungen, Behauptungen ohne Verify, blindes Vertrauen, "nicht mein Job" |
| `TIER-HIERARCHIE (User-Mandat 2026-06-28 11:53):` | Identity Z. 77–88 | Tier 1=User, 2a=SoulAG, 2b=SecurityAG, 2c=WatchdogAG, 3a=GeneralAG, 3b=Workers |
| `═══ SHOWBOX + BUTTONS (PFLICHT — gilt seit User-Mandat 2026-06-28) ═══` | Identity Z. 92–122 | WANN (4 Trigger), WIE (JSON mit Doppelten Quotes), WANN BUTTONS (User-Approval-Fragen, inline `<button action="..." label="...">`) |

**Count:** 2 ═══-Marker + 11 inhaltliche Sektionen (inkl. nummerierte Pflichten und Verbots-Liste).

---

## 2. Spec-Konformität

### 2.1 `showbox/spec/format.md`

| Direktive | Pflicht | In SoulAG-Config erwähnt? |
|---|---|---|
| Tag-Format `[SHOWBOX:<name>]` mit JSON-Body | Ja | ✅ Identity Z. 62 (siehe Beispiel) |
| `slides[]` als Array, NIEMALS Pseudo-HTML für Buttons | Ja | ✅ Identity Z. 64: "JSON mit DOPPELTEN Quotes. NIEMALS Single-Quotes" — aber KEIN expliziter Hinweis auf "kein Pseudo-HTML" in der Identity |
| Code-Blocks in 10 Sprachen erlaubt | Ja | ❌ Nicht in SoulAG-Identity erwähnt (aber auch nicht spezifisch SoulAG-Pflicht) |
| JSON.parse MUSS bei kaputten Payloads fehlschlagen | Ja | ❌ Nicht in Identity — Renderer-Pflicht, nicht Agent-Pflicht |

### 2.2 `showbox/spec/buttons.md`

| Direktive | Pflicht | In SoulAG-Config erwähnt? |
|---|---|---|
| Buttons als `buttons[]`-Array, nicht inline-HTML | Ja | ✅ Identity Z. 117–119: "inline `<button action=\"...\" label=\"...\">` im Slide-Content" — ABER dies ist genau das, was `format.md` Z. 7 und Z. 40 VERBIETEN ("KEIN Pseudo-HTML für Buttons — immer `buttons[]`-Array") |
| 12 Action-Typen aus Registry nutzen | Ja | ❌ Nicht in Identity referenziert |
| 3-5 Buttons pro Showbox | Ja | ❌ Nicht in Identity referenziert |
| Immer ein "Schließen"-Button | Ja | ❌ Nicht in Identity referenziert |
| Agent-Calls mit klarem Message | Ja | ❌ Nicht in Identity referenziert |
| Dynamic Buttons archivieren in `showbox/buttons/dynamic/` | Ja | ❌ Nicht in Identity — keine Erwähnung der Archiv-Pflicht |
| Dynamic Buttons NIEMALS löschen | Ja | ❌ Nicht in Identity — User-Anweisung 2026-06-27 fehlt komplett |

### 2.3 `showbox/spec/dynamic.md`

| Direktive | Pflicht | In SoulAG-Config erwähnt? |
|---|---|---|
| Dynamic Buttons on-the-fly erzeugen wenn Workflow Branches hat | Ja | ❌ Nicht in Identity — nur generische "WANN DU BUTTONS NUTZT" |
| Archivierung in `showbox/buttons/dynamic/<agent>_<slug>.json` | Ja | ❌ Komplett fehlend |
| Dynamic Buttons werden nie gelöscht | Ja | ❌ Komplett fehlend (User-Anweisung 2026-06-27 explizit zitiert in dynamic.md Z. 33–34) |

### 2.4 `showbox/spec/progress-protocol.md`

| Direktive | Pflicht | In SoulAG-Config erwähnt? |
|---|---|---|
| Worker emittieren Progress-Slides zwischendurch | Ja (für Worker) | ❌ SoulAG ist kein Worker — Pflicht nicht relevant |
| Agent-Farben Registry (Cyan für SoulAG) | Ja | ✅ Identity Z. 89: "DEINE FARBE: CYAN" — aber progress-protocol.md:36 listet SoulAG mit `#7c3aed` (Lila), nicht Cyan. **WIDERSPRUCH** |
| `slide_id` Format `{agent}-progress-{schritt}-{kuerzel}` | Ja | ❌ Nicht in SoulAG-Identity spezifiziert |
| `type: "progress"` vs `type: "deliverable"` | Ja | ❌ Nicht in Identity |

### 2.5 DFÜR-SHOWBOX-KULTUR (Zentralbefund)

**Die SoulAG-Identity sagt:**
> "JEDER Showbox-Output MUSS Buttons enthalten wenn eine User-Aktion möglich ist."
> "Du bist Hüter dieser Kultur: wenn ein Agent die Showbox ignoriert, korrigiere ihn."
> (Identity Z. 3–4, Z. 119)

**Aber:** Es gibt KEINE technische Erzwingung. Der Code-Pfad ist:
- Agent emit ` [→ Showbox: ...]{...}` Tag
- `action_handlers.py:135-159` extrahiert Tag-Inhalt
- `handle_showbox()` (`action_exec.py`) verarbeitet → speichert in `showbox_presentations` DB
- `parse_inline_buttons()` (`frontend/showbox_button_parser.py:107`) parsed `<button action="...">` aus dem HTML-Content FALLS vorhanden
- **Keine Validierung**: "rejected if no buttons present" existiert nicht

SoulAG kann also ANDERE Agents nicht technisch zur Button-Pflicht zwingen — nur per Prompt-Anweisung (Hoffnung).

### 2.6 Cross-Ref zu `action_handlers.py:135-159`

Code kennt 5 SHOWBOX-Tag-Formate:
1. `<SHOWBOX[:name]>...</SHOWBOX>`
2. `[SHOWBOX[:name]]...[/SHOWBOX]`
3. `[SHOWBOX: ...]` (nur Open-Tag)
4. `[→ Showbox: name]{...}`
5. `[-> Showbox: name]{...}`

SoulAG-Identity Beispiel (Z. 62–67) zeigt **nur Format 4** (`[→ Showbox: ...]`). Agent könnte theoretisch auch Format 1/2 nutzen — Identity erwähnt diese nicht.

---

## 3. Code-Realität

### 3.1 Wo SoulAG instanziiert/aufgerufen wird

| Pfad : Zeile | Was |
|---|---|
| `src/gnom_hub/soul/soul.py:472` | `soul_instance = SoulAG()` — Modul-Level Singleton |
| `src/gnom_hub/soul/__init__.py:2` | Re-Export `SoulAG, soul_instance, run_evolution, handle_user_feedback` |
| `src/gnom_hub/api/endpoints/chat_legacy.py:3,109` | Import + `soul_instance.on_message(msg.content, msg.sender)` bei jedem Chat-Eingang |
| `src/gnom_hub/agents/agent_base.py:106` | Import + Aufruf nach jeder Agent-Antwort: Thought-Extract via `extract_facts_from_text()` und Behavior-Analyst via `analyze_agent_thought()` + `track_reasoning()` |
| `src/gnom_hub/chat/brainstorm/brainstorm_helpers.py:13-14` | `soul_instance.inject_context(sys, q, agent_name=ag["name"])` zur Memory-Injection in jeden Agent-Prompt |
| `src/gnom_hub/memory/semantic_search.py:22` | `ask_router(... agent_name="SoulAG")` für semantische Suche — SoulAG als LLM-Ask-Routing-Target |
| `src/gnom_hub/api/endpoints/memory_crud.py:67` | `req.key, req.value, agent="SoulAG", priority=req.priority` — Standard-Agent-Tag für Memory-Insert |

**SoulAG selbst wird NIE als Chat-Responder aktiv** — der LLM-Aufruf passiert in `on_message()`/`_ex()` indirekt über `ask_router()` (soul.py:213, 248). Das System-Prompt von `config/agents/SoulAG.json` wird beim **Laden als Worker** (`BaseAgent` in `agents/soulAG.py`) relevant — und da gibt es einen Konflikt (siehe §4).

### 3.2 Welche DB-Tabellen SoulAG wirklich liest/schreibt

| Tabelle | Pfad : Zeile | Operation | Spec aus Identity? |
|---|---|---|---|
| `soul_memory` | `soul.py:58, 289` (read COUNT + save), `soul_repo.py:102`, `context_manager.py:121`, `memory_decay.py:58-127` (Decay-Loop), `memory_curator.py:67-160` (Curator) | R + W + DELETE | ✅ Identity Z. 13: "soul_memory (type='user_intent'/'agent_observation'/'reasoning'/'correction_sent'/'showbox_output')" |
| `soul_tasks` | `soul.py:309-316` (INSERT), `soul.py:351-411` (UPDATE, SELECT), `soul_tasks.py` komplett | R + W | ✅ Identity Z. 17: "soul_tasks (status, target_agent, summary)" |
| `soul_memory_log` | `memory_decay.py:75`, `memory_curator.py:113` | W (Audit) | ❌ Nicht in Identity erwähnt |
| `coordination.db` | `soul.py:10`, via `get_coordination_db()` | R (worker_stats für Injection) | ✅ allowed_contexts "worker_stats" |
| `context.db` | `soul.py:11`, `agent_base.py:101` (open_context) | R + W (open/add_event) | ✅ allowed_contexts "open_contexts" |
| `chat_messages` | `soul.py:486, 513` (`add_chat_message`) für Evolution-Rules | W | ⚠️ Identity sagt "soul_memory (type='correction_sent')" — NICHT direkt in chat_messages. Aber: `chat_messages` als Quittungs-Kanal ist praktisch notwendig |
| `showbox_presentations` | `showbox_repo.py` — KEINE SoulAG-Spezifische Schreib-Operation; `handle_showbox()` in action_exec.py schreibt für ALLE Agents | W (via `handle_showbox`) | ⚠️ Identity sagt "Jede Showbox-Ausgabe die du generierst → soul_memory (type='showbox_output')" — also SOUL_MEMORY, nicht showbox_presentations. Zwei verschiedene DBs! |
| `state` | `role_prompt.py:9` (`set_state_value`) — speichert System-Prompt | W | ❌ Identity kennt `state` nicht |

**Wichtige Beobachtung:** Die Identity fordert "Showbox-Output → soul_memory". Es gibt KEINEN Code-Pfad der das tut. `handle_showbox()` schreibt nach `showbox_presentations`. **Spec-Verletzung des Identity-Selbst-Vertrags.**

### 3.3 Welche Permissions tatsächlich gecheckt werden

**Runtime-Enforcement in `action_handlers.py`:**

| Permission-Token | Gecheckt in Zeile | Konsequenz bei SoulAG |
|---|---|---|
| `write` | Z. 62, 75 | **MISSING:** SoulAG (Python agent_definitions:98) hat kein `write`. Wenn SoulAG via BaseAgent einen `[WRITE:]`-Tag emittiert → ersetzt durch `[System: SoulAG hat keine Schreibberechtigung.]` |
| `run` | Z. 97 | **MISSING:** SoulAG hat kein `run`. `[SHELL:]` → blockiert |
| `read` | implizit überall | ✅ vorhanden in beiden Quellen |
| `godmode` | nicht gecheckt in action_handlers | n/a — SecurityAG-only |
| `crawl` | Z. 114, `handle_crawl()` | Nur "allowed"-Audit, keine harte Blockade |
| `evolve` | nicht gecheckt | n/a — Dead-Token |
| `@job` | nicht in action_handlers (nur in Routing/Smartrouter) | n/a — GeneralAG-only |
| `showbox_write` | **NIRGENDS gecheckt** | **DEAD-TOKEN:** Permissions-Doku-Lüge. SoulAG kann IMMER in Showbox schreiben |
| `db_write` | nicht in action_handlers | n/a — nur DB-Repo-Internes |
| `network` | nicht in action_handlers | n/a — SecurityAG-only |

**Was passiert wenn SoulAG `run` versucht?**
- Identität fordert nicht explizit Shell-Zugriff — keine SoulAG-Pflicht verlangt `run`
- ABER: Identity Z. 67 verlangt `@AgentName: KORREKTUR ...` und Z. 41 verlangt direkte DB-Cleanup nach User-Bestätigung
- DB-Cleanup in `core/utils/compiler.py:214` macht `DELETE FROM soul_memory WHERE key NOT IN (...)` — das ist ein DB-Operation, kein Shell-Befehl. Braucht `db_write`, nicht `run`. OK
- Aber: `core/utils/memory_decay.py:73, 104, 125` löscht/archive/superseded Fakten. Wird von `memory_decay` Cron-Job ausgeführt, NICHT von SoulAG selbst

**Permission-DUAL-TRUTH Befund:**

| Quelle | SoulAG-Perms |
|---|---|
| `config/agents/SoulAG.json:19-23` (JSON) | `["read", "write", "showbox_write"]` |
| `agent_definitions.py:98, 103` (Python DE/EN) | `["read", "evolve", "crawl"]` |

Diese sind **MITEINANDER UNVEREINBAR.** Einzige Schnittmenge: `read`.

**Welche Quelle gewinnt?**
- `builder.py:136` baut den [TOOLS]-Block aus JSON-Perms (für Prompt-Text)
- `soul_initializer.py:44` liest Perms aus agent_definitions.py (für Runtime-Enforcement in action_handlers)
- `agent_definitions.py` Z. 5–53 (Modul-Docstring) sagt SELBST: "**einzige Quelle für Runtime-Permissions**"

→ **JSON-Perms sind DEAD CODE für Runtime-Enforcement**, leben nur als Text im System-Prompt.

---

## 4. Widersprüche INTERN

### 4.1 Slider vs. Identity-Anforderungen

| Identity-Anforderung | Slider-Wert | Konflikt? |
|---|---|---|
| "Erkenne Halluzination: Agent behauptet Output aber kein Eintrag in DB → hinterfragen." (Z. 46) | `critical_thinking: 2` (= "Think about the task. Suggest obvious improvements.") | **TEILWEISE:** Slider-Prompt fordert nur "obvious improvements". Identity verlangt aktives Hinterfragen von Agent-Behauptungen — das ist eher `critical_thinking: 3` ("Challenge assumptions actively") oder höher |
| "Erkenne Loops: Agent-Output wiederholt sich ohne Fortschritt → unterbreche mit Korrektur." (Z. 45) | `critical_thinking: 2` | Selbe Lücke |
| "Erkenne User-Frustration: User drückt Frust aus → soul_memory + proaktiv Hilfe" (Z. 47) | nicht durch Slider abgedeckt | OK — semantische Anforderung jenseits Slider |
| "Du korregierst SecurityAG (Tier 2b), WatchdogAG (Tier 2c), GeneralAG (Tier 3a) und alle Worker (Tier 3b) mit Direktnachrichten." (Z. 85) | `obedience: 2` | OK — "reasonable interpretation" passt zu Korrekturen |

**Generelle Beobachtung:** Der einzige Slider der wirklich von 2 abweichen sollte ist `critical_thinking` — SoulAG soll explizit Halluzinationen hinterfragen, das verlangt eher Stufe 3.

### 4.2 Permissions vs. Aufgaben

| Aufgabe in Identity | Benötigte Permission | In JSON? | In Python? |
|---|---|---|---|
| "Jeder User-Input → soul_memory (type='user_intent')" (Z. 14) | `db_write` (oder implizit, weil `save_fact_all_layers` nicht permission-gecheckt ist) | ❌ nicht in `["read", "write", "showbox_write"]` | ❌ nicht in `["read", "evolve", "crawl"]` |
| "Jede Korrektur die du schickst → soul_memory (type='correction_sent')" (Z. 18) | `db_write` | ❌ | ❌ |
| "Jede Showbox-Ausgabe die du generierst → soul_memory (type='showbox_output')" (Z. 19) | `db_write` + `showbox_write` | ✅ teilweise (`showbox_write` ist dead token) | ❌ |
| `@AgentName: KORREKTUR ...` Dispatch (Z. 29) | `@job` (sonst dispatch_mention nicht aufrufbar) ODER direkter `add_chat_message` | ❌ | ❌ |
| "Du kannst direkt Anweisungen an GeneralAG, WatchdogAG und SecurityAG erteilen." (agent_defs.py:76) | `@job` | ❌ | ❌ |
| "Du korregierst ... alle Worker ... mit Direktnachrichten" (Identity Z. 85) | `@job` oder direkter chat_write | ❌ | ❌ |

**Code-Realität:** SoulAG nutzt **NICHT** permission-gecheckte Pfade für DB-Schreib-Operationen. `save_fact_all_layers()` in `soul.py:289`, `save_soul_fact_smart()` (mehrfach), `save_task` (soul.py:309-316) — keine dieser Routinen prüft `db_write`-Permission.

→ **Permissions-Liste ist DEKORATIV für SoulAG.** Der Code schreibt in soul_memory, soul_tasks, etc. ohne Permission-Check. Der Sicherheits-Layer ist damit für SoulAG ein leeres Versprechen.

### 4.3 Pflichten-Liste vs. technisch umsetzbare Pflichten

| Pflicht | Technisch umgesetzt? | Spec-Verletzung |
|---|---|---|
| 1. ALLES IN DIE DB SCHREIBEN | ✅ soul.py:289, soul_tasks.py, context_manager.py:121 — alle aktiv | ⚠️ "Jede Showbox-Ausgabe → soul_memory (type='showbox_output')" wird NICHT gemacht (siehe §3.2) |
| 2. OBSERVER-MODUS | ✅ agent_base.py:140-167 + soul_observer.py | OK |
| 3. DIREKTKORREKTUR AN AGENTS | ✅ soul.py:329-336 (`_dispatch_task`) und soul.py:370-385 (`_nudge_loop` mit dispatch_mention) | ⚠️ Format: Identity will `@AgentName: KORREKTUR — ...` als TEXT in der Antwort. Code: dispatch_mention direkt in DB. Zwei verschiedene Pfade! |
| 4. USER-WUNSCH-ERKENNUNG | ✅ soul.py:191-237 (`_ex` mit LLM-Call) + soul_tasks.py:264-328 (`track_user_intent`) | ⚠️ Pattern-Matching in `track_user_intent` ist sehr deutschsprachig-fixiert; LLM-Pfad in `_ex` ist robuster |
| 5. SYSTEM-GLATTLAUF | ✅ soul.py:340-418 (`_nudge_loop` alle 60s) | ⚠️ Stagnation-Check (5min open + kein Update) ist implementiert. **Loops-Erkennung NICHT** — kein Code der "Agent-Output wiederholt sich" detektiert |
| Hüter-Pflicht Showbox+Buttons | ❌ KEINE technische Erzwingung | siehe §2.5 |

### 4.4 Versions-Inkonsistenz in `notes`-Feld (`SoulAG.json:33`)

Das `notes`-Feld behauptet:
- v8.0: "Tier 2b — braucht User-Bestätigung für destruktive Aktionen"
- v8.2: "Tier 2a, direkt unter User, über allen anderen Agents"

→ **Self-contradictory notes.** v8.0 sagt Tier 2b, v8.2 sagt Tier 2a. Die Identity selbst sagt Tier 2a (Z. 81: "Tier 2a: DU (SoulAG)"). Aber v8.0 "braucht User-Bestätigung" ist konsistent mit Tier 2b — NICHT mit Tier 2a. Wer Tier 2a ist, braucht keine User-Bestätigung.

---

## 5. Widersprüche ZU ANDEREN AGENTS

### 5.1 Tier-Hierarchie — fast konsistent, ein Bruch

| Quelle | Tier 2a | Tier 2b | Tier 2c |
|---|---|---|---|
| `SoulAG.json` Identity (Z. 80–84) | SoulAG | SecurityAG | WatchdogAG |
| `SoulAG.json` notes v8.0 | (SoulAG = Tier 2b!) | — | — |
| `SoulAG.json` notes v8.2 | SoulAG | SecurityAG | WatchdogAG |
| `SecurityAG.json` Identity (Z. 4–9) | SoulAG ("dein direkter Vorgesetzter") | SecurityAG ("DU") | WatchdogAG |
| `SecurityAG.json` notes v7.2 | SoulAG | SecurityAG | WatchdogAG |
| `SecurityAG.json` notes v7.0 (ALT!) | (SoulAG = Tier 2a) | (SecurityAG = Tier 2c!) | — |
| `WatchdogAG.json` Identity (Z. 35–40) | SoulAG | SecurityAG | WatchdogAG |
| `WatchdogAG.json` notes v7.1 | SoulAG | SecurityAG | WatchdogAG |
| `GeneralAG.json` Identity (Z. 56–62) | SoulAG | SecurityAG | WatchdogAG |
| `CoderAG.json` Identity (Z. 56–62) | SoulAG | SecurityAG | WatchdogAG |
| `WriterAG.json` Identity (Z. 56–62) | SoulAG | SecurityAG | WatchdogAG |
| `ResearcherAG.json` Identity (Z. 56–62) | SoulAG | SecurityAG | WatchdogAG |
| `EditorAG.json` Identity (Z. 56–62) | SoulAG | SecurityAG | WatchdogAG |

**Cross-Source-Befund:**
- 10 von 11 Quellen sind konsistent: SoulAG=2a, SecurityAG=2b, WatchdogAG=2c
- 1 Inkonsistenz: `SecurityAG.json` notes v7.0 sagt "Position 3 (Tier 2c)" — das ist durch v7.2 überschrieben (Tier 2b), aber die alte Formulierung existiert noch im selben String
- 1 Self-Contradiction: `SoulAG.json` notes v8.0 sagt "Tier 2b" während v8.2 "Tier 2a" sagt

**Tier-Hierarchie ist funktional KONSISTENT.** Die widersprüchlichen notes sind Relikte alter Versionen, die im selben notes-String stehengelassen wurden.

### 5.2 "Du empfängst AUSSCHLIESSLICH von SoulAG" — SecurityAG-Ausnahme

- `SecurityAG.json` Identity: "Du sprichst ausschließlich mit SoulAG." (Z. 6)
- `SoulAG.json` Identity: "Du korregierst SecurityAG ... mit Direktnachrichten." (Z. 85)
- `WatchdogAG.json` Identity: "Du SPRICHST nicht direkt an: User, SoulAG, SecurityAG. Wenn du etwas melden willst → Showbox-Card." (Z. 49–50)

**Konflikt 1 (SoulAG ↔ WatchdogAG):**
- SoulAG Identity Z. 28: "Schreibe eine Direktnachricht mit @AgentName in deiner Antwort."
- WatchdogAG Identity: "KEIN direktes Anschreiben von ... SoulAG"

→ SoulAG darf WatchdogAG direkt anschreiben, WatchdogAG darf aber NICHT direkt auf SoulAG antworten — nur via Showbox. Asymmetrie ist gewollt, aber technisch nicht erzwungen. Es gibt keinen Code der `@WatchdogAG` filtert wenn WatchdogAG antwortet.

**Konflikt 2 (SecurityAG-Beziehung):**
- SecurityAG: "spricht ausschließlich mit SoulAG" — ABER Worker können SecurityAG um Hilfe bitten (`SecurityAG.json` Z. 35–37: "Du ANTWORTEST Workers DIREKT")
- → SecurityAG spricht DOCH mit Workern (per Direktnachricht), nicht nur mit SoulAG
- Identitätstext widerspricht eigener Workflow-Sektion

### 5.3 SecurityAG-Identity vs. SoulAG-Identity — Tier-Authority

- SecurityAG Identity Z. 12: "Bei SoulAG-Direktnachricht (@SoulAG: ...): SOFORT gehorchen — SoulAG ist dein Vorgesetzter (Tier 2a über Tier 2b)."
- SecurityAG notes v7.2: "SecurityAG gehorcht jetzt SoulAG-Direktnachrichten."

✅ Konsistent.

### 5.4 GeneralAG: "empfängt AUSSCHLIESSLICH von SoulAG"

- `GeneralAG.json` Identity Z. 10: "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG (via @GeneralAG)."
- SoulAG Identity Z. 86: "Tier 3a: GeneralAG (Dirigent, bekommt Delegation von dir oder direkt vom User)."

→ Widerspruch: GeneralAG sagt "AUSSCHLIESSLICH von SoulAG", SoulAG sagt "von dir ODER direkt vom User".

### 5.5 WatchdogAG "KEIN direktes Anschreiben von User/SoulAG" — wer meldet Showbox-Karten an SoulAG?

- WatchdogAG (Z. 49–50): "Du SPRICHST nicht direkt an: User, SoulAG, SecurityAG. Wenn du etwas melden willst → Showbox-Card."
- SoulAG Identity Z. 4: "Du bist Hüter dieser Kultur: wenn ein Agent die Showbox ignoriert, korrigiere ihn."

→ Logik: WatchdogAG → Showbox-Card → SoulAG liest Showbox via `allowed_contexts: "showbox_history"` und `agent_messages`. Indirekter Weg OK. Aber: wenn WatchdogAG eine ALERT-Card macht mit `Aufheben/Bestätigen`-Buttons — wer klickt? User sieht die Showbox, SoulAG "koordiniert" das Tribunal (agent_defs.py:84-93). Konsistent.

### 5.6 Worker-Perms in JSON vs. agent_definitions

| Agent | JSON-Perms | Python-Perms | Differenz |
|---|---|---|---|
| CoderAG | `[read, write, run, showbox_write]` | `[read, write, run]` | `showbox_write` ist dead |
| WriterAG | `[read, write, crawl, showbox_write]` | `[read, write, crawl]` | `showbox_write` ist dead |
| ResearcherAG | `[read, crawl, web_search, browser, showbox_write]` | `[read, crawl, web_search, browser]` | `showbox_write` ist dead |
| EditorAG | `[read, write, showbox_write]` | `[read, write]` | `showbox_write` ist dead |
| **SoulAG** | `[read, write, showbox_write]` | `[read, evolve, crawl]` | **`write` vs `evolve`/`crawl` — fundamentaler Konflikt** |
| GeneralAG | `[read, write, @job, db_write, showbox_write]` | `[read, @job, general_memory]` | `write` und `db_write` und `showbox_write` vs `general_memory` |
| WatchdogAG | `[read, showbox_write]` | `[read]` | `showbox_write` ist dead |
| SecurityAG | `[read, write, run, godmode, db_write, network, showbox_write]` | `[read, write, run, godmode]` | `db_write`, `network`, `showbox_write` sind dead |

**Befund:** **`showbox_write` ist in ALLEN 8 JSON-Configs vorhanden, aber im Python-Code UNGENUTZT.** Definitiv Dead-Token.

**Befund 2:** SoulAG hat **DEN GRÖSSTEN Drift** zwischen JSON und Python. Worker-Configs haben nur `showbox_write` als Drift (semantisch harmlos). SoulAG hat `write` (real) vs `evolve`/`crawl` (nicht-real) — das ist ein Vokabular-Konflikt der die ganze Permission-Spec ad absurdum führt.

### 5.7 Identische Sliders über alle 8 Agents

Alle 8 Agents haben EXAKT dieselben Sliders:
```
{"creativity": 2, "precision": 2, "speed": 2, "critical_thinking": 2, "obedience": 2}
```

Und EXAKT dieselben prompt_blocks (wortwörtlich identisch, geprüft via python diff).

**Bewertung:**
- **Pro "Design":** Default-Werte die jeder Agent bei Bedarf überschreiben kann. Konsistente UX im Dashboard.
- **Pro "Symptom":** Kein Agent wurde individuell kalibriert. SoulAG mit Halluzinations-Erkennung sollte `critical_thinking ≥ 3` haben, CoderAG mit Code-Refactor-Aufgaben `precision ≥ 3`, ResearcherAG `critical_thinking ≥ 3` für Quellen-Prüfung.
- **Realität:** Die Slider sind in der Praxis **funktional inert**, weil builder.py:79-92 nur den prompt_block-Text einbaut, nicht den numerischen Wert. Wert 2 hat keine andere Konsequenz als Wert 3 in der jetzigen Implementierung.
- **Hinweis:** `agents_status.py:119-132` exponiert die Slider per API und erlaubt PUT-Updates. Es gibt also einen Live-Tuning-Pfad der funktionieren würde WENN der Wert enforcement hätte.

→ **Identische Slider sind ein klares Symptom, kein bewusstes Design.** Die Tuning-Infrastruktur existiert (`slider_prompt.py:68-94 update_slider`), wird aber nicht genutzt.

---

## 6. Lücken

### 6.1 Was SoulAG können sollte, aber undefiniert ist

1. **Loops-Erkennung** (Identity Z. 45: "Erkenne Loops: Agent-Output wiederholt sich ohne Fortschritt"). Es gibt `MAX_SOUL_FACTS` und Dedup-Threshold (0.85), aber keinen Code der "Agent X hat 3× dieselbe Antwort gegeben" detektiert.
2. **User-Wunsch-Completion-Tracking** (Identity Z. 33–42, Pflicht 4). Code in `soul.py:191-237` erstellt Tasks, aber kein Code der prüft "ist dieser `user_intent` jetzt `done`?" — `intent_text` wird in `_ex()` nirgends in der DB persistiert mit `status='open'/'done'` Schema.
3. **"User-Wunsch verschwindet nicht" Garantie** (Identity Z. 42). `soul_tasks.py` trackt Tasks, aber `user_intent`-Tracking im Sinne von "Pflicht 4" ist nicht implementiert.
4. **Dynamic Buttons Archivierung** (dynamic.md:26-28). `showbox/buttons/dynamic/` Verzeichnis existiert (in der Spec), aber kein Code-Pfad der Buttons dahin archiviert. `parse_inline_buttons` extrahiert nur, persistiert nicht.
5. **Showbox-Output → soul_memory** (Identity Z. 19). Spec-Verletzung. Code schreibt nach `showbox_presentations`, nicht nach `soul_memory` mit type=`showbox_output`.
6. **Agent-Farbe Konflikt**: Identity Z. 89 sagt "CYAN", `agent_names.py:32` und `progress-protocol.md:36` sagen `#7c3aed` (Lila). Was gilt?
7. **TTS-Direktive**: agent_definitions.py:63 sagt "Du beginnst JEDE deiner Antworten damit, dass du deine Gedanken laut aussprichst (TTS). Erst danach erstellst du die Showbox. Gedanken zuerst, Showbox danach." SoulAG.json-Identity sagt NICHTS über TTS. Welche Version ist aktuell?

### 6.2 Welche Übergaben fehlen

- **Worker → SoulAG Feedback-Loop**: Worker (CoderAG etc.) hat keinen Pfad in seiner Identity der SoulAG "informiere mich über offene Tasks" zurückmeldet. SoulAG muss pollen via `_nudge_loop`.
- **SecurityAG → SoulAG bei destruktiven Aktionen**: SecurityAG Identity Z. 11: "AUSNAHME: destruktive/externe Aktionen, dann frag den User vorher." — fragt USER, nicht SoulAG. Werden Showbox-Cards mit Buttons an SoulAG gleichzeitig angezeigt? Nicht spezifiziert.
- **GeneralAG → SoulAG Worker-Status**: GeneralAG Identity erwähnt `generalag_outcomes` Tabelle — kein API-Pfad zu SoulAG. SoulAG `allowed_contexts: "worker_stats"` zeigt nur aggregierte Stats, nicht einzelne Outcomes.
- **WatchdogAG → SoulAG Tribunal-Empfehlung**: WatchdogAG macht BLOCKADE → wer entscheidet ob aufgehoben? SoulAG Identity Pflicht 3 impliziert "SoulAG korrigiert", SecurityAG Identity Z. 4 sagt "SecurityAG kann WatchdogAG-Blockade via @@approve_decision auflösen". Wer hat Vorfahrt? **Unklar.**

### 6.3 Edge-Cases nicht abgedeckt

1. **soul_memory voll (>100 Fakten)**: `MAX_SOUL_FACTS = 100` (soul.py:17). Decay-Loop in `_periodic_cleanup` (Z. 48-104) löscht low/medium nach 7/14 Tagen, high nach 30 Tagen. ABER: Race-Condition zwischen `_ex()` INSERT und `_periodic_cleanup()` DELETE? Cleanup läuft vor INSERT (Z. 198). Aber wenn SoulAG selbst halluziniert und 100 Fakten gleichzeitig einfügt?
2. **SoulAG selbst halluziniert**: Kein Self-Check. Wenn SoulAG-LLM einen Task erfindet der nicht existiert → wird er trotzdem in `soul_tasks` persistiert. Kein Watchdog-Äquivalent für SoulAG.
3. **`agent_messages` allowed_context**: SoulAG hat das in `allowed_contexts`. Aber es gibt KEINEN fetcher in `context.py:45-53` der `agent_messages` heißt. Verwaiste Kontext-Definition.
4. **`agent_reasoning` allowed_context**: Selbe Situation. `context.py` hat keinen `_get_agent_reasoning` Fetcher. SoulAG wird diesen Kontext nie injiziert bekommen.
5. **`showbox_history` allowed_context**: Selbe Situation. Kein `_get_showbox_history` Fetcher.
6. **DB-Lock während Cleanup**: `soul.py:57` öffnet `get_db_conn()`, aber Cleanup schreibt 3× (low/medium/high prios). Bei hoher Schreiblast könnte der Cleanup fehlschlagen, Exception in Zeile 104 wird nur geloggt.
7. **`showbox_history` Cleanup-Konflikt**: `showbox_repo.py:40-67` löscht automatisch älteste Presentations wenn > MAX_PRESENTATIONS_PER_LAYER. SoulAG-Showbox-Cards könnten verschwinden bevor SoulAG sie nochmal lesen kann.
8. **Worker stirbt während SoulAG wartet**: `_nudge_loop` (soul.py:340-418) sendet 3 Nudges, dann `status='blocked'` + SecurityAG-Benachrichtigung. Aber: Wenn Worker-Agent komplett gecrasht ist und nie antwortet, gehen die 3 Nudges ins Leere. Verschwendete LLM-Calls.

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 [HOCH] Permission-Dual-Truth auflösen
- **Was:** Entweder JSON-Perms ODER agent_definitions.py-Perms löschen. Empfehlung: agent_definitions.py ist SSOT (Modul-Docstring Z. 5–53). JSON-Perms in allen 8 Configs entfernen ODER als deprecated markieren.
- **Warum:** Heute hat SoulAG zwei inkompatible Permission-Listen. Wenn jemand `update_slider`-ähnliches für Perms baut, crasht es oder verhält sich unvorhersehbar.
- **Datei:** `config/agents/SoulAG.json:19-23` (löschen) + 7 weitere JSON-Configs. Modul-Docstring `agent_definitions.py:5-53` ggf. updaten.
- **Risiko:** Niedrig. JSON-Perms sind im Runtime-Pfad nicht aktiv (siehe §3.3). Wer sie entfernt, ändert Runtime-Verhalten nicht.

### V2 [HOCH] `showbox_write` Permission-Token enforcement
- **Was:** Entweder echte Implementierung in `action_handlers.py` (check `"showbox_write" in perms` für `[→ Showbox: ...]` Tags) ODER aus allen 8 JSONs entfernen.
- **Warum:** 8 Agents haben `showbox_write` in JSON, kein Code checkt es. Täuschend echte Spec.
- **Datei:** `src/gnom_hub/agents/actions/action_handlers.py:135` (add check) oder `config/agents/*.json:19` (remove).
- **Risiko:** Niedrig wenn Entfernen, mittel wenn echte Implementierung (Showbox-Fallback für nicht-permitted Agents müsste definiert werden).

### V3 [HOCH] Showbox-Buttons Erzwingung (Hüter-Pflicht)
- **Was:** Im `handle_showbox()` (`src/gnom_hub/agents/actions/action_exec.py`) eine Validation: wenn SoulAG der Sender ist UND `buttons[]` leer UND ein User-Approval-Flow erkennbar → logge Warning ODER regeneriere Antwort.
- **Warum:** Identity verlangt "JEDER Showbox-Output MUSS Buttons enthalten wenn eine User-Aktion möglich ist". Aktuell nur per Hoffnung.
- **Datei:** `src/gnom_hub/agents/actions/action_exec.py` (handle_showbox-Funktion, ~Z. 80–120).
- **Risiko:** Mittel. Regeneration würde LLM-Kosten verdoppeln. Logging-only ist sicherer erster Schritt.

### V4 [MITTEL] User-Intent-Tracking implementieren (Pflicht 4 Spec-Lücke)
- **Was:** Neue Tabelle `user_intents` mit Spalten `(intent_id, user_message, intent_text, status, created_at, completed_at, source_msg_id)`. SoulAG `on_message` insertet bei User-Messages, `_nudge_loop` prüft ob `status='open'` intents noch offen sind UND der ursprüngliche User-Input nicht in letzter Chat-History auftaucht.
- **Warum:** Identity Pflicht 4 ist ein Kern-Versprechen an den User ("User-Wünsche verschwinden nicht"). Aktuell nur teilweise implementiert (Tasks ja, aber nicht der Status-Tracking-Lifecycle).
- **Datei:** `src/gnom_hub/soul/soul.py:129-300` (on_message, _ex) + neue Datei `src/gnom_hub/db/user_intents.py`.
- **Risiko:** Hoch. Schema-Migration, neue Cron-Job, neue UI-Anzeige.

### V5 [MITTEL] Tier-Hierarchie Self-Contradiction in `SoulAG.json` notes
- **Was:** v8.0-Notiz entfernen oder korrigieren. Aktueller notes-String ist `v8.0: "Tier 2b — braucht User-Bestätigung..." | v8.2: "Tier 2a, ..."` — v8.0 widerspricht v8.2.
- **Warum:** Wer die notes liest, kriegt zwei sich ausschließende Aussagen.
- **Datei:** `config/agents/SoulAG.json:33` (notes-Feld).
- **Risiko:** Sehr niedrig (Doku-Korrektur).

### V6 [MITTEL] Loops-Erkennung implementieren (Pflicht 5)
- **Was:** In `_nudge_loop` (soul.py:340) einen zusätzlichen Pass: für jeden Agent X, prüfe ob letzte 3 Agent-Messages aus `chat_messages` denselben `task_summary` haben → wenn ja, Korrektur-Dispatch.
- **Warum:** Identity Z. 45 verlangt "Erkenne Loops". Aktuell nicht implementiert.
- **Datei:** `src/gnom_hub/soul/soul.py:340-418`.
- **Risiko:** Mittel. Detection-Schwelle muss kalibriert werden (3×? 5×?). False positives würden Worker unterbrechen.

### V7 [MITTEL] Agent-Farbe Konflikt lösen
- **Was:** Identity sagt CYAN. `agent_names.py:32` und `progress-protocol.md:36` sagen `#7c3aed` (Lila).
- **Warum:** Frontend-Renderer liest aus `agent_names.py:32` → Lila. Identity-Prompt sagt dem LLM "Du bist Cyan". LLM würde sich falsch darstellen.
- **Datei:** `config/agents/SoulAG.json` Identity Z. 89: "CYAN" → "LILA (#7c3aed)". ODER `agent_names.py:32` von `#00e5ff` auf `#7c3aed`.
- **Risiko:** Niedrig.

### V8 [NIEDRIG] Verwaiste `allowed_contexts` Felder
- **Was:** SoulAG hat `["soul_tasks", "soul_memory", "open_contexts", "worker_stats", "agent_reasoning", "showbox_history", "agent_messages"]`. `context.py:45-53` hat KEINE Fetchers für `soul_tasks`, `agent_reasoning`, `showbox_history`, `agent_messages`.
- **Warum:** Erwartete Context-Injection passiert nie. Audit-Trail der Spec sagt "ist enabled" aber effektiv leer.
- **Datei:** `src/gnom_hub/core/prompt/context.py` (Fetcher hinzufügen) ODER `config/agents/SoulAG.json` (Felder entfernen).
- **Risiko:** Niedrig wenn Entfernen, mittel wenn echte Fetcher (DB-Queries, Latenz).

### V9 [NIEDRIG] Sliders individualisieren
- **Was:** Mindestens `critical_thinking` für SoulAG auf 3 setzen ("Challenge assumptions actively. Propose fundamental changes.") — passt zur Halluzinations-Erkennungs-Pflicht.
- **Warum:** Aktuell tun Slider nichts, weil alle Agents identisch. Wenn der Wert je enforcement bekommt, soll SoulAG schon vorbereitet sein.
- **Datei:** `config/agents/SoulAG.json:4-10`.
- **Risiko:** Niedrig (kein Code der den Wert liest, nur Anzeige via API).

### V10 [NIEDRIG] Dynamic-Buttons-Archivierung automatisieren
- **Was:** Wenn SoulAG (oder ein anderer Agent) einen `<button action="..." label="...">` Tag inline in Showbox-Content setzt, automatisch in `showbox/buttons/dynamic/<agent>_<slug>.json` archivieren.
- **Warum:** Spec dynamic.md:26-34 sagt "Dynamic Buttons werden nie gelöscht". Aktuell kein Code-Pfad der dies tut.
- **Datei:** `src/gnom_hub/agents/actions/action_exec.py` (`handle_showbox`) + neuer Hook in `showbox_repo.py`.
- **Risiko:** Niedrig (nur persistieren).

---

## 8. Cross-Check-Notes für die Synthese

Diese Stichpunkte sollte der Cross-Synthesis-Verifier aufgreifen:

1. **Permission-Drift zwischen JSON und Python** ist NICHT nur ein SoulAG-Problem — es betrifft alle 8 Agents. SoulAG ist nur der krasseste Fall (`write` vs `evolve`/`crawl`). Andere Agents haben nur das Dead-Token `showbox_write` als Drift.
2. **`showbox_write` ist in 8/8 JSON-Configs** aber im Code nicht enforced. Entweder Implementierung oder Removal.
3. **Tier-Hierarchie ist zwischen allen 7 relevanten Identitäten konsistent** (SoulAG=2a, SecurityAG=2b, WatchdogAG=2c, GeneralAG=3a, Workers=3b). Die widersprüchlichen notes sind Versions-Artefakte.
4. **SoulAG-Identity hat 5 Pflichten, von denen Pflicht 4 (User-Wunsch-Completion-Tracking) und Pflicht 5 (Loops-Erkennung) nur teilweise oder gar nicht implementiert sind.** Pflicht 1 hat eine Spec-Lücke (Showbox-Output → soul_memory wird nicht gemacht).
5. **Agent-Farbe Diskrepanz**: Identity "CYAN" vs `agent_names.py:32` und `progress-protocol.md:36` Lila. Renderer-Realität ist Lila.
6. **`SoulAG.json` notes v8.0/v8.2 Self-Contradiction** (Tier 2b vs Tier 2a). Einfacher Fix.
7. **Verwaiste allowed_contexts Felder**: `soul_tasks`, `agent_reasoning`, `showbox_history`, `agent_messages` haben keinen Fetcher in `context.py`. SoulAG bekommt diese Inhalte nie in den Prompt.
8. **Sliders sind aktuell inert** (kein Code liest den numerischen Wert, nur den prompt_block-Text). Alle 8 Agents haben identische Slider → Symptom, kein Design.
9. **GeneralAG Identity widerspricht SoulAG Identity** über "AUSSCHLIESSLICH von SoulAG" vs "von dir ODER direkt vom User".
10. **WatchdogAG darf nicht direkt an SoulAG schreiben** (per eigener Identity), aber SoulAG darf WatchdogAG direkt anschreiben. Asymmetrie gewollt, nicht erzwungen.
11. **`agents/soulAG.py` ist 1 Zeile**: `if __name__ == "__main__": ... asyncio.run(...)` — nutzt `AGENT_DEFINITIONS["soulag"]["sys_prompt"]` der V3-"Sovereign"-Variante. SoulAG als BaseAgent-Instanz hat damit EINE komplett andere Identity als `config/agents/SoulAG.json` v8.3.
12. **SoulAG-LLM-Aufrufe** (soul.py:213, 248) nutzen Hardcoded System-Prompts ("SoulAG Task-Orchestrator v7.0" / "SoulAG Fakt-Extraktor") — die `config/agents/SoulAG.json` Identity wird HIER NICHT geladen. Der ganze v8.3-Rewrite ist also für die tatsächliche SoulAG-LLM-Interaktion möglicherweise unsichtbar.

---

**Ende des Audits. Keine Annahmen außer in Quellen belegt. Alle Pfad:Zeile-Referenzen verifiziert.**
