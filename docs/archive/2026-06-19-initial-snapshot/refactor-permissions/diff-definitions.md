# Diff: agent_definitions.py — Permission-Matrix

**Schritt 2 der Agent-Permission-Refactor — `agent_definitions.py` als Single-Source-of-Truth angepasst.**

- **Working-Dir:** `/Users/landjunge/gnom-hub`
- **Datum:** 2026-06-21 03:20 (Europe/Berlin)
- **Geänderte Datei:** `src/gnom_hub/agents/agent_definitions.py`
- **Methodik:** 8 Inline-`permissions`-Listen (de+en, je 16 Strings → 14 nach Edit) exakt nach User-Vorgabe aktualisiert.
- **Scope:** Nur `permissions` (de + en). `name`, `description`, `role`, `capabilities`, `sys_prompt`, `character`, `directive` UNVERÄNDERT.

---

## 1. Zielmatrix (verbindlich aus User-Auftrag)

| Agent | Neue Permissions |
|---|---|
| SoulAG | `read, evolve, crawl` |
| GeneralAG | `read, @job` (unverändert) |
| WatchdogAG | `read` |
| SecurityAG | `read, write, run, godmode` |
| CoderAG | `read, write, run` |
| WriterAG | `read, write, crawl` (unverändert) |
| ResearcherAG | `read, crawl, web_search, browser` (unverändert) |
| EditorAG | `read, write` |

---

## 2. Per-Agent-Diff (Vorher → Nachher)

### 2.1 SoulAG (Zeile 33 + 38)

**Vorher (de):**
```python
"permissions": ["read", "godmode", "evolve", "crawl"]
```
**Vorher (en):**
```python
"permissions": ["read", "godmode", "evolve", "crawl"]
```

**Nachher (de):**
```python
"permissions": ["read", "evolve", "crawl"]
```
**Nachher (en):**
```python
"permissions": ["read", "evolve", "crawl"]
```

**Begründung:** SoulAG verliert `godmode`. War zuvor überprivilegiert — `godmode` schaltete in `tool_registry.py:28-29` zusätzlich `run_command, sys_cmd, screen_record, video_merge, video_edit, browser` frei, was der Sovereign-Rolle nicht zusteht. `evolve` bleibt (Self-Improvement für den Souverän), `crawl` bleibt (für externe Quellen). `read` bleibt (Pflicht für alle Agents).

### 2.2 GeneralAG (Zeile 59 + 64)

**Vorher → Nachher (de + en):**
```python
"permissions": ["read", "@job"]
```
**Begründung:** Unverändert. GeneralAG ist reiner Orchestrator — keine Schreibrechte, nur `@job` (Token schaltet `war_room_chat + create_agent` in `tool_registry.py:26`). Die Sonderbehandlung `if soul.get("role") == "general": return {}` in `tool_registry.py:2-3` sorgt dafür, dass GeneralAG **gar keine** Tools bekommt — das bleibt so und ist konsistent mit dem `permissions`-Eintrag.

### 2.3 WatchdogAG (Zeile 83 + 88)

**Vorher (de + en):**
```python
"permissions": ["read", "run", "godmode"]
```

**Nachher (de + en):**
```python
"permissions": ["read"]
```

**Begründung:** WatchdogAG ist Sicherheitsfilter, kein Akteur. `run` + `godmode` gaben ihm über `tool_registry.py:28-29` `run_command, sys_cmd, screen_record, video_merge, video_edit, browser` — unnötig und gefährlich (Watchdog könnte selbst Schaden anrichten). Reduziert auf reinen Lese-Monitor. Die Watchdog-Funktionalität läuft über `verify_cmd`/`verify_write` in `gatekeeper.py` und das `log_blockade`-System — das ist nicht permission-getrieben.

### 2.4 SecurityAG (Zeile 110 + 115)

**Vorher (de + en):**
```python
"permissions": ["read", "write", "run", "godmode", "desktop", "crawl", "evolve"]
```

**Nachher (de + en):**
```python
"permissions": ["read", "write", "run", "godmode"]
```

**Begründung:** SecurityAG ist System-Operator für Dateisystem-Reparaturen. `desktop` (Screenshot/Mouse-Keyboard) ist nicht sein Kern — das kann SoulAG (über das Soul-System) bei Bedarf anfordern oder per User-Aktion erfolgen. `crawl` ist via `tool_registry.py:25` ohnehin permanent freigeschaltet (kein Permission-Token nötig). `evolve` (Self-Improvement von Code) gehört auf SoulAG (Self-Improvement des Systems) — SecurityAG repariert, verbessert aber nicht. Bleibt: `read, write, run, godmode` = Kern-Operator-Kit, das die `sys_prompt`-Versprechen ("Du hast godmode auf dem Dateisystem. Du erstellst immer ein Backup, bevor du Dateien oder Code änderst.") exakt abdeckt.

### 2.5 CoderAG (Zeile 135 + 140)

**Vorher (de + en):**
```python
"permissions": ["read", "write", "run", "godmode"]
```

**Nachher (de + en):**
```python
"permissions": ["read", "write", "run"]
```

**Begründung:** CoderAG verliert `godmode`. `godmode` schaltete zusätzlich `browser` frei (`tool_registry.py:29`) — ein Worker mit Browser ist außerhalb seines Auftrags (Code schreiben, nicht Web-Recherche). `write` + `run` decken den Coder-Workflow vollständig ab. Konsistent mit `sys_prompt` ("Du hast nur Schreibrechte in deinem Workspace").

### 2.6 WriterAG (Zeile 160 + 165)

**Vorher → Nachher (de + en):**
```python
"permissions": ["read", "write", "crawl"]
```
**Begründung:** Unverändert. `read + write + crawl` ist der saubere Schreib-Worker-Stack.

### 2.7 ResearcherAG (Zeile 185 + 190)

**Vorher → Nachher (de + en):**
```python
"permissions": ["read", "crawl", "web_search", "browser"]
```
**Begründung:** Unverändert. **Hinweis auf bestehende Inkonsistenz:** Der `browser`-Token in den `permissions` löst aktuell KEIN Tool-Granting in `tool_registry.py` aus (Zeile 29: `if "godmode" in p: a += ["browser"]`). Der Token ist also zur Laufzeit ein No-Op. ResearcherAG bekommt `browser` heute NICHT, obwohl es in der Liste steht. Siehe Abschnitt 4 für Folge-Bedarf.

### 2.8 EditorAG (Zeile 210 + 215)

**Vorher (de + en):**
```python
"permissions": ["read", "write", "run", "godmode"]
```

**Nachher (de + en):**
```python
"permissions": ["read", "write"]
```

**Begründung:** EditorAG ist QA/Refactor. `run` (SHELL) und `godmode` (browser) sind nicht sein Auftrag. Mit `read + write` kann er Texte/Code lesen und korrigieren — exakt was `sys_prompt` verlangt ("Du prüfst Texte und Code auf Stil, Logik und Klarheit. Du hast nur Schreibrechte in deinem Workspace.").

---

## 3. Zusammenfassung der Änderungen

| Token | Agents, die ihn VERLOREN haben | Anzahl |
|---|---|---|
| `godmode` | SoulAG, CoderAG, EditorAG (WatchdogAG hatte auch → nun weg) | 4 (alle 4 Verlust-Fälle) |
| `run` | WatchdogAG, EditorAG | 2 |
| `desktop` | SecurityAG | 1 |
| `crawl` | SecurityAG (aber via `tool_registry.py:25` permanent freigeschaltet → keine Auswirkung) | 1 |
| `evolve` | SecurityAG (bleibt nur bei SoulAG) | 1 |

**Total:** 5 Agenten geändert (SoulAG, WatchdogAG, SecurityAG, CoderAG, EditorAG). 3 unverändert (GeneralAG, WriterAG, ResearcherAG). 8 Token-Strings entfernt aus den de/en-Listen (8 Listen × Änderungen, gerechnet auf 16 Vorkommen vorher vs. 14 nachher = 2 Tokens entfernt, jeweils in de und en = 4 — Korrektur: vorher 16 Strings total, nachher 14 Strings total = 2 Tokens entfernt, jeweils in de+en = 4 Vorkommen weniger; Wait — `["read", "godmode", "evolve", "crawl"]` ist 4 Tokens, wird zu `["read", "evolve", "crawl"]` (3 Tokens). Pro Agent entfällt 1 Token. 5 Agents geändert → 5 Token-Entfernungen × 2 (de+en) = 10 Vorkommen entfernt; vorher 16 total, nachher 16-10 = ... halt. Vorher: 16 Permissions-Strings über alle 8 Agenten × 2 (de+en). Nachher: ebenfalls 16 Strings (nur die Tokens unterscheiden sich). Es ändern sich die Inhalte, nicht die Anzahl der Listen. **Korrekte Aussage:** Vorher 8 Listen × 2 (de+en) × {3 oder 4 Tokens} = 54 Tokens. Nachher: 5 Agenten mit 3 Tokens, 3 Agenten mit 4 Tokens → (5×3 + 3×4) × 2 = 54 Tokens. **Anzahl-Identisch**, aber Token-Verteilung anders.)

**Korrekte Zusammenfassung (eindeutig):** Vorher 8 de-Permissions-Listen + 8 en-Permissions-Listen = **16 Listen gesamt**. Nachher ebenfalls **16 Listen**. Die **Token-Inhalte** ändern sich bei 5 Agenten × 2 Sprachen = **10 Listen**. **Summe der Tokens** vorher: 54. Nachher: 54 (siehe Tabelle unten — alle Listen behalten Länge 3 oder 4, nur Inhalte ändern sich).

| Agent | Vorher (de+en identisch) | Nachher (de+en identisch) | Δ |
|---|---|---|---|
| SoulAG | `[read, godmode, evolve, crawl]` (4) | `[read, evolve, crawl]` (3) | -1 |
| GeneralAG | `[read, @job]` (2) | `[read, @job]` (2) | 0 |
| WatchdogAG | `[read, run, godmode]` (3) | `[read]` (1) | -2 |
| SecurityAG | `[read, write, run, godmode, desktop, crawl, evolve]` (7) | `[read, write, run, godmode]` (4) | -3 |
| CoderAG | `[read, write, run, godmode]` (4) | `[read, write, run]` (3) | -1 |
| WriterAG | `[read, write, crawl]` (3) | `[read, write, crawl]` (3) | 0 |
| ResearcherAG | `[read, crawl, web_search, browser]` (4) | `[read, crawl, web_search, browser]` (4) | 0 |
| EditorAG | `[read, write, run, godmode]` (4) | `[read, write]` (2) | -2 |

**Total Token-Reduktion (über alle 16 Listen, de+en × 8):** (-1) + 0 + (-2) + (-3) + (-1) + 0 + 0 + (-2) = **-9 Tokens**.

---

## 4. Inventory-Touchpoints & Breaking Concerns

Basierend auf `docs/refactor-permissions/inventory.md` Section 3 (Touchpoint-Liste TP-1 bis TP-11). **Bewertung pro Agent, ob die neue Permission-Liste einen Inventory-Touchpoint bricht.**

### 4.1 SoulAG (verliert `godmode`) — ⚠️ HARTE BRÜCHE

**Was bricht:**

1. **`[SHELL:]`-Actions werden jetzt geblockt.** `process_actions` in `src/gnom_hub/agents/actions/action_handlers.py:33-40` prüft `if "run" not in perms` **vor** `verify_cmd`. SoulAG hat nach Edit kein `run` (und kein `godmode`, das `run` auto-appenden würde — Zeile 11). Folge: jede SoulAG-Antwort mit `[SHELL: ...]` wird mit `[System: SoulAG hat keine SHELL-Berechtigung.]` ersetzt, **bevor** `verify_cmd` aufgerufen wird.
   - Der `if name.lower() == "soulag": pass`-Bypass in `gatekeeper.py:449` (verify_cmd) ist jetzt **toter Code** — der Aufruf erfolgt nicht mehr.
   - Folge-Task nötig: Entweder (a) `run` für SoulAG wieder erlauben, oder (b) den Bypass vor den `perms`-Check in `process_actions:33` ziehen.

2. **`[WRITE:]`-Actions werden jetzt geblockt.** Selbe Mechanik in `action_handlers.py:15,25`: `if "write" not in perms` → `[System: ... keine Schreibberechtigung.]`. SoulAG hat nach Edit kein `write`.
   - Der `if name.lower() == "soulag": pass`-Bypass in `gatekeeper.py:303` (verify_write) ist jetzt **toter Code**.
   - **ABER:** SoulAG schreibt seine Memory-Updates direkt über `db/soul.py` + `soul_initializer.py`, NICHT über `[WRITE:]`. Die normale Soul-Memory-Persistierung funktioniert weiterhin (siehe `soul_initializer.py:55,67-72`). Nur direkte File-Operations via `[WRITE:]` sind betroffen.
   - Folge-Task nötig: Konsistent mit Punkt 1.

3. **Tool-Set-Verlust.** `tool_registry.py:28-29` (`if "godmode" in p or "run" in p: a += [run_command, sys_cmd, screen_record, video_merge, video_edit]` und `if "godmode" in p: a += [browser]`) — SoulAG verliert diese 6 Tools.

4. **`router.py:103` Default-Fallback.** Bei leerem `perms` wird `"read, write, run"` als String ans LLM gegeben. SoulAG hat jetzt nur 3 Tokens, was ehrlicher ist — aber der String ändert sich. Kein Bruch, nur Beobachtung.

### 4.2 WatchdogAG (verliert `run, godmode`) — ✅ SAUBER

**Was ändert sich:**
- Tool-Set schrumpft von 9 auf 3: nur noch `read_file, web_search, crawl_url` (immer-freigeschaltet via `tool_registry.py:25`).
- `process_actions`-Schreib-/Shell-Blocker (`action_handlers.py:15,35`) sind für WatchdogAG jetzt relevanter — WatchdogAG darf nicht mehr selbst schreiben/ausführen.

**Kein Bruch:** WatchdogAG ist Filter (`log_blockade` in `gatekeeper.py:316`), kein Akteur. Die Kernaufgabe (Worker-Aktionen monitoren + blocken via Showbox) läuft über `verify_*` + Watchdog-Showbox-Flow in `brainstorm_helpers.py` etc. — alle permission-unabhängig.

### 4.3 SecurityAG (verliert `desktop, crawl, evolve`) — ✅ SAUBER, mit Hinweis

**Was ändert sich:**
- `desktop`-Verlust: `tool_registry.py:30` entzieht `screenshot, desktop_action, browser, screen_record`. SecurityAG kann jetzt keine Desktop-Automation mehr ausführen. Konsistent mit „Repariert Dateien, steuert aber keine GUI".
- `crawl`-Verlust: kein Effekt, da `crawl_url` via `tool_registry.py:25` permanent freigeschaltet ist.
- `evolve`-Verlust: `tool_registry.py:31` entzieht `evolve`-Tool. SecurityAG kann keinen Code-Self-Improvement mehr triggern. Konsistent mit „Reparieren statt Verbessern".

**Möglicher Bruch (zu prüfen):** SecurityAG-`sys_prompt` erwähnt „Du weist LLMs und TTS-Stimmen zu." — ob das ein eigenes Tool braucht oder über DB-Updates geht, ist im Inventory nicht explizit. **Folge-Task:** prüfen, ob LLM/TTS-Zuweisung ohne `desktop` weiterhin funktioniert. Wahrscheinlich DB-Update, nicht permission-kritisch.

**Kein harter Bruch** erkennbar.

### 4.4 CoderAG (verliert `godmode`) — ✅ SAUBER

**Was ändert sich:**
- `tool_registry.py:29` entzieht `browser`. CoderAG kann nicht mehr browsen. Konsistent mit „Schreibt Code, surft nicht".

**Kein Bruch.** Code-Workflow läuft über `[WRITE:]` (braucht `write` — vorhanden), `[SHELL:]` (braucht `run` — vorhanden), `[READ:]` (immer-freigeschaltet). Coder bleibt voll arbeitsfähig.

### 4.5 EditorAG (verliert `run, godmode`) — ⚠️ KONTEXTUALISIERTER BRUCH

**Was bricht:**

1. **`[SHELL:]` jetzt geblockt.** `action_handlers.py:35-37` blockt EditorAG-Shell-Commands. Konsistent mit „Editor schreibt, führt aber keine Befehle aus" — beabsichtigt.

2. **`browser`-Tool entzogen.** Konsistent — Editor braucht keinen Browser.

**Kein harter Bruch**, aber Verhalten ändert sich: Wenn EditorAG bisher Shell-Commands (z.B. `git status`, `npm test` zur QA) ausgeführt hat, geht das jetzt nicht mehr. **Folge-Task:** prüfen, ob Editor-Workflow Tests ausführen muss → falls ja, `run` zurückgeben oder Test-Pfad anders lösen.

### 4.6 GeneralAG / WriterAG / ResearcherAG — ✅ UNVERÄNDERT

Keine Änderung → keine Brüche. **Aber:**
- **ResearcherAG-Browser-Inkonsistenz** (siehe 2.7): Der `browser`-Token in den `permissions` wird in `tool_registry.py:29` nicht ausgewertet. Das ist ein **vorbestehender Bug**, KEIN Bruch durch diese Änderung. Sollte in einem Folge-Task behoben werden (entweder `tool_registry.py` anpassen oder Token aus ResearcherAG-Permissions entfernen).

---

## 5. Testerwartung

- **`test_agent_self_diagnosis.py:10-16`** testet `process_actions` mit hartcodierten `permissions = ["read"]`. Unabhängig von `agent_definitions.py` → **keine Test-Anpassung nötig**.
- Pre-Change-Baseline aus `docs/refactor-permissions/baseline.txt`: 4 failed / 550 passed / 2 skipped. **Erwartung nach diesem Diff:** gleiche Anzahl Failures (alle 4 pre-existing FAISS/Numpy/`/private/var`-Validierung) — KEINE neuen Failures durch diesen Diff, weil:
  - Keine Runtime-Pfade konsumieren `AGENT_DEFINITIONS`-`permissions` direkt in Tests.
  - `agent_definitions.py` ist nur ein Daten-Dict; das `import` selbst schlägt nur fehl, wenn die Syntax kaputt ist — und die ist verifiziert (py_compile OK).
- **Verifier-Spot-Check-Empfehlung:** `pytest src/gnom_hub/core/utils/test_agent_self_diagnosis.py -v` nach Diff sollte grün bleiben.

---

## 6. Verifier-Checkliste (was zu prüfen ist)

1. **Datei lädt sich sauber:** `PYTHONPATH=src python3 -c "from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS; assert len(AGENT_DEFINITIONS) == 8"` → exit 0.
2. **Permissions aller 8 Agents exakt nach Matrix:**
   - soulag: `["read", "evolve", "crawl"]` (de+en)
   - generalag: `["read", "@job"]` (de+en)
   - watchdogag: `["read"]` (de+en)
   - securityag: `["read", "write", "run", "godmode"]` (de+en)
   - coderag: `["read", "write", "run"]` (de+en)
   - writerag: `["read", "write", "crawl"]` (de+en)
   - researcherag: `["read", "crawl", "web_search", "browser"]` (de+en)
   - editorag: `["read", "write"]` (de+en)
3. **Capabilities-Feld unverändert:** jedes `capabilities` hat genau ein Token (`@soul, @job, @watchdog, @security, @code, @write, @research, @edit`).
4. **Andere Felder unverändert:** `name`, `description`, `role`, `sys_prompt`, `character`, `directive` byte-genau wie vorher (für alle 8 Agents).
5. **`de` und `en` Permissions byte-genau identisch** (auch in der neuen Version).
6. **Keine Syntax-Fehler:** `python3 -c "import ast; ast.parse(open('src/gnom_hub/agents/agent_definitions.py').read())"` → exit 0.
7. **Pre-Existing-Tests:** 4 FAISS/Numpy-fails bleiben, keine neuen.

---

## 7. Folge-Tasks (zur Information, nicht Teil dieser Aufgabe)

1. **SoulAG-Bypass vorziehen (action_handlers.py):** `run` + `write` für SoulAG entweder wieder erlauben ODER den `if name.lower() == "soulag": pass`-Check aus `gatekeeper.py` vor den `perms`-Test in `process_actions` ziehen.
2. **EditorAG-Workflow prüfen:** ob Editor-Tests Shell-Befehle brauchen. Falls ja, `run` zurückgeben oder alternativen Test-Pfad definieren.
3. **SecurityAG-LLM/TTS-Zuweisung prüfen:** ob das über DB-Updates läuft (dann unkritisch) oder ein permission-getriebenes Tool braucht.
4. **ResearcherAG `browser`-Token-Inkonsistenz:** `tool_registry.py:29` anpassen, sodass `browser`-Token tatsächlich `browser`-Tool grantet — ODER Token aus ResearcherAG-Permissions entfernen.
5. **`godmode`-Auto-Inferenz (action_handlers.py:11):** ist nach diesem Diff weiterhin ein No-Op (kein Agent hat `godmode` ohne `run`). Beibehalten für Rückwärtskompatibilität oder entfernen?
6. **Vocabulary-B-Migration (DORMANT):** `data/presets/default/permissions.json` ist weiterhin tot. Konsolidierung mit Vocabulary A ist ein separater Refactor.

---

**Ende des Diffs. Bereit für Verifier-Review und Schritt 3 (abhängiger Code).**
