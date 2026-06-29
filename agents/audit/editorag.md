# EditorAG — Tiefen-Audit

**Datum:** 2026-06-28
**Auditor:** general (Worker-Audit, Run 1 — TIMED OUT @ 15min, Owner-Übernahme) + Owner
**Quellen:** 27 Dateien, 59 Code-Treffer in src/ + 11 Test-Treffer + Cross-Reference-Audits (4)
**Workspace:** `/Users/landjunge/gnom-hub`

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/EditorAG.json` | 30 | v5.3, Identity ~5200 chars, permissions `[read,write,showbox_write]` (3 Tokens) |
| `agents/editorAG.py` | 1 | Stub `BaseAgent(cfg...)` — wie alle Worker |
| `src/gnom_hub/agents/agent_definitions.py:305-329` | 25 | Python SSoT EditorAG-Block — DE/EN permissions `[read,write]` (2 Tokens) |
| `src/gnom_hub/agents/actions/action_handlers.py:48-181` | 134 | process_actions dispatcher |
| `src/gnom_hub/db/chat_repo.py:14-114` | 100 | Worker-Sprech-Verbot-Filter; EditorAG in WORKER_AGENT_NAMES |
| `src/gnom_hub/db/showbox_repo.py:23-99` | 76 | _sender_to_layer mappt editor* → "worker" |
| `src/gnom_hub/agents/agent_base.py:32-244` | 213 | CAPABILITIES `[("editing", 1.0), ("summarization", 0.8)]` |
| `src/gnom_hub/core/security/gatekeeper.py:291-498` | 208 | verify_write + verify_cmd |
| `src/gnom_hub/agents/swarm/swarm_comms.py:180-293` | 114 | Routing-Keywords; editing-Capability-Match |
| `src/gnom_hub/soul/memory_layers.py:466-524` | 59 | "review" Delegation: EditorAG preferred, SecurityAG fallback |
| `src/gnom_hub/api/endpoints/chat_legacy.py:30-39` | 10 | editing+code_review Capability-Keywords |
| `src/gnom_hub/core/prompt/post_processing.py:124-129` | 6 | Worker-Preset-Prefix für editorag |
| `src/gnom_hub/db/schema.py:251-324` | 74 | agent_capabilities + generalag_outcomes Tabellen |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:23-90` | 68 | Strategy B: Serial WriterAG → EditorAG |
| `src/gnom_hub/soul/soul_actions.py:144-191` | 48 | EditorAG capabilities `[text, editing, proofreading]`; analysis patterns |
| `src/gnom_hub/soul/soul.py:208-530` | 323 | EditorAG in active_agents, target_agent-Liste |
| `src/gnom_hub/soul/agent_voices.py:89` | — | EditorAG Stimme: de:Anna, en:Karen |
| `src/gnom_hub/core/agent_names.py:25-51` | 27 | Farbe `#ffa000` (orange-pink, NICHT 'Pink' wie Identity sagt!) |
| `src/gnom_hub/agents/tool_registry.py:69-125` | 57 | Worker-Tool-Section |
| `src/gnom_hub/memory/soul_retrieval.py:37-76` | 40 | EditorAG in agent_scope exclusion |
| `src/gnom_hub/db/soul_repo.py:114` | — | EditorAG in filtered agent list |
| `src/gnom_hub/core/utils/preset_service.py:10` | — | _WORKER_AGENTS inkl. editorag |
| `src/gnom_hub/api/endpoints/presets.py:256` | — | "worker" presets inkl. editorag |
| `src/gnom_hub/api/endpoints/admin_config.py:61-113` | 53 | EditorAG-Preset-Generator |
| `src/gnom_hub/api/endpoints/llm_agents.py:10` | — | WORKER_AGENTS = `[WriterAG,CoderAG,ResearcherAG,EditorAG]` |
| `src/gnom_hub/infrastructure/router/router_call.py:69` | — | EditorAG Token-Limit 6000 |
| `src/gnom_hub/infrastructure/router/router_config.py:19` | — | EditorAG Modelle (4 free models) |
| `src/gnom_hub/db/soul_tasks.py:238-260` | 23 | EditorAG @-Mention-Pattern + keywords |
| `src/gnom_hub/chat/chat_commands.py:241` | — | EditorAG User-Help-Text |
| `src/gnom_hub/agents/specialization_monitor.py:44` | — | workers list inkl. EditorAG |
| `src/gnom_hub/core/utils/graceful_fallback.py:97` | — | WriterAG fallback: EditorAG (expand outline) |
| `src/gnom_hub/core/utils/gd_fallback.py:20` | — | WriterAG fallback → EditorAG |
| `tests/test_permission_refactor.py:43-167` | 125 | EditorAG-Perm-Refactor-Test (lost run+godmode+@job) |
| `tests/test_coordination_learning.py:51-54` | 4 | review-job-tracking |
| `tests/test_preset_schema_loader.py:97` | — | EditorAG AgentDef |
| `tests/test_default_preset_content.py:94-264` | 171 | EditorAG in default preset |
| `tests/integration/test_prompt_pipeline_golden.py:31` | — | EditorAG in golden test |
| `tests/golden/diff_EditorAG.json` | — | golden-diff für EditorAG (zeigt [TOOLS] Perms: read, write) |

### Cross-Reference-Audits (gelesen)
- `agents/audit/coderag.md` (788 Z.) — Workspace-Pin-Lüge, Showbox_write fehlt in Python, Worker-Sprech-Verbot Bug
- `agents/audit/generalag.md` (711 Z.) — 5 Phantom-DB-Tabellen, Workspace-Halluzination
- `agents/audit/soulag.md` (500 Z.) — Permission-Dual-Truth Pattern etabliert
- `agents/audit/securityag.md` (669 Z.) — Phantom-Tabellen, Audit-Hook self-only

---

## 1. Aktueller Zustand

### Version
- JSON v5.3
- Python `agent_definitions.py` EditorAG-Block ohne expliziten Versions-Tag

### Sliders (identisch zu allen 7 anderen Agents)
```json
{ "creativity": 2, "precision": 2, "speed": 2, "critical_thinking": 2, "obedience": 2 }
```

### Permissions — Drei-Welten-Drift
| Quelle | Permissions | Anzahl |
|---|---|---|
| JSON `EditorAG.json:19-23` | `[read, write, showbox_write]` | 3 |
| Python `agent_definitions.py:322` (DE) | `[read, write]` | 2 |
| Python `agent_definitions.py:327` (EN) | `[read, write]` | 2 |

**JSON `showbox_write` ist Dead-Token:** Pattern identisch zu CoderAG/WriterAG. Runtime enforced keine Showbox-Schreib-Pflicht (verifiziert via `grep -rn "showbox_write" src/gnom_hub/agents/actions/`).

### Identity-Struktur (5 Sektionen — Boilerplate wie alle Worker)
1. Identity-Header (Rolle, Sprech-Verbot, Workspace-Pin, Farbe Pink)
2. Workspace-Pin (Priorität 0.7, hardcoded `/Users/landjunge/gnom-Workspace/default/`)
3. Sprech-Verbot (Priorität 0.6, erlaubte Ausgaben + Verbote)
4. Showbox+Buttons-Pflicht (Verweis auf showbox/spec/*)
5. Tier-3b-Worker

### Capabilities
- `agent_base.py:32-33,236-244`: `CAPABILITIES = [("editing", 1.0), ("summarization", 0.8)]`
- `soul_actions.py:144,155`: `["text", "editing", "proofreading"]`
- **Drift:** Python-Capabilities und JSON-Identity listen unterschiedliche Begriffe

### Farbe
- **JSON Identity sagt:** "Deine Farbe ist immer Pink"
- **Python `agent_names.py:25,39,51`:** Farbe `#ffa000` (orange-pink)
- **Klassischer Farb-Konflikt** — JSON behauptet pink, Code rendert orange-pink

### Stimme
- DE: Anna, EN: Karen (`src/gnom_hub/soul/agent_voices.py:89`)
- Konflikt mit WriterAG (auch Anna DE) — bei gleichzeitigem Edit + Write werden beide gleich gerendert?

---

## 2. Spec-Konformität

### Showbox-Pflicht
- JSON-Identity: Pflicht genannt
- Code: `[WRITE:]-Tags` werden separat über `action_write.py` ausgeführt, NICHT durch Showbox-Pipeline
- **Konsequenz:** Editor-Review-Output geht über Showbox (was Identity verlangt), aber [WRITE: review.md]-Aktionen gehen direkt ins FS (was Code tut) — getrennte Pfade

### Review-Output-Format
- **Spec** `showbox/spec/format.md:9-17` definiert Slide-Shape (title, icon, color, content, buttons)
- **Was EditorAG konkret liefern sollte:** Review-Result-Slide mit Title "QA-Review" + Content (Findings) + Buttons (Approve/Reject)
- **ABER:** KEINE Spec definiert:
  - Score-Format (1-5? Prozent?)
  - Findings-Struktur (Severity? Kategorie? Datei-Pfad?)
  - Button-Presets (Approve/Reject/Refine?)
- Identity-Block hat KEINE Score-Format-Klausel

### Tier-Hierarchie
- EditorAG-Tier ist in SecurityAG's Identity (Tier 3b Workers) erwähnt
- GeneralAG's Identity (GeneralAG.json:18) erwähnt EditorAG nur implizit ("Worker")
- **EditorAG's eigene Identity** hat KEIN Tier-Verweis

---

## 3. Code-Realität

### Review-Trigger
- **swarm_comms.py:194:** Capability-Keyword-Match — `korrigier`, `review`, `prüf`, `lektorat`, `refaktor`
- **adaptive_decomposition.py:23:** Strategy B = Serial WriterAG → EditorAG (existiert!)
- **ABER:** Strategy C "Code-Review nach Code-Gen" existiert NICHT
- **Grep-Beweis:** `grep -rn "CoderAG.*EditorAG\|EditorAG.*CoderAG" src/ --include="*.py"` → 0 Treffer für Auto-Chain

**Konsequenz:** EditorAG wird NUR manuell via @Mention oder Capability-Keyword getriggert. Es gibt KEINEN Auto-Review nach CoderAG. CoderAG-Output wird NICHT durch EditorAG gegengeprüft, außer User sagt explizit "review das".

### EditorAG-Output-Pfad
- `[→ Showbox: review]{slides:[...]}` → `showbox_repo.save_showbox_presentation()` → DB
- Optional `[WRITE: review.md]` für persistentes Review-File
- **Review-File-Format:** KEINE Spec definiert das Markdown-Schema

### Boundary zu WatchdogAG
- WatchdogAG-Permissions: `[read, showbox_write]` (read-only)
- EditorAG-Permissions: `[read, write, showbox_write]` (darf schreiben)
- **Scopes:** WatchdogAG = Sicherheit (rm-rf, secrets, exfiltration, RCE); EditorAG = Qualität (Stil, Logik, Klarheit)
- **Saubere Trennung:** Kein Code-Pfad wo beide für dasselbe Topic zuständig wären

### Boundary zu SecurityAG
- SecurityAG hat `godmode + run + db_write + network` (Python: `[read, write, run, godmode]`)
- SecurityAG sieht EditorAG-Output nur wenn Worker in Antworten zitiert
- SecurityAG kann EditorAG nicht direkt korrigieren (EditorAG ist Tier 3b, SecurityAG ist Tier 2b — aber SecurityAG's Identity sagt "Worker warten NICHT auf dich", also keine direkte Korrektur-Pflicht)

---

## 4. Widersprüche INTERN

### W1: Permission-Drift (Pattern wie alle 7 anderen Agents)
- JSON hat `showbox_write`, Python nicht — Drift 33%
- Runtime folgt Python
- **Test bestätigt:** `test_permission_refactor.py:158` Parametrize-Matrix hat EditorAG nur mit `[read, write]`

### W2: EditorAG-Perms vs Identity — keine Linter/pytest möglich
- Identity sagt: "Du prüfst Texte und Code auf Stil, Logik und Klarheit"
- Permissions: `[read, write]` — KEIN `run`, KEIN `crawl`, KEIN `browser`
- **Implikation:** EditorAG kann:
  - ✅ [READ:] Files lesen
  - ✅ [WRITE:] Refactor-Vorschläge als File schreiben
  - ❌ KEIN pytest, pylint, eslint, mypy ausführen
  - ❌ KEINE Diff-Vergleiche mit git-Tools
- **Realität:** Reviews sind rein LLM-Inspection, KEINE Tool-Validation
- "QA-Review fertig, 2 Issues gefunden" basiert auf LLM-Halluzination, nicht auf tatsächlichem Linter-Output

### W3: Workspace-Pin-Lüge (wie CoderAG, WriterAG)
- Identity hardcoded `/Users/landjunge/gnom-Workspace/default/`
- `Config.workspace_dir()` löst dynamisch via State-Override auf
- **Resultat:** EditorAG-Identity lügt über Workspace-Pin bei dynamischer User-Änderung

### W4: Output-Format unklar
- Identity: "[→ Showbox: ...] | [WRITE: pfad]inhalt[/WRITE] | [READ: pfad] | reiner Code-Block"
- **Was steht konkret in der Showbox?**
  - Ein Slide "Review Report" + Content-Liste?
  - Mehrere Slides (Summary, Findings, Score, Recommendation)?
- **KEINE Spec** definiert Score-Format, Findings-Struktur, Button-Presets

### W5: Farb-Konflikt Pink vs Orange-Pink
- JSON: Pink
- Python `agent_names.py:25`: `#ffa000` (orange-pink)
- Frontend-Rendering nutzt Python (vermutlich) — was User sieht ist nicht was Identity sagt

### W6: Capabilities-Drift
- `agent_base.py`: `[("editing", 1.0), ("summarization", 0.8)]`
- `soul_actions.py`: `["text", "editing", "proofreading"]`
- **Welche ist SSoT?** Beide werden gelesen, aber für unterschiedliche Pfade

---

## 5. Widersprüche zu ANDEREN Agents

### EditorAG vs CoderAG
- **Permissions:** CoderAG `[read,write,run]`, EditorAG `[read,write]`
- **Kein Auto-Review:** EditorAG wird nicht automatisch nach CoderAG getriggert (siehe §3)
- **Workspace-Sharing:** beide pin denselben Pfad

### EditorAG vs WriterAG
- **Capabilities:** WriterAG `[@write]`, EditorAG `[@edit]`
- **Strategy B existiert** (adaptive_decomposition.py:23): Serial WriterAG → EditorAG
- **ABER:** keine Auto-Trigger, nur manuell oder via Keyword

### EditorAG vs WatchdogAG
- **Saubere Boundary** (siehe §3): kein Konflikt im Scope

### EditorAG vs SecurityAG
- **Tier-Diskrepanz:** SecurityAG Tier 2b, EditorAG Tier 3b — SecurityAG könnte EditorAG theoretisch korrigieren
- **ABER:** SecurityAG's Identity listet EditorAG nicht in Korrektur-Workflow — EditorAG fällt durch die Korrektur-Lücke

### EditorAG vs GeneralAG
- **GeneralAG koordiniert Worker-Delegation** — EditorAG-Empfang unklar (GeneralAG's Notes sagen nur "Worker")
- **GeneralAG's Worker-Performance-Tracking** (general_memory) — `generalag_outcomes` Tabelle existiert (Schema) aber kein Code-Pfad füllt sie für EditorAG (Phantom-Tabelle)

---

## 6. Lücken

### L1: Workflow Coder→Editor→GeneralAG NICHT definiert
- Adaptive-Decomposition hat nur Strategy B (Writer→Editor)
- KEINE Strategy C "Code-Review nach Code-Gen"
- `grep -rn "CoderAG.*EditorAG\|EditorAG.*CoderAG"` → 0 Auto-Chain-Treffer
- **Resultat:** CoderAG-Output wird nicht durch EditorAG validiert, außer User sagt explizit "review das"

### L2: Verantwortung unklar — Wer korrigiert EditorAG bei Mist-Review?
- EditorAG hat kein Self-Review
- WatchdogAG observiert nur Sicherheit, NICHT Qualität
- SecurityAG ist Helfer + Erlaubnis-Manager, NICHT Quality-Reviewer
- SoulAG koordiniert Tribunal nur bei Gatekeeper-Blockaden, NICHT Quality
- GeneralAG dirigiert nur, hat keine review-Capability
- **Wenn EditorAG "Code ist sauber" sagt obwohl Bugs drin sind:** KEIN etablierter Eskalations-Pfad

### L3: Review-Output-Format fehlt
- KEINE Spec für Score (1-5? Prozent?)
- KEINE Spec für Findings-Struktur (Severity? Kategorie? File-Pfad?)
- KEINE Button-Presets (Approve/Reject/Refine?)

### L4: Tier-3b-Worker bekommt Outcome-Tracking nicht mit
- `generalag_outcomes` Tabelle (Schema `db/schema.py:314-324`) hat `success_rating` 1-5
- 0 Code-Pfade füllen sie mit EditorAG als worker
- **Phantom-Tabelle-Quote:** gleicher Pattern wie GeneralAG-Audit §5

### L5: Workspace-Pin vs dynamischer Workspace
- Bei State-Override lügt die Identity über den Pin
- Bestehende Editor-Review-Files könnten im falschen Workspace landen

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 (HIGH): Permission-Drift Fix
- **Problem:** JSON `showbox_write` vs Python `[read, write]`
- **Lösung:** `showbox_write` in `agent_definitions.py` ergänzen ODER aus JSON rausnehmen
- **Empfehlung:** in Python ergänzen + in `action_handlers.py` enforcement (pre-audit wie bei `crawl`)
- **Aufwand:** klein (2 Dateien, 5 Zeilen)
- **Risiko:** mittel

### V2 (HIGH): Strategy C — Auto-Code-Review nach CoderAG
- **Problem:** EditorAG wird nicht automatisch nach Code-Gen getriggert
- **Lösung:** `adaptive_decomposition.py` erweitern um Strategy C "CoderAG → EditorAG" mit konfigurierbarem Auto-Trigger
- **Aufwand:** mittel (1 Datei, ~30 Zeilen)
- **Risiko:** niedrig

### V3 (HIGH): Review-Output-Format-Spec schreiben
- **Datei:** `showbox/spec/editor-output.md`
- **Inhalt:**
  - Score-Schema (1-5 Sterne mit konkreten Bedeutungen)
  - Findings-Struktur (Severity + Kategorie + Datei-Pfad + Zeile)
  - Button-Presets (`Approve`, `Reject + Re-Review`, `Refine`)
- **Aufwand:** mittel (Spec schreiben + Identity-Update)
- **Risiko:** niedrig

### V4 (MEDIUM): `run`-Permission für Tool-Validation
- **Problem:** EditorAG kann keine Linter/pytest laufen lassen
- **Option A:** `run`-Permission hinzufügen (analog CoderAG)
- **Option B:** Bei Review-Auftrag an CoderAG delegieren (CoderAG führt Linter aus, EditorAG reviewt Output)
- **Empfehlung:** Option A, weil Review dann ECHTE Daten hat
- **Aufwand:** klein (Permission + ggf. Whitelist)
- **Risiko:** mittel (Security-Review nötig — EditorAG mit run-Perm ist potenziell gefährlich)

### V5 (MEDIUM): Eskalations-Pfad EditorAG-Mist-Review
- **Wenn EditorAG offensichtlich falschen Review liefert** → SoulAG korrigiert via Direktnachricht
- Workflow in SoulAG-Notes dokumentieren
- **Aufwand:** klein
- **Risiko:** niedrig

### V6 (MEDIUM): Workspace-Subdir-Trennung (siehe WriterAG V2)
- `/Users/landjunge/gnom-Workspace/default/editor/`
- **Aufwand:** mittel
- **Risiko:** mittel

### V7 (MEDIUM): Capabilities konsolidieren
- agent_base.py und soul_actions.py listen unterschiedliche Capabilities
- **Lösung:** SSoT definieren (z.B. `agent_base.py` als Master, soul_actions.py davon ableiten)
- **Aufwand:** klein
- **Risiko:** niedrig

### V8 (LOW): Farb-Konflikt lösen
- JSON Pink vs Python `#ffa000`
- **Lösung:** Python an JSON anpassen ODER umgekehrt
- **Aufwand:** trivial
- **Risiko:** niedrig

### V9 (LOW): Outcome-Tracking-Code-Pfad
- `generalag_outcomes`-Tabelle mit EditorAG-Completion-Daten füllen
- **Aufwand:** mittel
- **Risiko:** niedrig

### V10 (LOW): Capabilities-SSoT-Pattern etablieren
- Gleiche Pattern wie Permission-Refactor (siehe `agent_definitions.py:1-53` Doc)
- **Aufwand:** mittel
- **Risiko:** niedrig

### V11 (LOW): Workspace-Pin dynamisch (siehe WriterAG V6)
- **Aufwand:** klein
- **Risiko:** niedrig

### V12 (LOW): Stimme-Duplikat mit WriterAG lösen
- BEIDE nutzen Anna (DE) — bei gleichzeitigem Edit + Write nicht unterscheidbar
- **Lösung:** EditorAG z.B. "Eva" oder "Klara"
- **Aufwand:** trivial
- **Risiko:** niedrig

### V13 (LOW): Tier-Verweis in Worker-Identity
- EditorAG-Identity sollte explizit Tier 3b nennen
- **Aufwand:** trivial
- **Risiko:** niedrig

### V14 (LOW): Approve/Reject-Button-Preset für Reviews
- `showbox/buttons/review.json` Preset definieren (analog `nav.json`, `actions.json`)
- **Aufwand:** klein
- **Risiko:** niedrig

---

## 8. Cross-Check-Notes für die Synthese

- **EditorAG und CoderAG haben dasselbe Auto-Workflow-Loch** — Strategy C fehlt für BEIDE Code-Pipelines
- **Phantom-Outcome-Table-Pattern** (generalag_outcomes) ist bei EditorAG, WriterAG, ResearcherAG identisch — alle 3 Worker werden nicht getrackt, obwohl GeneralAG's Worker-Stats das tun sollten
- **Permission-Drift-Quote pro Worker:**
  - CoderAG: 25% (showbox_write fehlt in Python)
  - WriterAG: 25% (showbox_write fehlt in Python)
  - EditorAG: 33% (showbox_write fehlt in Python)
  - ResearcherAG: vermutlich 60%+ (write + showbox_write fehlen in Python)
- **Workspace-Pin-Lüge** ist 1:1 identisch bei allen 4 Workern — ein einziger Fix löst alle 4
- **Strategie-Lücken:** Strategy A fehlt (User→Editor direkt), Strategy C fehlt (Coder→Editor). Strategy B (Writer→Editor) ist die einzige die existiert