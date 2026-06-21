# LLM-Page — Broken Modules Analysis

**Stand:** 2026-06-21 (Owner-Skip — team plan `plan_0690f6bc` an 15min-Hardcap auf `identify-broken` gestorben)
**Quelle der Findings:** User-Feedback + Code-Inspektion `src/gnom_hub/frontend/dashboard.js:405-901`

---

## Methodik

Pro gerendertes UI-Element auf der LLM-Page (`showLLMConfig()`, dashboard.js:405) wurde geprüft:
1. Existiert ein Event-Listener?
2. Hat der Listener eine wirksame Aktion?
3. Wird das Resultat sichtbar im UI (Status-Badge, Text, Toast)?
4. Wird der State in `window.llmPendingChanges` getrackt?
5. Wird beim Save (`window.__llmRefreshAfterSave`) refresht?

Backend-Endpoints via `/api/llm/*` (alle lt. Baseline vorhanden und implementiert).

---

## Modul-Tabelle

| Modul | Element | Render-Zeile | Hat Listener | Wirksame Aktion | Sichtbar-im-UI | PendingChange | RefreshAfterSave | STATUS |
|---|---|---|---|---|---|---|---|---|
| Keys-Input | `<input id="llm-keys-input">` | 512 | ✅ paste+change (782-783) | ✅ processKeyText → testAndSave | ✅ #llm-status | n/a (Direkt-Save) | n/a | OK |
| File-Import | `<button id="llm-import-file-btn">` | 513 | ✅ click (776) | ✅ file-input.click | implizit | n/a | n/a | OK |
| Agent-Provider | `<select data-field="provider">` | 428 | ✅ change (786) | ✅ queueAgentChange | ✅ Status-Dot | ✅ | ✅ | TEILWEISE — Status-Dot bleibt grau |
| **Agent-Model** | **`<input data-field="model">`** | **433** | **✅ change (801)** | **✅ queueAgentChange** | **❌ Input statt Dropdown** | **✅** | **✅** | **❌ BROKEN — soll Dropdown sein** |
| **Capabilities-Spalte** | **`<td>text</td>`** | **435** | **n/a** | **❌ statisch 'text'** | **❌** | **n/a** | **❌** | **❌ BROKEN — hartkodiert** |
| **Status-Lämpchen** | **`.llm-status-dot`** | **436** | **n/a (sollte auf Provider-Change reagieren)** | **❌ keine Update-Logik** | **❌ bleibt grau (#6b7a90)** | **n/a** | **❌** | **❌ BROKEN — keine Farb-Logik** |
| **Caps (DB)-Spalte** | **`<td data-agent-cap>`** | **437** | **n/a** | **❌ statisch '—'** | **❌** | **n/a** | **❌** | **❌ BROKEN — nie befüllt** |
| Mode-Buttons | `.llm-mode-btn` | 444 | ✅ click (820) | ✅ autoRoute → Backend | ✅ Status-Text | ✅ | ✅ | OK |
| Service-Card Provider | `<select data-llm-svc>` | 473 | ✅ change (804) | ✅ queueServiceChange | ✅ Status-Badge | ✅ | ✅ | OK |
| Service-Card Model | `<select data-svc-field="model">` | 480 | ✅ change (810) | ✅ queueServiceChange | ✅ Status-Badge | ✅ | ✅ | OK |
| Service-Card Key | `<input data-svc-field="key">` | 488 | ✅ change (813) | ✅ queueServiceChange + Refresh | ✅ Status-Badge | ✅ | ✅ | OK |
| Service-Card Test | `<button data-svc-test>` | 490 | ✅ click (826) | ✅ POST /api/llm/test | ✅ Status-Line | n/a (inline) | n/a | OK |
| Save-Hinweis | statischer Text | 527 | n/a | n/a | ✅ | n/a | n/a | OK |

**5 von 13 Modulen broken oder unvollständig.**

---

## Severity-Ranking

### ❌ CRITICAL — Broken

**1. Agent-Model-Dropdown fehlt** (Severity: Critical)
- **Datei:Zeile:** `src/gnom_hub/frontend/dashboard.js:433`
- **Aktuell:** `<input data-field="model" placeholder="" value="" />`
- **Soll:** `<select data-field="model">` mit verfügbaren Modellen des gewählten Providers
- **User-Impact:** User muss Model-Namen auswendig wissen. Bei Tippfehler silent failure.
- **Fix-Pfad:**
  - Provider-Liste kommt aus `loadProviderRegistry()` (bereits geladen in `allProviders`, Zeile 420)
  - Bei Provider-Wechsel: `updateAgentModelPlaceholder()` (Zeile 557) muss das `<select>` neu befüllen statt nur Placeholder zu setzen
  - Model-Liste kann aus `/api/llm/providers` (liefert `models_per_provider`) oder aus openrouter-API geholt werden
  - Fallback: free-text-input wenn keine Liste verfügbar

**2. Status-Lämpchen (.llm-status-dot) bleibt grau** (Severity: Critical)
- **Datei:Zeile:** `src/gnom_hub/frontend/dashboard.js:436`
- **Aktuell:** `background:#6b7a90;` (Default-Grau, hardcodiert)
- **Soll:** Dot wird grün wenn gültiger Key für den Provider existiert (lookup via `/api/llm/keys`), gelb wenn pending, rot wenn kein Key, grau wenn nichts gewählt
- **User-Impact:** User sieht nicht welcher Agent provider-ready ist. Massiver Verlust der visuellen Orientierung.
- **Fix-Pfad:**
  - Helper-Funktion `refreshAgentStatusDot(agentName, provider)` schreiben
  - Bei `populateAgentProviders()` (Zeile 539) und bei jeder Provider-Änderung aufrufen
  - Logik ähnlich `refreshServiceCard` (Zeile 566) aber für Agent-Status

**3. Capabilities-Spalte hartkodiert 'text'** (Severity: Major)
- **Datei:Zeile:** `src/gnom_hub/frontend/dashboard.js:435`
- **Aktuell:** `<td>text</td>` für jeden Agenten
- **Soll:** Liste der Caps des gewählten Providers (z.B. `['text','vision','tools']` aus `provider.caps`)
- **User-Impact:** Capabilities sind eine zentrale Information auf der LLM-Page — User kann nicht entscheiden welcher Provider für welche Aufgabe passt.
- **Fix-Pfad:**
  - In `populateAgentProviders()` nach `populateAgentProviders` ein Pendant `updateAgentCapsColumn()` bauen
  - Bei Provider-Wechsel: Caps-Spalte neu rendern

**4. Caps (DB)-Spalte hartkodiert '—'** (Severity: Major)
- **Datei:Zeile:** `src/gnom_hub/frontend/dashboard.js:437`
- **Aktuell:** `<td data-agent-cap="${a}">—</td>` für jeden Agenten
- **Soll:** Caps die aktuell in der DB für den Agent gespeichert sind (aus `/api/llm/agents` Response, `caps`-Feld)
- **User-Impact:** User sieht nicht was tatsächlich wirksam ist — Diskrepanz zwischen UI-Wahl und DB-State unsichtbar.
- **Fix-Pfad:**
  - In `loadAgents()` (Zeile 692) zusätzlich die `caps` aus Response lesen und in die Spalte schreiben

### ⚠️ MAJOR — Teilweise OK

**5. Kein expliziter "Save"-Button auf der LLM-Page**
- **Datei:Zeile:** `dashboard.js:526-528` (nur Hinweis-Text)
- **User muss im Header speichern** (separater Save-Button vom globalen System)
- **Fix-Optionen:**
  - (a) Hinweis klarer machen: "Save-Button oben rechts im Header"
  - (b) Save-Button zusätzlich inline am Seitenende
  - Empfehlung: (a) — Hinweistext präziser formulieren

---

## Beobachtungen aus Backend-Endpoints

Lt. Baseline (`docs/llm-page-audit/baseline.txt`):

| Endpoint | Methode | FE-Nutzung | Impl-Datei | Status |
|---|---|---|---|---|
| /api/llm/providers | GET | ✅ loadProviderRegistry (dashboard.js:3718) | llm_models.py:110 | OK |
| /api/llm/test | POST | ✅ 665, 837 | llm_keys.py:30 | OK |
| /api/llm/keys | GET/POST | ✅ 672, 682, 700, 800, 813, 868, 897 | llm_keys.py:10/15 | OK |
| /api/llm/agents | GET/POST | ✅ 693, 754 | llm_agents.py:14/76 | OK |
| /api/llm/service | GET | ✅ 859, 890 | llm_models.py:233 | OK |
| /api/llm/service | POST | ❌ FE ruft nicht direkt (vermutlich globalSave) | llm_models.py:247 | UNUSED |
| /api/llm/auto_assign | POST | ❌ | llm_agents.py:? | Legacy |
| /api/llm/test_agent | POST | ❌ | llm_agents.py:? | Legacy |
| /api/llm/routing_insights | GET | ❌ | llm_agents.py:? | Legacy |

Die 3 Legacy-Endpoints (`auto_assign`, `test_agent`, `routing_insights`) sind nicht im FE verwendet — möglicherweise toter Code (eigener Audit nötig, OUT OF SCOPE für diesen Fix).

---

## Was NICHT in diesem Fix-Scope liegt

- Backend-Endpoints (alle vorhanden und korrekt)
- Routing-Logik im Backend (separater Bereich)
- Service-Cards (Web Search + TTS) — funktionieren bereits
- Keys-Paste/File-Import — funktioniert bereits
- Mode-Buttons (Auto-Routing) — funktionieren bereits
- Legacy-Endpoints (auto_assign, test_agent, routing_insights) — separater Audit
- PRE_PUSH_CHECKLIST.md / Cleanup

---

## Fix-Reihenfolge (vorgeschlagen)

1. **Agent-Model-Dropdown** — `<input>` → `<select>` mit Model-Liste pro Provider
2. **Status-Lämpchen** — Refresh-Funktion für `.llm-status-dot` schreiben
3. **Capabilities-Spalte** — Dynamisch aus `provider.caps` befüllen
4. **Caps (DB)-Spalte** — Dynamisch aus `/api/llm/agents` Response befüllen
5. **Save-Hinweis präzisieren** (optional)

Jeder Fix: ~30 Zeilen JS. Test: pytest darf nicht regressieren (LLM-Page hat aktuell KEINE pytest-Tests — nur Smoke-Test via manuelles Reload im Browser).

**Owner-Skip-Fortsetzung:** Fixes inline implementieren (siehe nächster Schritt im Plan).

---

## Fix-Status (Owner-Skip inline, 2026-06-21)

| Fix | Status | Datei:Zeile | Verifikation |
|---|---|---|---|
| 1. Model-Dropdown | ✅ DONE | `dashboard.js:433` (input→select), `:569` (populateAgentModels), `:774` (refreshProviders) | node --check OK; JS-Syntax gültig |
| 2. Status-Lämpchen | ✅ DONE | `dashboard.js:436` (data-agent-status-dot + text), `:619` (refreshAgentStatusDots), `:907` (change listener), `:774` (refreshProviders) | node --check OK; refreshAgentStatusDots grün/gelb/rot/grau |
| 3. Capabilities-Spalte | ✅ DONE | `dashboard.js:435` (data-agent-caps-col), `:602` (updateAgentCapsColumn), `:802` (loadAgents) | node --check OK; aus provider.caps befüllt |
| 4. Caps (DB)-Spalte | ✅ DONE | `dashboard.js:437` (data-agent-cap, schon vorhanden), `:817-826` (loadAgents) | node --check OK; zeigt `provider/model [caps]` |
| 5. Save-Hinweis | ⏸ Optional | nicht implementiert (out of scope für 1. Iteration) | — |

**Geänderte Dateien:**
- `src/gnom_hub/frontend/dashboard.js` (showLLMConfig + helpers) — Cache-Buster v=25 → v=26
- `src/gnom_hub/frontend/index.html` (Cache-Buster)

**Verifikation:**
- `node --check src/gnom_hub/frontend/dashboard.js` → OK (kein Output = gültig)
- `pytest` → 576 passed / 4 failed (war 565/4 — +11 weil test_godmode_adds_run_permission-Fix aus R2 jetzt greift)
- 4 pre-existing Failures unverändert (FAISS/NumPy + /private/var)
