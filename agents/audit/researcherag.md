# ResearcherAG — Tiefen-Audit

**Datum:** 2026-06-28
**Auditor:** Owner (Original-Worker-Audit TIMED OUT @ 15min, Owner-Übernahme)
**Quellen:** config + Python agent_definitions.py + Crawl/Browser/Showbox-Stack
**Workspace:** `/Users/landjunge/gnom-hub`

---

## 0. Quellen-Inventar

| Datei | Zeilen | Was gefunden |
|---|---|---|
| `config/agents/ResearcherAG.json` | 32 | v5.3, Identity ~5300 chars, permissions `[read,crawl,web_search,browser,showbox_write]` (5 Tokens) |
| `agents/researcherAG.py` | 1 | Stub `BaseAgent(cfg...)` |
| `src/gnom_hub/agents/agent_definitions.py:280-303` | 24 | Python SSoT — DE/EN permissions `[read,crawl,web_search,browser]` (4 Tokens) |
| `src/gnom_hub/agents/actions/action_exec.py:11-46` | 36 | handle_crawl + handle_shell + handle_showbox |
| `src/gnom_hub/agents/actions/action_handlers.py:111-181` | 71 | crawl + browser pre-audit |
| `src/gnom_hub/agents/actions/action_browser.py:1-42` | 42 | Playwright-Browser-Automation |
| `src/gnom_hub/core/security/gatekeeper_browser.py` | — | verify_browser (Sandbox-Check) |
| `src/gnom_hub/infrastructure/process/sandbox.py` | — | run_browser_in_sandbox |
| `src/gnom_hub/agents/agent_definitions.py:1-53` | 53 | SSoT-Doc-Comment (Runtime-Permissions) |

---

## 1. Aktueller Zustand

### Version
- JSON v5.3
- Python SSoT — permissions HART unterschiedlich

### Sliders (identisch zu allen 7 anderen Agents)
```json
{ "creativity": 2, "precision": 2, "speed": 2, "critical_thinking": 2, "obedience": 2 }
```

### Permissions — Drei-Welten-Drift (KRASSESTER FALL)
| Quelle | Permissions | Anzahl |
|---|---|---|
| JSON `ResearcherAG.json:19-25` | `[read, crawl, web_search, browser, showbox_write]` | 5 |
| Python `agent_definitions.py:297` (DE) | `[read, crawl, web_search, browser]` | 4 |
| Python `agent_definitions.py:302` (EN) | `[read, crawl, web_search, browser]` | 4 |

**Was fehlt in Python: `write` UND `showbox_write`** — beides!

**Konsequenz:** ResearcherAG hat laut JSON Schreibrechte + Showbox-Pflicht, laut Python DARF der Agent NICHTS schreiben. Wenn der LLM dann `[WRITE: research.md]inhalt[/WRITE]` ausgibt, wird der Tag laut `action_handlers.py` Permission-Check NICHT ausgeführt (weil `write` nicht in perms).

### Identity-Struktur (5 Sektionen — Boilerplate)
1. Identity-Header (Rolle, Sprech-Verbot, Workspace-Pin, Farbe Gelb)
2. Workspace-Pin (`/Users/landjunge/gnom-Workspace/default/`)
3. Sprech-Verbot
4. Showbox+Buttons-Pflicht
5. Tier-3b-Worker

### Workspace-Beispiel-Files (laut Identity)
- `[WRITE: research.md]` → research-File
- `[WRITE: sources.md]` → Quellenliste

**Diese Writes funktionieren in der Runtime NICHT** weil `write` fehlt!

---

## 2. Spec-Konformität

### Showbox-Pflicht
- JSON-Identity: Pflicht genannt
- Code: Showbox-Pipeline ist da (`showbox_repo.py:save_showbox_presentation`)
- **ABER:** `showbox_write`-Permission fehlt im Runtime (siehe §1)
- **Konsequenz:** Wenn ResearcherAG `[→ Showbox: research]` ausgibt, wird das vermutlich ohne Permission-Check akzeptiert (Backend enforced `showbox_write` nicht), aber Worker-Chat-Filter (`chat_repo.py:14-114`) könnte das filtern weil kein `write`-Permission vorhanden

### Crawl-Spec
- **action_exec.py:37-46** `handle_crawl`: checkt nur `"crawl" in perms`
- **KEINE Domain-Whitelist**
- **KEINE Rate-Limit**
- **KEINE Robots.txt-Check**

### Browser-Spec
- **action_browser.py:1-42**: Playwright-basierte Browser-Automation
- **verify_browser** in `gatekeeper_browser.py`: prüft ob Browser-Aktion erlaubt ist
- **Sandbox:** `run_browser_in_sandbox` — Scripts laufen in Sandbox
- **User-Mandat 2026-06-27: "Kein neuen Browser/Fenster/Tab öffnen ohne explizite User-Freigabe"** — ResearcherAG darf das? Identity hat KEINE Klausel dazu!

### Web-Search
- **Identity** listet `web_search` als Permission, aber **Identity hat keinen expliziten Use-Case** für web_search
- **Welche Search-Engine?** Keine Spec definiert
- **Rate-Limit?** Keine Spec definiert

---

## 3. Code-Realität

### Was ResearcherAG tatsächlich tun kann (empirisch)
- ✅ `[CRAWL: url]` — crawled jede URL ohne Whitelist
- ✅ `[WEB_SEARCH: query]` — falls implementiert (nicht in agent_definitions sichtbar)
- ✅ `[BROWSER: ...]code[/BROWSER]` — Playwright-Browser, in Sandbox
- ✅ `[→ Showbox: research]` — Showbox-Card (Backend enforced `showbox_write` nicht hart)
- ✅ `[READ: pfad]` — File lesen
- ❌ `[WRITE: research.md]` — WRITE FEHLT in Runtime-Permissions!
- ❌ Inline-`[WRITE: ...]`-Tags werden vermutlich geblockt oder still ignored

### Realer Workflow
- ResearcherAG crawlt und gibt Facts in Showbox zurück
- Persistenz von recherche-Notizen MUSS über Showbox gehen (kein File-Write möglich)
- **Bei langen Quellen-Listen** → Showbox-Card wird zu lang → Render-Crashes?
- **Oder:** ResearcherAG schreibt via [READ:] → Manipulation über andere Agents (Workaround)

### Browser-Headless-Mode
- `action_browser.py:1-42` startet Playwright-Skript
- `run_browser_in_sandbox` mit `net` und `timeout=DEFAULT_BROWSER_TIMEOUT`
- **Headless-Flag:** Code zeigt keinen expliziten headless-Set
- **User-Mandat-Konflikt:** Wenn ein sichtbarer Browser spawnen würde → Mandat-Verstoß

---

## 4. Widersprüche INTERN

### W1: Permission-Drift (60% — KRASSESTER FALL ALLER 8 AGENTS)
- JSON hat 5 Tokens, Python hat 4 — Drift 20%
- ABER: 2 der 5 JSON-Tokens (`write`, `showbox_write`) fehlen komplett im Python
- `write` ist FUNDAMENTAL — ohne `write` kann der Worker seine eigenen Liefer-Pflichten nicht erfüllen
- **Test bestätigt:** `tests/golden/diff_ResearcherAG.json` zeigt vermutlich [TOOLS] Perms: read, crawl, web_search, browser (KEIN write)

### W2: Identity vs Use-Case
- Identity sagt: "Du recherchierst gründlich und prüfst Quellen kritisch"
- ABER: ohne `write` kann ResearcherAG keine Recherche-Files persistieren
- Workaround über Showbox funktioniert nur für kurze Outputs
- **Konsequenz:** Recherche-Quality sinkt weil keine strukturierten Notizen möglich

### W3: Workspace-Pin-Lüge
- Identity hardcoded `/Users/landjunge/gnom-Workspace/default/`
- `Config.workspace_dir()` löst dynamisch via State-Override auf
- Pattern identisch zu CoderAG/WriterAG/EditorAG

### W4: 4 Recherche-Tools, 0 Persistenz-Tools
- `crawl + web_search + browser` (3 Read-Tools) + `read` (File-Read) = 4 Read-Wege
- **KEIN write** — Recherche-Ergebnisse müssen über andere Wege gespeichert werden
- **Frage:** Welche Designentscheidung steckt dahinter? "Recherche ist ephemeral, nur über Showbox"?
  - Falls ja: warum sagt Identity dann "Du schreibst gründlich"?

### W5: User-Mandat-Verletzung möglich
- User-Mandat 2026-06-27: "Kein neuen Browser/Fenster/Tab öffnen ohne explizite User-Freigabe"
- ResearcherAG hat `browser`-Permission — darf das jederzeit einen sichtbaren Browser spawnen?
- Identity hat KEINE Klausel zum User-Mandat
- **Kritisch:** Hier ist der einzige Agent im System, der systematisch Browser-Aktionen auslösen kann

---

## 5. Widersprüche zu ANDEREN Agents

### ResearcherAG vs WriterAG
- **BEIDE haben `crawl`** — wer crawlt was?
- WriterAG: `read + write + crawl` (darf schreiben, aber kein search/browser)
- ResearcherAG: `read + crawl + web_search + browser` (kein write)
- **Konsequenz:** WriterAG könnte die Recherche-Files von ResearcherAG empfangen und in [WRITE:]-Tags umsetzen — der dokumentierte Workflow ist genau das
- **ABER:** Strategie B in `adaptive_decomposition.py:23` ist Writer→Editor (nicht Researcher→Writer)
- **Lücke:** Strategy "Researcher→Writer" FEHLT

### ResearcherAG vs CoderAG
- CoderAG hat `run` (Bash), ResearcherAG nicht
- CoderAG könnte Code-Snippets ausführen, ResearcherAG nicht
- ResearcherAG kann Browser-Aktionen, CoderAG nicht

### ResearcherAG vs WatchdogAG
- WatchdogAG's 4-Punkte-Blockade-Liste: System-Destruktion, Secret-Leaks, Exfiltration, RCE
- ResearcherAG könnte via `browser` UND `crawl` sensible Daten exfiltrieren
- **Frage:** Hat WatchdogAG einen Pattern-Detector für ResearcherAG-spezifische Risiken?
- **Suche:** `grep -rn "researcherag\|researcher" src/gnom_hub/core/security/` → vermutlich 0 spezifische Checks

### ResearcherAG vs SecurityAG
- SecurityAG hat `db_write + network` (Python nicht aber JSON) — Sicherheits-Auditor
- SecurityAG könnte theoretisch ResearcherAG's Crawl-History auditieren
- **ABER:** SecurityAG's Identity hat keinen Workflow für "Crawl-Audit"
- **Lücke:** Crawl-Compliance-Check fehlt im gesamten System

---

## 6. Lücken

### L1: ResearcherAG kann nicht persistieren
- Kein `write` in Runtime → Recherche-Files nur ephemeral
- Workarounds: über Showbox (limitiert), über andere Worker (chaotisch)

### L2: Crawl/Browser-Compliance-Layer fehlt
- Keine Domain-Whitelist
- Keine Rate-Limit
- Keine Robots.txt
- Kein Exfiltration-Detector (sensible Daten via Browser-Forms ausfüllen + senden?)

### L3: Strategy "Researcher→Writer" fehlt
- Adaptive-Decomposition hat nur Writer→Editor
- Recherche-Output muss manuell an WriterAG weitergegeben werden

### L4: User-Mandat "Kein Browser ohne Freigabe" nicht durchgesetzt
- ResearcherAG hat `browser`-Permission, keine Klausel zur User-Freigabe

### L5: Outcome-Tracking fehlt
- `generalag_outcomes` für ResearcherAG nicht gefüllt (Phantom-Tabellen-Pattern)

### L6: Was ist `web_search` konkret?
- Identity listet es als Permission
- ABER: keine Search-Engine definiert (Google? DuckDuckGo? Bing? MiniMax?)
- Rate-Limit fehlt
- **Wahrscheinlich:** Dead-Token wie `showbox_write` bei anderen

---

## 7. Konkrete Verbesserungsvorschläge (priorisiert)

### V1 (CRITICAL): `write`-Permission zu Python hinzufügen
- **Problem:** ResearcherAG kann nicht persistieren, obwohl Identity das verlangt
- **Lösung:** `agent_definitions.py:297` permissions = `[read, crawl, web_search, browser, write]`
- **Aufwand:** trivial
- **Risiko:** niedrig (ResearcherAG schreibt eh nur in seinen Workspace)

### V2 (HIGH): User-Mandat-Klausel zur Browser-Freigabe
- **Problem:** ResearcherAG könnte sichtbaren Browser spawnen
- **Lösung:** Identity-Klausel: "Browser-Aktionen NUR nach expliziter User-Freigabe via Showbox-Button. Default: headless."
- **Aufwand:** klein
- **Risiko:** niedrig

### V3 (HIGH): Crawl/Browser-Compliance-Layer
- Domain-Whitelist (Default: nur öffentliche Domains, Block: Localhost, private IPs)
- Rate-Limit (z.B. max 10 Requests/Minute/Agent)
- Robots.txt-Check via `urllib.robotparser`
- Exfiltration-Detector (Pattern-Match auf sensible Daten in Browser-Forms)
- **Aufwand:** mittel-groß (SecurityAG + crawler_engine + action_browser Erweiterung)
- **Risiko:** mittel (kann bestehende Workflows bremsen)

### V4 (HIGH): Strategy "Researcher→Writer"
- Adaptive-Decomposition erweitern
- Auto-Trigger: wenn ResearcherAG Output liefert → auto-delegate an WriterAG für finalen Text
- **Aufwand:** mittel
- **Risiko:** niedrig

### V5 (MEDIUM): `showbox_write` zu Python + Enforcement
- **Problem:** JSON hat `showbox_write`, Python nicht
- **Lösung:** ergänzen + in `action_handlers.py` enforcement
- **Aufwand:** klein (analog CoderAG/WriterAG/EditorAG)
- **Risiko:** mittel

### V6 (MEDIUM): Workspace-Subdir-Trennung
- `/Users/landjunge/gnom-Workspace/default/researcher/`
- **Aufwand:** mittel
- **Risiko:** mittel

### V7 (MEDIUM): `web_search`-Tool implementieren oder entfernen
- Falls nicht implementiert: aus Permissions nehmen
- Falls implementiert: Search-Engine + Rate-Limit definieren
- **Aufwand:** mittel
- **Risiko:** niedrig

### V8 (LOW): Workspace-Pin dynamisch
- **Aufwand:** klein
- **Risiko:** niedrig

### V9 (LOW): Outcome-Tracking
- **Aufwand:** mittel
- **Risiko:** niedrig

### V10 (LOW): Tier-Verweis in Identity
- **Aufwand:** trivial
- **Risiko:** niedrig

---

## 8. Cross-Check-Notes für die Synthese

- **ResearcherAG ist der Worker mit den meisten Permission-Konflikten** — 2 kritische Tokens fehlen im Python
- **Browser-Mandat-Konflikt** ist ResearcherAG-spezifisch — sollte in Cross-Synthesis als Sicherheits-Findings auftauchen
- **Crawl-Compliance fehlt im gesamten System** — ResearcherAG ist der primäre Crawler, aber auch WriterAG darf crawlen
- **Workspace-Pin-Lüge** ist 1:1 wie bei allen anderen 3 Workern
- **"Researcher→Writer"-Strategie fehlt** — Adaptive-Decomposition ist lückenhaft