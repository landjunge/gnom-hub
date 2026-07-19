# README-Inventar vs. Code (Abgleich 2026-07-19)

**Zweck:** Alle READMEs — lokal **und auf GitHub** (Branches + Git-Historie) — erfassen, zusammenfassen, mit Code abgleichen.  
**Quellen:** `origin/master`, `origin/main`, `git log --all`, GitHub Trees API.  
**Priorität User:** schnell + fehlerfrei — Doku-Drift ist Risiko, kein Feature.

---

## 0. GitHub-Stand (Remote)

### `origin/master` (aktuell, Default)

10 README-Pfade:

- `README.md`, `README.de.md`
- `docs/README_CODE_ALIGNMENT_2026-07.md`
- `docs/diagrams/README.md`
- `docs/archive/2026-06-19-initial-snapshot/README.md`
- `docs/archive/2026-06-22-failed-analysis/README.md`
- `playwright-live/README.md`
- `showbox/README.md`, `showbox/flash/README.md`, `showbox/buttons/dynamic/README.md`

### `origin/main` (älterer/paralleler Branch auf GitHub)

- `README.md` (~633 Zeilen) — **ANDERE** Marketing-README als master (Forge/Swarm/„Sandboxed Workers“, 681 Tests, …)
- `README.de.md`
- Showbox + playwright + Archive — **ohne** `docs/diagrams/README.md` und ohne dieses Alignment-Doc

### `origin/gh-pages`

- **kein** README (nur GitHub-Pages HTML/Screenshots)

### Historisch jemals im Git (heute gelöscht / verschoben)

| Pfad | Letzter Commit | Kurzinhalt |
|------|----------------|------------|
| `README_EN.md` | 2026-05-24 | EN-Marketing, „40-Line Rule“, 8 Agents, ~1800 LOC Story |
| `Gnom-Hub/README.md` | 2026-05-14 | DE Mini-Orchestrator, `pip install -e .`, `gnom-hub` |
| `Gnom-Hub_bak/README.md` | 2026-05-14 | „Cortex“ Install-Notiz |
| `gnom_workspace/readme.md` | 2026-05-16 | **To-Do List App** (User-Workspace-Demo, nicht Hub) |
| `src/mc707/README.md` | 2026-06-24 | Roland MC-707 MIDI-Lib (später eigenes Repo) |
| `showbox/*.bak` | 2026-06-28 | Backups der Showbox-READMEs |

---

## 1. Welche READMEs gibt es? (aktiv)

### Aktiv auf `master` (SoT-Branch)

| Datei | ~Zeilen | Rolle |
|-------|---------|--------|
| `README.md` | ~497 | Hauptdoku EN (Memory/TKG-lastig) |
| `README.de.md` | ~487 | DE-Parallelversion |
| `showbox/README.md` | ~22 | Kanon Showbox-Tag/Buttons |
| `showbox/flash/README.md` | ~48 | 1px Agent-Flash |
| `showbox/buttons/dynamic/README.md` | ~34 | Dynamic Buttons Archiv |
| `playwright-live/README.md` | ~49 | Playwright Maus-Demo |
| `docs/diagrams/README.md` | ~51 | Mermaid-Quellen |
| `docs/archive/.../README.md` | Index | Historische Snapshots |
| `docs/README_CODE_ALIGNMENT_2026-07.md` | dieses Doc | Abgleich |

### Branch `main` (GitHub) — extra beachten

| Claim auf `main` README | vs. Code / master |
|-------------------------|-------------------|
| „Worker Agents (Sandboxed)“ | **Marketing** — keine Sandbox-Roadmap (User-Verbot) |
| 681 Tests Badge | veraltet |
| Forge/Immutable Products Vision | Vision, nicht Betriebs-SoT |
| ZWC / Steganography als Feature | Code hat ZWC-Reste — nicht primärer Stabilitätsfokus |
| „44 Providers“ | Registry existiert; nicht = 44 live verdrahtet |

**Wichtig:** Wer GitHub öffnet und auf **`main`** schaut, sieht **andere** Story als auf **`master`**.

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
| TKG auto-recall im Agent-Loop | S5: `builder._inject_tkg_recall` + `ask_router` übergibt User-Message; Flags `TKG_AUTO_*` | **OK verdrahtet** |
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
