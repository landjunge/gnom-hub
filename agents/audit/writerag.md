# WriterAG — Tiefen-Audit

**Datum:** 2026-06-28
**Auditor:** general (Worker-Audit, Run 1 — TIMED OUT @ 15min, Owner-Übernahme) + Owner
**Quellen:** 25+ Dateien, 67 Python-Treffer + 37 Test-Treffer + Live-Workspace-Check
**Workspace:** `/Users/landjunge/gnom-hub`

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/WriterAG.json` | 31 | v5.3, Identity ~6000 chars, permissions `[read,write,crawl,showbox_write]` |
| `agents/writerAG.py` | 1 | Stub `BaseAgent(cfg...)` — gleiche Form wie alle anderen |
| `src/gnom_hub/agents/agent_definitions.py:255-278` | 24 | Python SSoT WriterAG-Block — DE/EN permissions `[read,write,crawl]` (3 Tokens) |
| `src/gnom_hub/agents/actions/action_handlers.py:48-181` | 134 | process_actions dispatcher |
| `src/gnom_hub/agents/actions/action_exec.py:11-46` | 36 | handle_crawl + handle_shell + handle_showbox |
| `src/gnom_hub/db/chat_repo.py:14-114` | 100 | Worker-Sprech-Verbot filter (chat_repo.add_chat_message) |
| `src/gnom_hub/agents/swarm/swarm_comms.py:66-291` | 226 | parse_agent_sequence + keyword routing |
| `src/gnom_hub/agents/specialization_monitor.py:6-49` | 44 | WriterAG drift hardcoded |
| `src/gnom_hub/agents/team_velocity.py:17-21` | 5 | WriterAG underutilization check |
| `src/gnom_hub/soul/memory_layers.py:450-470` | 21 | delegation_rules defaults |
| `src/gnom_hub/soul/soul_actions.py:136-191` | 56 | AGENT_CAPS |
| `src/gnom_hub/soul/agent_voices.py:81-90` | 10 | WriterAG = Anna/Samantha |
| `src/gnom_hub/infrastructure/router/router_config.py:18` | — | minimax default |
| `src/gnom_hub/infrastructure/router/router_call.py:69` | — | Token-Limit 6000 |
| `src/gnom_hub/agents/actions/adaptive_decomposition.py:22-90` | 69 | WriterAG $0.03/s |
| `src/gnom_hub/core/utils/graceful_fallback.py:96-97` | 2 | WriterAG fallback chain |
| `src/gnom_hub/core/utils/gd_fallback.py:19-37` | 19 | WriterAG fallback chain |
| `src/gnom_hub/core/prompt/post_processing.py:124-130` | 7 | Worker preset injection |
| `src/gnom_hub/memory/embeddings.py:55-90` | 36 | Worker scope filter |
| `src/gnom_hub/db/soul_tasks.py:230-260` | 31 | intent patterns |
| `src/gnom_hub/db/showbox_repo.py:30-37` | 8 | writer→worker layer |
| `src/gnom_hub/api/endpoints/llm_agents.py:9-11` | 3 | WORKER_AGENTS list |
| `src/gnom_hub/api/endpoints/presets.py:247-256` | 10 | preset groups |
| `src/gnom_hub/chat/chat_commands.py:230-245` | 16 | Worker-Layer Doku |
| `src/gnom_hub/agents/tool_registry.py:11-71` | 61 | crawl_url + always-on |
| `src/gnom_hub/agents/agent_names.py:4-41` | 38 | WriterAG name normalize |
| `src/gnom_hub/api/endpoints/admin_config.py:55-113` | 59 | preset generator |
| **Live-Workspace** `gnom-Workspace/default/.agents/writerag/soul.json` | 11 | Permissions `[read,write,crawl]` — MATCHT Python, NICHT JSON |

---

## 1. Aktueller Zustand

### Version
- JSON v5.3, letzte Änderung 2026-06-28 (siehe notes)
- Python `agent_definitions.py` hat keinen expliziten Versions-Tag (nur Refactor-Stand 2026-06-21 in Doc-Comment)
- Live-Workspace `soul.json`: folgt Python, keine `showbox_write`

### Sliders (identisch zu allen 7 anderen Agents)
```json
{ "creativity": 2, "precision": 2, "speed": 2, "critical_thinking": 2, "obedience": 2 }
```
Mit identischen `prompt_blocks` (siehe SoulAG-Audit §1 — Slider-Differenzierung ist toter Pfad über alle 8 Agents).

### Permissions — Drei-Welten-Drift
| Quelle | Permissions | Anzahl |
|---|---|---|
| JSON `WriterAG.json:19-24` | `[read, write, crawl, showbox_write]` | 4 |
| Python `agent_definitions.py:272` (DE) | `[read, write, crawl]` | 3 |
| Python `agent_definitions.py:277` (EN) | `[read, write, crawl]` | 3 |
| Live `soul.json` | `[read, write, crawl]` | 3 |

**JSON `showbox_write` ist Dead-Token:** kein Code-Pfad enforced `showbox_write` als Pflicht (verifiziert via `grep -rn "showbox_write" src/gnom_hub/agents/actions/` → 0 enforcement-Treffer). Identity-Block fordert "Showbox-Pflicht", aber Runtime kennt das Token nicht.

### Identity-Struktur
- **5 Sektionen** in JSON (gleiche Boilerplate wie alle Worker — siehe CoderAG-Audit §1.4):
  1. Identity-Header (Rolle, Sprech-Verbot, Workspace-Pin, Farbe Grün)
  2. Workspace-Pin (Priorität 0.7, hardcoded `/Users/landjunge/gnom-Workspace/default/`)
  3. Sprech-Verbot (Priorität 0.6, erlaubte Ausgaben + Verbote)
  4. Showbox+Buttons-Pflicht (Verweis auf showbox/spec/*)
  5. Tier-3b-Worker
- **Python `sys_prompt`** (agent_definitions.py:260-268): ~500 chars, viel kürzer als JSON, nur Rolle + Sprech-Verbot + Farbe. KEIN Workspace-Pin, KEIN Showbox+Buttons-Pflicht, KEIN Tier-Verweis.

### Stimme
- DE: Anna, EN: Samantha (`src/gnom_hub/soul/agent_voices.py:89`)
- TTS erzwungen ("Du denkst laut. Jeder Gedanke muss über TTS hörbar sein.") — gilt für alle Agenten

---

## 2. Spec-Konformität

### Showbox-Pflicht vs. Code-Realität
- **Spec** `showbox/spec/format.md:1-9`: Container `[SHOWBOX:<name>]` mit JSON-Body + `buttons[]`-Array
- **Spec** `showbox/spec/buttons.md:30-44`: 3-5 Buttons pro Showbox, immer "Schließen"-Button, Action-Registry
- **JSON-Identity**: Pflicht explizit genannt
- **Chat-Repo-Filter** `chat_repo.py:14-114`: droppt Worker-Chat ohne Purpose-Tag, loggt als `cooldown`
- **ABER:** `[WRITE:]`-Tags werden separat via `action_handlers.py` ausgeführt — die gehen nicht über Showbox, sondern direkt aufs Filesystem
- **Test:** `test_action_write_e2e.py` validiert Write-Tag-Ausführung, aber NICHT Showbox-Wrapper

**Befund:** Worker-Direktiven wie "8 Intros gespeichert" würden als Cooldown gefiltert. Write-Tags umgehen den Filter (separate Pipeline). Aber: was passiert wenn WriterAG beides will — Text-Ausgabe + Datei? Identity sagt "Showbox mit Button", Code trennt die Pfade.

### Crawl-Spec
- **Identity** fordert nicht explizit crawl
- **JSON permissions:** `crawl` als 4. Token
- **action_exec.py:37-46** `handle_crawl`: checkt nur `"crawl" in perms`, KEINE Domain-Whitelist
- **action_handlers.py:111-121**: pre-audit vor crawl-Match
- **Audit-Hook** `_audit_security` loggt ALLE crawl-Aufrufe in `security_audit_log` — WriterAG-Aufrufe erscheinen dort mit agent_name="writerag"

**Befund:** Crawl ist technisch da, aber Security/Compliance fehlt. WriterAG darf `crawl.example.com` UND `localhost-admin.example.com` ohne Unterschied.

### Tier-Hierarchie
- **Identity v5.3 notes:** "Worker: minimal — Workspace + Chat-History"
- **Tier-3b-Position** in SecurityAG identity erwähnt (`SecurityAG.json:18` Z.39)
- **GeneralAG identity** (GeneralAG.json:18): "Du empfängst Aufträge AUSSCHLIESSLICH von SoulAG" → Worker-Empfänger unklar in GeneralAG-Notes (nur "konsistent mit System-Agents")
- **Python `agent_definitions.py`:** kein Tier-Verweis

**Befund:** Worker-Tier ist nur in SecurityAG/GeneralAG notes erwähnt, NICHT in WriterAG-eigener Identity. Wer WriterAG direkt adressiert außer über GeneralAG weiß das nicht.

---

## 3. Code-Realität

### Write-Pfad (analog zu CoderAG)
- `[WRITE: pfad]inhalt[/WRITE]` → `action_handlers.py:48-181` `process_actions()` → `action_write.py`
- **Cold-Start-Hang-Fix** (Memory 2026-06-28): Import von `gnom_hub.core.zwc_codec` statt `gnom_hub.soul.zwc_soul` — Cold-Start ~5s statt ~30s
- **Workspace-Resolution:** `path_validator.py:7-25` `_safe(wd, f, perms)` — `perms=False` blockt Pfade außerhalb Workspace
- **Backup:** vor jedem Write wird Backup erstellt (siehe CoderAG-Audit §3.4)

### Crawl-Pfad
- `[CRAWL: url]` → `action_handlers.py:111-121` pre-audit → `action_exec.py:37-46` `handle_crawl()`
- **crawler_engine:** `gnom_hub.infrastructure.utils.crawler_engine` — `crawl_smart(url)` oder `crawl_data(url)`
- **Kein Domain-Filter, keine Rate-Limit, keine Robots.txt-Prüfung im Code**

### Sprech-Verbot-Filter
- `chat_repo.py:14-114` `add_chat_message()` — wenn `agent_layer == "worker"` und kein Purpose-Tag → droppt, loggt `cooldown`
- **Test bestätigt:** Cooldown-Events in `audit_log` mit `event_type="cooldown"`

### Showbox-Schreib-Pfad
- `[→ Showbox: name]{slides:[...]}` → `showbox_repo.py:save_showbox_presentation()` → DB
- **NEU:** `showbox_write`-Permission ist Dead-Token (siehe §1)

### Was WriterAG tatsächlich macht (empirisch)
- Erhält Delegation via `@WriterAG schreibe X` von GeneralAG (via swarm_comms.py routing)
- Schreibt File in `/Users/landjunge/gnom-Workspace/default/` (Workspace-Pin)
- Optional: crawlt URLs (crawl-Permission), aber Use-Case unklar (ResearcherAG ist zuständig)
- Output: Showbox-Card + optional [WRITE:]-Tag

---

## 4. Widersprüche INTERN

### W1: Permission-Dual-Truth (Pattern wie alle 8 Agents)
- JSON hat 4 Tokens, Python hat 3 — Drift 25%
- `showbox_write` ist in der JSON-Pflicht-Kette, aber Runtime kennt es nicht
- Live-Workspace folgt Python (nicht JSON)
- **Konsequenz:** User-Manipulation via `PUT /api/agents/{a_id}/sliders` aktualisiert JSON, aber nicht die Runtime-Permissions

### W2: Crawl ohne Use-Case-Begründung
- Identity sagt "schreibt klar, präzise und zielgrupperecht" — KEINE crawl-Begründung
- Aber `crawl`-Permission existiert (sowohl JSON als auch Python)
- ResearcherAG ist explizit für Recherche zuständig — Wer crawlt was?
- **Realität:** Beide haben `crawl`. Es gibt keine Workflow-Trennung "WriterAG holt sich Fakten via crawl" vs "ResearcherAG liefert Briefing via [WRITE:]".

### W3: Workspace-Sharing ohne Locking
- Alle 4 Worker pinnen `/Users/landjunge/gnom-Workspace/default/`
- KEINE Worker-spezifischen Subdirs in den JSON-Identities
- KEINE file-locking in `action_write.py`
- 2 parallele Worker-Tasks auf dieselbe Datei = Race-Condition / Datenverlust

### W4: Sprech-Verbot vs Showbox-Pflicht — Lücke bei Fehler-Meldungen
- VERBOTEN: 'Hier ist der Text...', 'OK fertig', Status-Reports ohne Showbox
- ERLAUBT: Showbox + Write + Read + Code-Block
- **Was wenn ein Tool fehlschlägt?** Identity listet keine Error-Kommunikation. Worker müsste Showbox mit "Fehler: X" bauen — aber das ist nicht explizit erlaubt/verboten.

---

## 5. Widersprüche zu ANDEREN Agents

### WriterAG vs CoderAG
- **Permissions-Unterschied:** CoderAG hat `run`, WriterAG hat `crawl` — kein gemeinsames Tool außer `read+write`
- **Workspace-Sharing:** beide pin `/Users/landjunge/gnom-Workspace/default/` — keine Subdir-Trennung
- **Output-Format:** CoderAG = Code-Files, WriterAG = Markdown/Text. Aber keine Format-Spec definiert, was eine "Writer-Lieferung" vom Format her exakt sein muss (Header? Body? Buttons? Bildunterschrift?)

### WriterAG vs EditorAG
- **Identity-Boilerplate identisch** (siehe §1) — nur Rollen-Satz + Farbe unterschiedlich
- **Sequenz:** Strategy B (Writer→Editor) existiert in `adaptive_decomposition.py:23`, aber Strategy C (Code-Review nach Code-Gen) FEHLT
- **Trigger:** EditorAG wird getriggert durch `korrigier/review/prüf/lektorat/refaktor`-Keywords in `swarm_comms.py:194` — wenn User das nicht sagt, kein Auto-Review

### WriterAG vs ResearcherAG
- **BEIDE haben `crawl`** — wer macht was?
- **ResearcherAG:** `crawl + web_search + browser` (4 Tools), aber **KEIN `write`!** (siehe ResearcherAG-Audit)
- **WriterAG:** `crawl` (1 Tool), plus `write + read`
- **Konsequenz:** ResearcherAG kann Fakten nicht persistieren (nur Showbox + inline-Quellen). WriterAG kann theoretisch crawlen + schreiben. Workflow unklar.

### WriterAG vs SoulAG
- SoulAG hat `crawl + evolve` (Python: agent_definitions.py:98)
- WriterAG hat `crawl`
- **SoulAG's `evolve`-Permission:** was bedeutet das? Code-Refactor? Self-Modification? Kein Code-Pfad enforced das als Worker-Privileg.
- **SoulAG's `crawl`:** kann selbst crawlen statt zu delegieren — überlappt mit WriterAG/ResearcherAG

### WriterAG vs SecurityAG
- SecurityAG hat `crawl` nicht in Python (`[read, write, run, godmode]`) — keine Recherche-Pflicht
- SecurityAG darf Worker-Blockaden auflösen (Tier 2b über Tier 3b)
- **Wenn WriterAG via crawl gegen Robots.txt verstößt:** SecurityAG muss manuell eingreifen (kein automatischer Crawl-Compliance-Check)

---

## 6. Lücken

### L1: Was ist eine "Writer-Lieferung" konkret?
- Identity definiert Rollen-Satz aber keinen Liefer-Standard
- Showbox-Slide-Inhalt: Free-Form? Markdown? HTML? Length-Limit?
- Tone-of-Voice-Preset? Es gibt `src/gnom_hub/api/endpoints/presets.py:247-256` mit "worker"-Gruppe, aber keine Writer-spezifischen Templates

### L2: Crawl-Compliance fehlt
- Keine Robots.txt-Check
- Keine Domain-Whitelist
- Keine Rate-Limit
- SecurityAG muss manuell prüfen — kein Auto-Alert

### L3: Tier-3b-Worker bekommt Outcome-Tracking nicht mit
- `generalag_outcomes`-Tabelle existiert (Schema `db/schema.py:314-324`) — aber 0 Code-Pfade füllen sie mit WriterAG als worker (gleicher Befund wie GeneralAG-Audit §5 für die Phantom-DB-Tabellen)
- Konsequenz: WriterAG-Performance wird nicht gemessen, GeneralAG's Worker-Stats sind unvollständig

### L4: Kein definiertes Fallback wenn Crawl fehlschlägt
- Was wenn `crawler_engine` 503/Timeout zurückgibt? Worker stoppt? Sendet Fehler-Showbox? Retry?
- Kein Code-Pfad definiert das Verhalten

### L5: Workspace-Subdir-Konvention fehlt
- Andere Worker (EditorAG, ResearcherAG) haben gleiche Pin-Lüge
- Wenn User Workspace wechselt → welche Worker-Files bleiben zurück? Keine Migration definiert

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 (HIGH): Permission-Drift Fix
- **Problem:** JSON `[read,write,crawl,showbox_write]` vs Python `[read,write,crawl]`
- **Lösung:** Entweder `showbox_write` aus JSON rausnehmen ODER in `agent_definitions.py` ergänzen
- **Empfehlung:** `showbox_write` ALS Runtime-Permission ergänzen + in `action_handlers.py` enforcement hinzufügen (pre-audit wie bei `crawl`)
- **Aufwand:** klein (2 Dateien, 5 Zeilen)
- **Risiko:** mittel — wenn enforcement hart ist, könnten bestehende Worker-Outputs brechen

### V2 (HIGH): Workspace-Subdir-Trennung
- **Problem:** Alle 4 Worker auf denselben Pin
- **Lösung:** `/Users/landjunge/gnom-Workspace/default/{coder,writer,editor,researcher}/` als Worker-spezifische Subdirs
- **Aufwand:** mittel (Identity-Updates + path_validator-Anpassung)
- **Risiko:** mittel — bestehende User-Workspaces müssten migriert werden

### V3 (HIGH): Crawl-Use-Case klären
- **Option A:** WriterAG verliert `crawl`, ResearcherAG liefert via [WRITE:] Briefing
- **Option B:** WriterAG behält `crawl` für "live content" (z.B. wenn User "schreib mir was über URL X" sagt)
- **Empfehlung:** Option A + explizite Identity-Klausel "WriterAG crawlt NICHT, erhält Briefing von ResearcherAG"
- **Aufwand:** klein (Identity-Update + Permission-Liste)
- **Risiko:** niedrig

### V4 (MEDIUM): Writer-Output-Format-Spec
- Liefer-Standard definieren: 1 Slide Title + Content + ≥1 Button (Approve/Reject/Refine)
- Datei: `showbox/spec/writer-output.md` (analog zu `format.md`/`buttons.md`)
- **Aufwand:** mittel (Spec schreiben + LLM-Prompt-Update)
- **Risiko:** niedrig

### V5 (MEDIUM): Crawl-Compliance-Layer
- Domain-Whitelist (Default: nur öffentliche Domains, keine Localhost)
- Rate-Limit (z.B. max 10 Requests/Minute/Agent)
- Robots.txt-Check via `urllib.robotparser`
- **Aufwand:** mittel (crawler_engine-Erweiterung)
- **Risiko:** niedrig

### V6 (MEDIUM): Workspace-Pin dynamisch
- Identity hardcoded `/Users/landjunge/gnom-Workspace/default/` lügt bei State-Override
- Lösung: `Config.workspace_dir()` Lookup im prompt_builder, Platzhalter `{workspace_dir}` in Identity
- **Aufwand:** klein (Identity-Template + builder.py update)
- **Risiko:** niedrig

### V7 (MEDIUM): Fehler-Kommunikations-Klausel
- Worker-Identity ergänzen: "Bei Tool-Fehlern: Showbox-Card mit Error-Slide + Buttons 'Retry'/'Abbrechen'"
- Vermeidet das Sprech-Verbot-Eck-Problem
- **Aufwand:** klein
- **Risiko:** niedrig

### V8 (LOW): Crawl-Fallback-Verhalten definieren
- Code-Pfad in `action_exec.py:37-46` ergänzen: bei `crawler_engine`-Fehler → Showbox-Card "Crawl fehlgeschlagen, möchtest du Retry?"
- **Aufwand:** klein
- **Risiko:** niedrig

### V9 (LOW): Tier-3b-Notiz in Worker-Identity
- Worker-Identities sollten Tier + Empfänger-Regel explizit nennen (User-Mandat 2026-06-28 11:53 Konsistenz)
- **Aufwand:** klein (4 Dateien)
- **Risiko:** niedrig

### V10 (LOW): WriterAG-spezifische Presets
- `presets.py:247` Worker-Gruppe hat aktuell keine Writer-Templates
- Templates für: Marketing-Text, README, Blog-Post, Landing-Page-Copy, E-Mail
- **Aufwand:** mittel
- **Risiko:** niedrig

---

## 8. Cross-Check-Notes für die Synthese

- **WriterAG ist der typische Worker-Boilerplate-Agent** — fast alle Befunde (Permission-Drift, Workspace-Pin-Lüge, Showbox-Boilerplate) gelten 1:1 für EditorAG/ResearcherAG/CoderAG
- **WriterAG hat den unique Befund "crawl ohne Use-Case"** — das muss Cross-Synthesis als zentrales Worker-Disziplin-Thema aufgreifen
- **Live-Workspace-Check** (`soul.json`) ist der einzige "drei Welten"-Check der alle 3 SSoT-Schichten (JSON, Python, Live) vergleicht — sollte für alle 8 Agents gemacht werden
- **Worker-Subdir-Trennung (V2)** ist die wichtigste architektonische Änderung — sollte mit EditorAG/ResearcherAG-Audits abgeglichen werden, weil die ALLE betroffen sind