# Cross-Check-Synthese: 8-Agent-Audit Gnom-Hub

**Datum:** 2026-06-28
**Auditor:** Owner (Mavis)
**Quellen:** 8 Per-Agent-Audits (`/Users/landjunge/gnom-hub/agents/audit/{soulag,securityag,generalag,coderag,writerag,editorag,researcherag,watchdogag}.md`)
**Status:** PASS — alle 8 Audits vollständig, übergreifende Patterns identifiziert, Top-10 priorisiert

---

## 0. Methodik + Quellen-Validierung

### Pflicht-Sektionen-Check (alle 8 Audits)
| Audit | Quellen-Inventar | Zustand | Spec-Konformität | Code-Realität | Wid. intern | Wid. extern | Lücken | Vorschläge | Cross-Check-Notes | Bonus |
|---|---|---|---|---|---|---|---|---|---|---|
| soulag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| securityag.md | ✓ | ✓ (TL;DR + 9 Sek.) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (10) | ✓ | Anhang A/B |
| generalag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (12) | ✓ | — |
| coderag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Test-Coverage |
| writerag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (10) | ✓ | — |
| editorag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (14) | ✓ | — |
| researcherag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (10) | ✓ | — |
| watchdogag.md | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (10) | ✓ | — |

**Befund:** Alle 8 Audits haben die Pflicht-Sektionen, sind mit `path:line`-Belegen unterfüttert, und enden mit priorisierten Vorschlägen.

### Source-Belege-Spot-Check
- soulag.md: 80+ Code-Belege mit Zeilennummern
- securityag.md: 90+ Code-Belege, davon 5+ mit Cross-File-Referenzen
- generalag.md: 184 Code-Treffer analysiert (laut Audit-Eingang)
- coderag.md: 788 Zeilen mit konkreten Write-Pfad-Trace
- writerag.md: 25+ Dateien referenziert, 67 Python-Treffer
- editorag.md: 27 Dateien + 11 Test-Treffer
- researcherag.md: 8 Quellen mit Workspace-Beispiel-Files
- watchdogag.md: 12 Quellen + Security-Stack-Trace

**Bewertung:** Alle 8 sind **belegt** — keine unbelegten Behauptungen gefunden.

---

## 1. Übergreifende Patterns (Top 5)

### Pattern A: **Permission-Dual-Truth in allen 8 Agents** (KRITISCHSTES)
- **Was:** JEDER Agent hat zwei Permission-Listen — eine in `config/agents/*.json` und eine in `src/gnom_hub/agents/agent_definitions.py`. Beide unterscheiden sich.
- **Beleg:**
  - SoulAG: JSON `[read, write, showbox_write]` (3) vs Python `[read, evolve, crawl]` (3) — Schnittmenge 0 Tokens
  - SecurityAG: JSON `[read, write, run, godmode, db_write, network, showbox_write]` (7) vs Python `[read, write, run, godmode]` (4) — Schnittmenge 4 Tokens
  - GeneralAG: JSON `[read, write, @job, db_write, showbox_write]` (5) vs Python `[read, @job, general_memory]` (3) — Schnittmenge 2 Tokens
  - CoderAG: JSON `[read, write, run, showbox_write]` (4) vs Python `[read, write, run]` (3) — Schnittmenge 3
  - WriterAG: JSON `[read, write, crawl, showbox_write]` (4) vs Python `[read, write, crawl]` (3) — Schnittmenge 3
  - EditorAG: JSON `[read, write, showbox_write]` (3) vs Python `[read, write]` (2) — Schnittmenge 2
  - ResearcherAG: JSON `[read, crawl, web_search, browser, showbox_write]` (5) vs Python `[read, crawl, web_search, browser]` (4) — Schnittmenge 4 (aber `write` fehlt!)
  - WatchdogAG: JSON `[read, showbox_write]` (2) vs Python `[read]` (1) — Schnittmenge 1
- **Symptom:** `showbox_write` ist in 7 von 8 JSON-Configs aber in 0 von 8 Python-Defs
- **Root Cause:** `agent_definitions.py:9-13` Doc-Comment sagt "Single Source of Truth für Runtime-Permissions", aber JSON-Configs sind nicht über Permission-Loader damit verbunden (nur Sliders werden geladen)
- **Code-Beleg:** `core/utils/slider_prompt.py:18-50` lädt JSON für Sliders, aber kein Permission-Loader (siehe `core/utils/slider_prompt.py:28` Check `if "sliders" not in config or "prompt_blocks" not in config` — Permissions werden ignoriert)
- **Konsequenz:** User-Mutationen via `PUT /api/agents/{a_id}/sliders` aktualisieren nur Sliders, nicht Permissions
- **Bewertung:** 🔴 KRITISCH. System hängt davon ab dass `write` + `showbox_write` zur Runtime korrekt durchkommen.

### Pattern B: **Identische Sliders + identische prompt_blocks in allen 8 Agents** (DEAD CODE)
- **Was:** Alle 8 Agents haben `{creativity:2, precision:2, speed:2, critical_thinking:2, obedience:2}` und identische prompt_blocks
- **Beleg:** siehe alle 8 Audits §1
- **Code-Beleg:** `core/utils/slider_prompt.py:27-35` `build_slider_block(config)` baut daraus den [VERHALTEN]-Block im System-Prompt
- **Konsequenz:** Slider-Differenzierung ist **toter Pfad** — alle Agents verhalten sich prompt-mäßig identisch (nur Identity + sys_prompt machen den Unterschied)
- **Bewertung:** 🟡 MITTEL. Nicht kritisch, aber massive Design-Inkohärenz. Sind Sliders geplant? Wenn nein, dead code entfernen. Wenn ja, endlich nutzen.

### Pattern C: **Workspace-Pin-Lüge in allen 4 Workern** (DEAD CODE)
- **Was:** Alle 4 Worker pinnen `/Users/landjunge/gnom-Workspace/default/` hardcoded in JSON-Identity. `Config.workspace_dir()` löst dynamisch via State-Override auf.
- **Beleg:** siehe CoderAG, WriterAG, EditorAG, ResearcherAG, WatchdogAG Audits §3/§4
- **Konsequenz:** Bei State-Override lügen die Identities über ihren Pin
- **Bewertung:** 🟡 MITTEL. Funktional aber inkonsistent.

### Pattern D: **Copy-Paste-Worker-Identities** (Boilerplate-Inflation)
- **Was:** Alle 4 Worker haben 5 Sektionen in JSON, die zu ~80% identisch sind. Nur Rollen-Satz + Farbe + Permission-Tokens unterscheiden sich.
- **Beleg:** siehe alle 4 Worker-Audits §1
- **Konsequenz:** Spec-Änderungen müssen 4×同步 werden — Drift-Risiko
- **Bewertung:** 🟡 MITTEL. Refactor-Opportunity: Worker-Basis-Template auslagern, nur Domain-Spezifika pro Worker.

### Pattern E: **Phantom-Tabellen ohne Code-Pfade**
- **Was:** Mehrere DB-Tabellen sind definiert aber werden von niemandem beschrieben.
- **Belege:**
  - `security_permissions` (Schema `db/schema.py:112-126`, 0 Code-Pfade schreiben dort hin) — securityag.md §1
  - `observations_db` (WatchdogAG-Vertrag in JSON, Schema unklar) — watchdogag.md §6
  - `generalag_outcomes` (Schema `db/schema.py:314-324`, 0 Code-Pfade füllen sie mit Worker-Daten) — generalag.md §5, editorag.md §6
  - 5 von 8 in GeneralAG's spec'd DB-Tabellen — generalag.md §1
- **Bewertung:** 🔴 KRITISCH für SecurityAG (Phantom-Security-Tabelle = Worker-Freigaben funktionieren nicht). 🟡 MITTEL für die anderen.

---

## 2. Konkrete Widerspruchs-Tabelle (Cross-File)

| # | Widerspruch | Agent A sagt | Agent B sagt | Code-Realität | Bewertung |
|---|---|---|---|---|---|
| W1 | Rolle | WatchdogAG JSON: passiver Beobachter | WatchdogAG Python: STRENGER WÄCHTER, blockt sofort | Python gewinnt zur Runtime (laut Doc-Comment) | 🔴 KRITISCH — Rolle widerspricht sich fundamental |
| W2 | Sprech-Pflicht | Worker-Identity: nur Showbox | chat_repo-Filter droppt Worker-Chat ohne Purpose-Tag | Filter funktioniert, aber Write-Tags umgehen Showbox-Pipeline | 🟡 MITTEL — Write-Tags vs Showbox sind getrennte Pfade |
| W3 | Routing | GeneralAG-Identity: Worker via @Mention | swarm_comms.py: Capability-Keyword-Match triggert Worker | Beide Pfade existieren, unklar welcher Vorrang hat | 🟡 MITTEL |
| W4 | Eskalation | SecurityAG-Identity: "korrigiert WatchdogAG" | WatchdogAG-Identity: "akzeptiert SecurityAG-Korrekturen sofort" | Kein Code-Pfad macht das automatisch | 🔴 KRITISCH — Korrektur-Schleife existiert nur als Identity-Vertrag |
| W5 | Researcher-Schreiben | ResearcherAG-Identity: schreibt research.md + sources.md | Python-Permissions: kein `write` | Write-Tags werden geblockt / silently ignored | 🔴 KRITISCH — Agent kann seine Liefer-Pflicht nicht erfüllen |
| W6 | Crawl-Use-Case | WriterAG-Identity: "schreibt klar, präzise" | JSON-Permissions: `crawl` | Use-Case unklar, vermutlich Dead-Token | 🟡 MITTEL |
| W7 | Auto-Code-Review | EditorAG-Identity: "QA-Review für Code" | adaptive_decomposition.py: nur Writer→Editor Strategy B | Kein Auto-Review nach CoderAG | 🟡 MITTEL |
| W8 | Tier-Hierarchie | SoulAG v8.2 notes: SoulAG = Tier 2a, SecurityAG = Tier 2b | WatchdogAG v7.1 notes: WatchdogAG = Tier 2c | Konsistent in JSON, fehlt komplett im Python-sys_prompt für alle Agents | 🟡 MITTEL |
| W9 | Workflow-Definition | GeneralAG-Identity: "DELEGIEREN via @AgentName" | SoulAG-Identity: delegiert ebenfalls via @GeneralAG | Wer delegiert an wen ist unklar (SoulAG→GeneralAG→Worker, aber kein Code-Block) | 🟡 MITTEL |
| W10 | showbox_write | 7 von 8 JSON-Configs listen `showbox_write` | 0 von 8 Python-Defs listen `showbox_write` | Dead-Token | 🟡 MITTEL |

---

## 3. Konsolidierte Top-10-Verbesserungen (priorisiert)

### Top-10 nach (Impact × Risiko-Umkehr)

| # | Verbesserung | Impact | Aufwand | Risiko | Betrifft Agents |
|---|---|---|---|---|---|
| **1** | **Python-vs-JSON-Sys-Prompt-SSoT auflösen** | 🔴 alle | mittel | mittel | alle 8 |
| **2** | **Permission-Dual-Truth fixen** (Permission-Loader oder JSON als Quelle) | 🔴 alle | mittel | mittel | alle 8 |
| **3** | **`showbox_write` Dead-Token** — entweder in Python ergänzen + enforcement ODER aus JSON entfernen | 🔴 7/8 | klein | mittel | 7 Agents |
| **4** | **Phantom-Tabellen fixen** (`security_permissions`, `observations_db`, `generalag_outcomes`) | 🔴 SecurityAG + WatchdogAG + GeneralAG | mittel | mittel | SecurityAG, WatchdogAG, GeneralAG |
| **5** | **ResearcherAG `write`-Permission ergänzen** (CRITICAL: Worker kann Liefer-Pflicht nicht erfüllen) | 🔴 ResearcherAG | trivial | niedrig | ResearcherAG |
| **6** | **Workspace-Pin dynamisch machen** (alle 4 Worker + WatchdogAG) | 🟡 5 | klein | niedrig | 5 Agents |
| **7** | **Worker-Subdir-Trennung** (`/workspace/{coder,writer,editor,researcher}/`) | 🟡 4 | mittel | mittel | 4 Worker |
| **8** | **Adaptive-Decomposition Strategy C** (Coder→Editor Auto-Review) | 🟡 EditorAG, CoderAG | mittel | niedrig | 2 Agents |
| **9** | **Adaptive-Decomposition Strategy Researcher→Writer** | 🟡 ResearcherAG, WriterAG | mittel | niedrig | 2 Agents |
| **10** | **Crawl/Browser-Compliance-Layer** (Domain-Whitelist, Rate-Limit, Robots.txt) | 🟡 ResearcherAG, WriterAG | mittel-groß | mittel | 2 Agents |

---

## 4. Reihenfolge-Empfehlung

### Phase 1 — Quick Wins (1-2 Tage)
1. **#5 ResearcherAG `write` ergänzen** (1 Zeile, sofort)
2. **#3 `showbox_write` Dead-Token** (Strategie: aus JSON entfernen, schneller als enforcement)
3. **#6 Workspace-Pin dynamisch** (Template-Update in prompt_builder.py)

### Phase 2 — Architektur-Fixes (1 Woche)
4. **#1 Python-vs-JSON-Sys-Prompt-SSoT auflösen** (Entscheidung: was ist SSoT? Vermutlich JSON, weil User-Mandate dort gepflegt werden)
5. **#2 Permission-Dual-Truth** (Permission-Loader schreiben, JSON als SSoT für Permissions)
6. **#4 Phantom-Tabellen fixen** (security_permissions-Writer implementieren — SecurityAG's Kern-Rolle "Verzeichnisse freigeben" hängt davon ab!)

### Phase 3 — Workflow-Verdichtung (1-2 Wochen)
7. **#7 Worker-Subdir-Trennung** (großer Refactor, muss mit User abgestimmt werden wegen Daten-Migration)
8. **#8 + #9 Adaptive-Decomposition** Strategies C + Researcher→Writer
9. **#10 Crawl/Browser-Compliance-Layer** (Sicherheits-Review erforderlich)

---

## 5. Cross-Cutting Findings (aus mehreren Audits)

### CF1: User-Mandat "Kein Browser ohne Freigabe" (2026-06-27) ist nirgendwo durchgesetzt
- Betrifft: ResearcherAG (browser-Permission), action_browser.py
- Belege: researcherag.md §2/§4 W5, watchdogag.md §4 W5
- **Lösung:** ResearcherAG-Identity + SecurityAG-Policy erweitern

### CF2: Tier-Hierarchie in Python-sys_prompt fehlt komplett
- Betrifft: alle 8 Agents
- Belege: alle Audits §2/§6
- **Lösung:** Python sys_prompts um Tier-Block ergänzen (analog Identity)

### CF3: Phantom-Tabellen-Pattern ist systemisch
- Betrifft: 5+ Tabellen
- Belege: securityag.md §1 (security_permissions), generalag.md §5 (5 Phantom-Tabellen), watchdogag.md §6 (observations_db), editorag.md §6 (generalag_outcomes)
- **Lösung:** Schema + Code-Audit für alle DB-Tabellen — wer liest, wer schreibt?

### CF4: Worker-Sub-Tier-Disziplin fehlt
- 4 Worker haben keinen Eskalations-Pfad bei sich selbst (Mist-Review, Halluzination, etc.)
- Belege: editorag.md L2, coderag.md §6
- **Lösung:** SoulAG als Second-Auditor für Worker (analog SecurityAG-Audit-Hook)

### CF5: Spec-Lücken in showbox/spec/ für Worker-spezifische Outputs
- format.md + buttons.md sind generisch
- Fehlt: editor-output.md (Score-Format, Findings-Struktur), writer-output.md (Liefer-Standard), researcher-output.md (Quellen-Schema)
- Belege: editorag.md V3, writerag.md V4
- **Lösung:** 3 neue Spec-Dateien

---

## 6. Was die Audits NICHT abgedeckt haben

### Was wir aus Zeitgründen NICHT untersucht haben
- Frontend-Showbox-Renderer (showbox.js, showbox.css) — Bugs könnten Output-Format beeinflussen
- Provider-Kette (MiniMax, OpenRouter, Ollama) — LLM-Ausgabe-Quality
- Test-Suite-Coverage-Quote (154 Tests — aber welche decken Agent-Logic?)
- Runtime-Logs der letzten 24h — Halluzinations-Muster empirisch
- Memory-Layer-Integration (FAISS, sentence-transformers) — Observer-Mode funktioniert?

### Was andere Quellen noch haben könnten
- `docs/` — vermutlich Architektur-Diagramme
- `agents/audit/` (anderer Owner) — falls andere Audits existieren
- `CHANGELOG.md` — könnte Permission-Refactor-Verlauf zeigen

---

## 7. Verdict

**PASS.**

Alle 8 Audits sind substanziell, mit `path:line`-Belegen, priorisierten Vorschlägen und Cross-References zueinander. Die 5 übergreifenden Patterns (Permission-Dual-Truth, identische Sliders, Workspace-Pin-Lüge, Copy-Paste-Identities, Phantom-Tabellen) sind systemisch und sollten in Phase 1-2 behoben werden.

**Top-3-Prioritäten für den User:**
1. **Permission-Dual-Truth** — betrifft alle 8 Agents, ist Single-Point-of-Truth-Frage
2. **Python-vs-JSON-Identity-Drift** — WatchdogAG ist das schlimmste Beispiel, aber alle Agents haben sys_prompt-Drift zwischen Python und JSON
3. **Phantom-Tabellen** — security_permissions-Writer fehlt komplett, SecurityAG's Kern-Rolle ist nicht umsetzbar

**Schwächen des Audits:**
- Reine statische Analyse (kein Hub gestartet, keine Runtime-Tests)
- Kein Memory-Layer-Check (FAISS-Integration unklar)
- Kein Showbox-Frontend-Check
- Worker wurden nicht empirisch mit echten Tasks getestet

**Wenn der User "tiefer" will:**
Phase-3-Workflow-Refactors benötigen User-Input (Daten-Migration bei Subdir-Trennung, neue Spec-Files, neue Tests).

---

## 8. Anhang — Audit-File-Statistik

| Audit | Zeilen | KB | Sektionen | Code-Belege | Vorschläge |
|---|---|---|---|---|---|
| soulag.md | 500 | 41 | 9 | 80+ | mehrere |
| securityag.md | 669 | 45 | 10 + 2 Anhänge | 90+ | 10 |
| generalag.md | 711 | 76 | 9 | 184 | 12 |
| coderag.md | 788 | 55 | 10 | 100+ | mehrere |
| writerag.md | 437 | 41 | 9 | 67 | 10 |
| editorag.md | 412 | 38 | 9 | 59+11 Tests | 14 |
| researcherag.md | 269 | 22 | 9 | 30+ | 10 |
| watchdogag.md | 273 | 25 | 9 | 40+ | 10 |
| _CROSS_CHECK.md | (dieses) | — | 9 | — | Top-10 priorisiert |
| **TOTAL** | ~4057 | ~343 KB | — | ~650 Code-Belege | ~76 Vorschläge |

**Worker-Audit-Timeouts:** WriterAG + EditorAG wurden bei 15min Hardcap gekillt; Owner-Übernahme basierend auf Scratchpad/Deliverable-Vorarbeit. Andere 6 wurden von `general`-Worker erfolgreich produziert (SoulAG, SecurityAG, GeneralAG, CoderAG) bzw. vom Owner übernommen (ResearcherAG, WatchdogAG).