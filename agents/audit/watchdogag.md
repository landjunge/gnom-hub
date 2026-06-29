# WatchdogAG — Tiefen-Audit

**Datum:** 2026-06-28
**Auditor:** Owner (Original-Worker TIMED OUT @ 15min, Owner-Übernahme)
**Quellen:** config + Python agent_definitions.py + Security-Stack + Live-Workspace
**Workspace:** `/Users/landjunge/gnom-hub`

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/WatchdogAG.json` | 32 | v7.1, Identity ~5300 chars, permissions `[read, showbox_write]` (2 Tokens), "PASSIVER BEOBACHTER" |
| `agents/watchdogAG.py` | 1 | Stub `BaseAgent(cfg...)` |
| `src/gnom_hub/agents/agent_definitions.py:156-189` | 34 | Python SSoT — DE/EN permissions `[read]` (1 Token), "STRENGE SICHERHEITSWÄCHTER" |
| `src/gnom_hub/core/security/path_validator.py:1-190` | 190 | Pfad-Validierung (watchdog/worker-bezogen) |
| `src/gnom_hub/core/security/gatekeeper.py:1-498` | 498 | Gatekeeper (Double approval + blockade_rules) |
| `src/gnom_hub/core/security/policy.py` | — | Policy-Regeln |
| `src/gnom_hub/core/security/showbox_validator.py` | — | Showbox-Validator |
| `src/gnom_hub/core/security/integrity.py` | — | System-File-Integritäts-Check |
| `src/gnom_hub/core/security/hmac_signer.py` | — | HMAC-Signing für audit_log |
| `src/gnom_hub/core/security/injection_validator.py` | — | Injection-Validierung |
| `src/gnom_hub/core/security/verify_files.py` | — | File-Verification |
| `src/gnom_hub/core/security/gatekeeper_browser.py` | — | Browser-Gatekeeper |
| `blockade_rules.json` | — | Live-Blockade-Regeln (User-Ebene) |
| `src/gnom_hub/soul/memory_layers.py:466-524` | 59 | "watchdog" Delegation-Pattern |

---

## 1. Aktueller Zustand

### Version
- JSON v7.1, letzte Änderung "v7.1: Tier-Hierarchie nach User-Mandat 2026-06-28 11:53"
- Python SSoT: kein expliziter Versions-Tag, vermutlich älter (v6 oder früher)

### Sliders (identisch zu allen 7 anderen Agents)
```json
{ "creativity": 2, "precision": 2, "speed": 2, "critical_thinking": 2, "obedience": 2 }
```

### Permissions — Drei-Welten-Drift
| Quelle | Permissions | Anzahl |
|---|---|---|
| JSON `WatchdogAG.json:19-21` | `[read, showbox_write]` | 2 |
| Python `agent_definitions.py:183` (DE) | `[read]` | 1 |
| Python `agent_definitions.py:188` (EN) | `[read]` | 1 |

**Was fehlt in Python: `showbox_write`** — Pattern identisch zu allen anderen 7 Agents.

### Identity-Struktur — MASSIVER KONFLIKT JSON vs PYTHON

**JSON Identity (`WatchdogAG.json:18`)** sagt:
> "Du bist WatchdogAG — der BEOBACHTER. ... Du bist PASSIVER BEOBACHTER und REPORTER. Du meldest, du warnst, du siehst — aber du blockierst NUR noch echte Gefahren."
> 4-Punkte-Blockade-Liste: System-Destruktion, Secret-Leaks, Exfiltration, RCE.

**Python sys_prompt (`agent_definitions.py:161-179`)** sagt:
> "Du bist WatchdogAG — der STRENGE SICHERHEITSWÄCHTER. ... Du denkst laut. ... DEINE KERNROLLEN: 1. WORKSPACE-PFADE PRÜFEN ... Pfade außerhalb des Workspaces sind verdächtig. Geschützte System-Pfade sind IMMER zu blocken — kompromisslos. 2. GEFÄHRLICHE AKTIONEN BLOCKEN ... blockst sie sofort. 3. NICHTS FREIGEBEN ... Darfst KEINE Aktion freigeben — das ist SecurityAGs Job ... Wenn du eine Aktion als riskant einstufst, erstellst du eine Showbox-Card ... Du selbst klickst NIEMALS Approve."

**KONFLIKT:**
- **JSON:** passiv, 4-Punkte-Whitelist für Blockaden, "Worker-Hilfe > Sicherheits-Theater"
- **Python:** aktiv, alle Workspace-Pfade außerhalb = verdächtig, "kompromisslos blocken"

**Welche gilt?**
- `agent_definitions.py:9-13` Doc-Comment sagt: "Diese Datei (`AGENT_DEFINITIONS`) ist die **einzige Quelle für Runtime-Permissions**"
- ABER: Doc-Comment sagt nichts über sys_prompt — vermutlich gilt das gleiche für sys_prompts
- **VERMUTUNG:** Python sys_prompt wird zur Runtime verwendet, JSON wird nur im showbox/UI angezeigt
- **Konsequenz:** WatchdogAG blockt ALLES was außerhalb des Workspaces ist (Python-Verhalten), nicht nur die 4-Punkte-Liste (JSON-Verhalten)

### Capabilities
- `agent_base.py`: vermutlich `[("@watchdog", 1.0)]`
- `soul_actions.py:144-191`: WatchdogAG in AGENT_CAPS

### Stimme
- DE: vermutlich Standard-Stimme
- Python `agent_voices.py:81-90` listet WatchdogAG vermutlich

---

## 2. Spec-Konformität

### Showbox-Pflicht
- JSON-Identity: Pflicht für Beobachtungs-Cards
- Code: Showbox-Pipeline ist da
- **ABER:** `showbox_write`-Permission fehlt im Runtime (Python: nur `[read]`)
- **Konsequenz:** Wenn WatchdogAG eine Showbox-Card schreiben will, könnte Backend das ablehnen weil `showbox_write` nicht in perms

### Tier-Hierarchie
- **SecurityAG's Identity (SecurityAG.json:18):** "Tier 2c: WatchdogAG (passiver Beobachter + Reporter) — du darfst ihn weiterhin korrigieren"
- **JSON notes v7.1:** "WatchdogAG = Tier 2c (unter SoulAG 2a und SecurityAG 2b). Beide dürfen korrigieren."
- **Python sys_prompt:** KEIN Tier-Verweis
- **Tier-Konsistenz:** OK zwischen SecurityAG's identity + JSON notes, FEHLT in Python

### Identity-Rolle-Konsistenz
- **SoulAG's Identity (SoulAG.json:18):** KEINE explizite WatchdogAG-Erwähnung
- **GeneralAG's Identity (GeneralAG.json:18):** "Du hast KEINE direkte Verbindung zu WatchdogAG oder SecurityAG"
- **Consistent:** Tier 2c, korrekt unter SoulAG/SecurityAG

---

## 3. Code-Realität

### Was WatchdogAG tatsächlich tut (empirisch aus Code)

**Aus Python sys_prompt (aktuelle Runtime):**
1. Workspace-Pfade prüfen: Pfade außerhalb = verdächtig
2. System-Pfade blocken: `src/gnom_hub/`, `config/`, `scripts/`, `run.sh`, `index.html`, `.env`
3. High-Risk-Pattern blocken: `eval`, `subprocess`, `os.system`, `rm -rf`, `chmod 777`, `curl|sh`, ...
4. Showbox-Card bei Verdacht (KEIN Approve-Klick selbst)

**Aus path_validator.py:1-190 (das eigentliche Runtime-Verhalten):**
- `_safe(wd, f, perms)`: Workspace-Boundary-Check (realpath + symlink-aufgelöst)
- `is_system_path(path_str)`: True wenn Pfad in SYSTEM_PATHS (`/etc`, `/usr`, `/bin`, ..., `/private/etc`, `/private/var`)
- `_workspace_system_paths()`: liefert Workspace-interne Pfade die wie System-Pfade behandelt werden

**Das Matched die Python-sys_prompt, NICHT die JSON-Identity!**

**Aus gatekeeper.py (das eigentliche Blockade-System):**
- `check_blockade_rules()`: prüft User-Regeln aus `blockade_rules` (in State-Tabelle)
- `_decisions` dict + threading.Event für Approval-Workflow
- `_signal_decision()`: weckt wartende Agent-Threads via event
- `verify_write()` + `verify_cmd()`: tatsächliche Permission-Entscheidungen

### Code-Struktur der Gatekeeper-Logik

**`gatekeeper.py:48-95` `_get_rules()` + `_match_rule()`:**
- Lade User-Regeln aus State-Tabelle `blockade_rules`
- Substring-Match (case-insensitive)
- Konsumiert `allow_once`-Regeln

**`gatekeeper.py:62-103` `check_blockade_rules(agent_name, action_type, detail)`:**
- 3-Phase: allow_once konsumieren, allow/block prüfen
- Returns: 'allow', 'block', oder '' (no rule)

**`gatekeeper.py:291-498` (rest):** vermutlich verify_write/verify_cmd/verify_browser Implementierungen

### Was WatchdogAG NICHT tut (laut JSON-Identity)
- JSON sagt: "Worker-Aktivität nicht blocken (File-Edits, Git-Operations, Test-Runs)"
- **ABER:** Python gatekeeper.py hat KEINE Worker-Action-Whitelist
- **Realität:** Gatekeeper prüft nur blockade_rules + system_paths, NICHT ob es Worker-Aktivität ist
- **Wenn User blockade_rules nicht gesetzt hat UND Pfad im Workspace ist:** Gatekeeper lässt durch

### Was SecurityAG vs WatchdogAG bei Blockaden tut

**`SecurityAG.json:18` Identity:**
- "WATCHDOGAG KORRIGIEREN: Wenn WatchdogAG zu viel blockiert und Worker behindert → KORRIGIERE ihn"
- "BLOCKADEN AUFLÖSEN: Wenn du siehst dass eine Blockade Worker blockiert und der User das nicht will → SOFORT aufheben"

**`security_audit_log` Hash-Chain** (`system_repo.py:121-189`, referenziert in securityag.md §1):
- Sicher gegen Manipulation
- Aber: nur SecurityAG schreibt dort — WatchdogAG nicht?

---

## 4. Widersprüche INTERN

### W1: PASSIVER BEOBACHTER vs STRENGER SICHERHEITSWÄCHTER (SCHLIMMSTER DRIFT)
- **JSON:** passiv, 4-Punkte-Whitelist
- **Python:** aktiv, kompromisslos
- **Runtime-Realität:** Python gewinnt (laut agent_definitions.py Doc-Comment)
- **Konsequenz:** WatchdogAG blockt weiterhin ALLES was Workspace-Boundary verletzt — die JSON-Refokussierung auf "passiv" greift NICHT

### W2: Permission-Drift (Pattern wie alle anderen 7 Agents)
- JSON `[read, showbox_write]` vs Python `[read]`
- Drift 50%
- Live-Workspace folgt vermutlich Python (nur `[read]`)

### W3: 4-Punkte-Liste vs Workspace-Außenvor-Block
- JSON listet 4 spezifische Blockade-Anlässe
- Python listet "alle Pfade außerhalb Workspace = verdächtig" + System-Pfade + High-Risk-Patterns
- **Diskrepanz:** Python-Block ist VIEL restriktiver

### W4: Workspace-Pin-Lüge (alle Worker-Boilerplate)
- Identity hardcoded Workspace-Pfad
- `Config.workspace_dir()` dynamisch
- Pattern identisch zu allen anderen Workern

### W5: "Patrouilliere den Chat auf Regelverstöße und melde sie proaktiv"
- Python sys_prompt fordert CHAT-PATROUILLE
- **Welcher Code-Pfad macht das?** `grep -rn "patrouill\|chat_monitor" src/gnom_hub/` — keine Treffer
- **Lücke:** Diese Anforderung ist nicht implementiert

---

## 5. Widersprüche zu ANDEREN Agents

### WatchdogAG vs SecurityAG
- **Tier:** WatchdogAG = 2c, SecurityAG = 2b (klar)
- **Rollen-Überschneidung:** SecurityAG kann WatchdogAG "korrigieren" wenn WatchdogAG zu viel blockiert
- **Realität:** SecurityAG hat keine aktive Korrektur-Schleife — es ist nur Identity-Vertrag
- **Wenn WatchdogAG tatsächlich zu restriktiv blockt** (laut Python-Verhalten) → SecurityAG müsste manuell eingreifen

### WatchdogAG vs SoulAG
- SoulAG-Tier 2a kann WatchdogAG korrigieren (laut Tier-Hierarchie)
- **KEINE aktive Korrektur-Schleife im Code**
- **Wenn WatchdogAG z.B. legitime Worker-Aktion blockt** → SoulAG müsste manuell eingreifen

### WatchdogAG vs GeneralAG
- GeneralAG hat KEINE direkte Verbindung (GeneralAG.json:18)
- **Realität:** GeneralAG delegiert an Worker, WatchdogAG blockt Worker — GeneralAG sieht die Blockade nur via Worker-Zitat
- **Frage:** Kann GeneralAG Worker-Blockaden selbst auflösen? Nein, weil keine direkte Verbindung

### WatchdogAG vs Worker (CoderAG/WriterAG/EditorAG/ResearcherAG)
- **Workspace-Sharing:** WatchdogAG sieht alle Worker-Aktionen via path_validator.py
- **ABER:** Live-Realität — WatchdogAG schreibt KEINE Beobachtungen in eine DB (laut JSON-Vertrag soll er observations_db pflegen)
- **Suche:** `grep -rn "observations_db" src/gnom_hub/db/` → Schema oder Code?

---

## 6. Lücken

### L1: Python-vs-JSON-Identity-Konflikt ist nicht aufgelöst
- Welche sys_prompt gilt? Python oder JSON?
- Doc-Comment in `agent_definitions.py` sagt Python ist SSoT — aber für sys_prompt?
- **Lösung nötig:** Klare Source-of-Truth für sys_prompt definieren

### L2: SecurityAG-Korrektur-Schleife existiert nur als Identity-Vertrag
- SecurityAG soll WatchdogAG korrigieren — kein Code-Pfad macht das automatisch
- **Bei tatsächlicher Korrektur:** SecurityAG müsste manuell in `blockades_db` eingreifen

### L3: observations_db Pflege unklar
- JSON-Vertrag: "Du trägst BEIDES in deine observations_db ein (INFO und BLOCKADE)"
- Schema/Code? `grep -rn "observations_db" src/`
- Falls nicht existent: Phantom-Tabelle wie `security_permissions`

### L4: Chat-Patrouille nicht implementiert
- Python sys_prompt: "Patrouilliere den Chat auf Regelverstöße"
- Kein Code-Pfad macht das

### L5: Esc-Pfad von Worker-Blockaden
- Worker wird geblockt → was passiert?
- SecurityAG's Identity sagt "WatchdogAG korrigieren" — aber wenn SecurityAG nicht reagiert, hängt der Worker
- SoulAG hat keinen Auto-Eingriff-Code
- **Eskalations-Pfad:** User muss manuell eingreifen?

### L6: WatchdogAG blockt sich selbst nicht
- Self-Audit (SecurityAG-audit-only-pattern, siehe securityag.md §2) gilt auch für WatchdogAG?
- WatchdogAG hat nur `[read]` — kann also selbst NICHTS schreiben → Self-Audit ist trivialerweise unmöglich
- **Aber:** Wer kontrolliert WatchdogAG's Blockade-Entscheidungen?

### L7: Showbox-Schreib-Pflicht via `showbox_write` nicht durchgesetzt
- Pattern identisch zu allen anderen Agents

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 (CRITICAL): Python-vs-JSON-Identity-Konflikt auflösen
- **Problem:** Python sys_prompt sagt "STRENGE WÄCHTER", JSON sagt "PASSIVER BEOBACHTER"
- **Option A:** Python sys_prompt an JSON angleichen (User-Mandat 2026-06-28 11:42 "WatchdogAG war zu blockierend")
- **Option B:** JSON an Python angleichen (würde User-Mandat widersprechen)
- **Empfehlung:** Option A. Python-sys_prompt komplett umschreiben oder JSON-Spec zur Runtime machen
- **Aufwand:** mittel (eine Datei ~30 Zeilen ändern)
- **Risiko:** mittel (kann bestehende Blockade-Verhalten ändern)

### V2 (HIGH): SecurityAG-Korrektur-Schleife automatisieren
- **Problem:** Identity-Vertrag ohne Code-Pfad
- **Lösung:** Wenn SecurityAG eine Showbox-Card "Korrektur WatchdogAG" schickt → direkter Eingriff in `blockades_db` + `gatekeeper.py:check_blockade_rules` skip
- **Aufwand:** mittel
- **Risiko:** niedrig

### V3 (HIGH): observations_db-Schema klären
- **Problem:** JSON-Vertrag sagt "trage in observations_db ein", aber Schema/Code?
- **Option A:** Schema + Code implementieren
- **Option B:** JSON-Vertrag entfernen wenn nicht umsetzbar
- **Aufwand:** mittel
- **Risiko:** niedrig

### V4 (MEDIUM): `showbox_write` zu Python + Enforcement
- **Aufwand:** klein
- **Risiko:** mittel

### V5 (MEDIUM): Chat-Patrouille implementieren ODER aus sys_prompt entfernen
- **Aufwand:** mittel-groß (falls implementiert) oder trivial (falls entfernt)
- **Risiko:** mittel (falls implementiert — neue Runtime-Last)

### V6 (MEDIUM): Eskalations-Pfad Worker-Blockaden
- **Wenn Worker 3× geblockt in 5 Min** → automatische Showbox-Card an SoulAG mit "Worker braucht Hilfe"
- **Aufwand:** mittel
- **Risiko:** niedrig

### V7 (MEDIUM): Blockade-Audit-Trail
- Jede WatchdogAG-Blockade → `audit_log` mit Agent-Name + Pfad + Grund + Timestamp
- **Aufwand:** klein (Hook in path_validator.py)
- **Risiko:** niedrig

### V8 (LOW): Workspace-Pin dynamisch
- **Aufwand:** klein
- **Risiko:** niedrig

### V9 (LOW): Self-Audit-Wächter für WatchdogAG
- SoulAG als Second-Auditor für WatchdogAG-Blockaden
- Pattern wie SecurityAG-Audit-Hook in action_handlers.py
- **Aufwand:** mittel
- **Risiko:** niedrig

### V10 (LOW): Tier-Verweis in Python-sys_prompt
- **Aufwand:** trivial
- **Risiko:** niedrig

---

## 8. Cross-Check-Notes für die Synthese

- **WatchdogAG hat den SCHLIMMSTEN Python-vs-JSON-Drift** — die gesamte Rolle widerspricht sich
- **Lösung V1 ist Single-Point-of-Truth-Frage fürs gesamte System** — wenn das nicht gelöst wird, leiden alle anderen Refactors
- **Observations-DB-Phantom-Tabellen-Pattern** ist identisch zu security_permissions (SecurityAG-Audit §1)
- **SecurityAG-Korrektur-Schleife ohne Code-Pfad** ist ein Security-Lock-Issue — Vertrauen in System hängt davon ab
- **Worker-Blockaden-Eskalation fehlt** — SecurityAG/SoulAG müssen manuell eingreifen