# README-Inventar vs. Code (Abgleich 2026-07-19)

**Zweck:** Alle jemals im Repo relevanten READMEs erfassen, Kernaussagen zusammenfassen, mit aktuellem Code abgleichen.  
**Priorität User:** schnell + fehlerfrei — Doku-Drift ist Risiko, kein Feature.

---

## 1. Welche READMEs gibt es?

### Aktiv (aktuell im Tree)

| Datei | ~Zeilen | Rolle |
|-------|---------|--------|
| `README.md` | ~497 | Hauptdoku EN (Marketing + Architektur + TKG) |
| `README.de.md` | ~487 | Deutsche Parallelversion von README.md |
| `showbox/README.md` | ~22 | Kanon Showbox-Tag/Buttons |
| `showbox/flash/README.md` | ~48 | 1px Agent-Flash CSS/JS |
| `showbox/buttons/dynamic/README.md` | ~34 | Archiv dynamischer Buttons |
| `playwright-live/README.md` | ~49 | Playwright Maus-Demo (Standalone) |
| `docs/diagrams/README.md` | ~51 | Mermaid-Quellen + Palette |
| `docs/archive/2026-06-19-initial-snapshot/README.md` | ~36 | Index alter Snapshots |
| `docs/archive/2026-06-22-failed-analysis/README.md` | ~12 | Index fehlerhafte Analyse |

### Historisch (git / Backup, nicht primäre SoT)

| Quelle | Inhalt |
|--------|--------|
| Git: `README_EN.md` (früher) | Vorgänger EN |
| Git: `Gnom-Hub/README.md`, `Gnom-Hub_bak/` | alte Kopien |
| `showbox/README.md.bak`, `flash/README.md.bak` | Backups |
| Archiv 19.06. | alte ARCHITECTURE, CONTRIBUTING, Briefings … |
| `.pytest_cache/README.md` | pytest intern — irrelevant |

**SoT für Architektur (laut Archiv selbst):** `docs/ARCHITECTURE.md` + Status/Strategie-Docs — **nicht** alle README-Claims.

---

## 2. Zusammenfassung der READMEs (Inhalt)

### A) Root `README.md` / `README.de.md` (Haupt)

**Versprechen:**
- Local-first Multi-Agent, **8 Agenten**, FastAPI, Port **3002**
- Quickstart: `install.py`, `./start_gnom_hub.sh`, `curl /api/health`
- **3 Memory-Layer:** Offload+Mermaid, HOT/WARM/COLD SQLite, **TKG** (Kuzu/InMemory)
- **6 SQLite-DBs** unter `~/.gnom-hub-*/data/`
- LLM: MiniMax → OpenAI-Compat → DeepSeek → Ollama + Desktop Key-Reconcile
- **SoulAG** als Orchestrator im Roster
- ~30 API-Router, „220+ Endpoints“, Tests „496 CI / 730 full“
- Offload `[OFFLOAD_RECALL:…]`, FAISS/TF-IDF
- TKG ehrlich: Auto-Recall im Agent-Loop **TODO**, Token-Economy **nicht gemessen**

### B) Showbox-READMEs

- Tag-Syntax, Buttons nur in `buttons[]`, Presets, Tier-Hierarchie
- Flash: 8 Agent-Farben, MutationObserver
- Dynamic-Buttons: Naming + Archiv

### C) playwright-live

- Standalone npm/Playwright-Mausdemos — **nicht** Kern des Hubs

### D) docs/diagrams

- Mermaid-Quellen, Palette Paper/Forest/Copper — stimmt zu den Diagrammen im Root-README

### E) Archive-READMEs

- 19.06.-Snapshot **veraltet**
- 22.06.-Analyse **verworfen** (9 Faktenfehler) → SoT ARCHITECTURE.md

---

## 3. Abgleich README ↔ Code (Stand Code 2026-07)

| Claim (README) | Code-Realität | Urteil |
|----------------|---------------|--------|
| 8 Agenten: Soul, General, Watchdog, Security, Coder, Writer, Editor, Researcher | `agent_definitions` / Process-Manager | **OK** |
| Default-Chat-Orchestrator = **SoulAG** (Roster-Text) | `chat_legacy`: Default → **GeneralAG** | **DRIFT** |
| Quickstart `start_gnom_hub.sh` + Port 3002 | Scripts existieren, Default 3002 | **OK** |
| Health `{"status":"ok"}` | oft `ok` + `agents{…}` Objekt | **OK** (etwas reicher) |
| ~30 API-Router | `endpoints/*.py` ≈ 30 | **OK** |
| „220+ Endpoints“ | ~160 `@router.get/post/…` | **ÜBERTRIEBEN** (~160) |
| 6 SQLite-DBs (gnomhub, passive, soul_passive, context, coordination, rules) | Dateien unter `~/.gnom-hub/data/` vorhanden | **OK** (plus Kuzu, emb_cache, …) |
| DB-Pfad `~/.gnom-hub-3003/data/` im Text | Default eher `~/.gnom-hub` / Port-Isolation | **DRIFT** (Beispiel-Port) |
| LLM-Kette MiniMax → … → Ollama | Router: **konfigurierbar**; Default-Config oft **openrouter/free**; MiniMax nur wenn so gesetzt | **DRIFT** (Kette als fest behauptet) |
| Key-Reconcile Desktop `api_keys.txt` | `key_reconciler` vorhanden | **OK** |
| Offload + OFFLOAD_RECALL | `memory/offload`, `action_handlers` | **OK** (Code da) |
| TKG Code + Tests + Benchmark-Scripts | `memory_tkg/`, tests, scripts | **OK** |
| TKG auto-recall im Agent-Loop | README selbst: TODO; Code: kein `engine.query` in agent/soul Loop | **OK ehrlich / Lücke bleibt** |
| Embeddings FAISS + TF-IDF Fallback | vorhanden (optional deps) | **OK** |
| Python 3.10+ Badge | `requires-python >=3.9` | **leichter DRIFT** |
| Tests 496 CI / 730 full (2026-07-11) | CI ~**537** passed (Juli 2026, ignore-list) | **VERALTET** |
| Module-Count 207 / 47 test files | ca. 225 py modules, viele tests | **ungefähr** |
| HTTP/WS im Architektur-ASCII | praktisch **HTTP**; kein zentrales WebSocket-Chat | **DRIFT** (WS übertrieben) |
| install.py | vorhanden | **OK** |
| Showbox-Tags | Code + Frontend verarbeiten SHOWBOX / → Showbox | **OK** (mehrere Formate im Code) |
| showbox/flash Integration | Dateien da; Haupt-UI nutzt modular-showbox | **teilweise** (Doku vs. Integrationstiefe) |
| playwright-live | Standalone-Demos | **OK**, nicht Hub-Kern |
| „zero cloud dependency“ im Kern | LLM-Provider oft **Cloud** (OpenRouter/MiniMax) | **MARKETING** — lokal ist Host, nicht zwingend lokal LLM |

---

## 4. Gesamturteil

### Stimmt grob
- Local-first **Host**, 8 Agenten, FastAPI, Start/Stop, Showbox-Konzept, Memory-Schichten **im Code**, TKG-Modul, 6+ DB-Dateien, Offload-Mechanik, Diagramme, ehrliche TKG-Lücken im README selbst.

### Wichtigste Doku-Fehler (für „schnell & fehlerfrei“ relevant)
1. **Default-Chat = GeneralAG**, nicht SoulAG (README-Roster täuscht).  
2. **LLM-Default** ist nicht „MiniMax-first-Kette“, sondern **Routing/UI/DB** (oft openrouter free).  
3. **Testzahlen** und Endpoint-Counts veraltet.  
4. **WS** und **„zero cloud“** überzeichnen.  
5. **DB-Pfad-Beispiel** (`-3003`) kann verwirren.

### Archiv-READMEs
- Bewusst **historisch** — nicht gegen aktuellen Code lesen, außer mit Banner „veraltet“.

### Relation zu User-Priorität
- Die READMEs beschreiben **viele Features** (Memory/TKG/Offload) korrekt als **Code-Module**.  
- Sie behaupten teilweise **Betriebs- und Routing-Wahrheiten**, die **nicht mehr** stimmen.  
- Für Stabilität zählt Code + `ARCHITECTURE`/Status-Docs; Root-README ist **teilweise Marketing + Memory-Doku**, nicht Betriebs-SoT.

---

## 5. Empfehlung (ohne neue Features)

1. Root-README: **eine Zeile Default-Routing GeneralAG**; SoulAG = Beobachter/Memory.  
2. LLM-Abschnitt: „folgt `config/routing.txt` + UI“ — keine feste MiniMax-Kette.  
3. Test-Badge/Zahlen aktualisieren oder „siehe `local_ci.sh`“.  
4. „220+ Endpoints“ → „~160“ oder weglassen.  
5. HTTP/WS → nur HTTP (SSE optional).  
6. Archiv-READMEs unangetastet lassen.

---

*Erstellt 2026-07-19 durch Abgleich der README-Dateien mit `src/` und Live-Health.*
