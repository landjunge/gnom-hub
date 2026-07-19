# Gnom-Hub — Technischer Status Report

**Stand:** 2026-07-19  
**Version:** 1.2.0 (`pyproject.toml`)  
**Scope:** Live-Code unter `src/gnom_hub/`, Agent-Prozesse, SQLite, Frontend, LLM-Routing  
**Codebasis:** ~30 300 LOC Python (225 Module) + ~12 700 LOC Frontend-JS/HTML  

---

## 1. Executive Summary

Gnom-Hub ist ein **lokal laufender Multi-Agent-Orchestrator**: ein FastAPI-Hub, acht Agent-Subprozesse, eine gemeinsame SQLite-Datenbank und ein monolithes Web-UI. Das Produkt ist **funktionsreich und aktiv** (Chat, Showbox, Permissions, Workflows, OpenRouter/MiniMax/Ollama, Memory/TKG).

**Aktueller Betriebszustand (Messung 2026-07-19):**

| Metrik | Wert |
|--------|------|
| Health API | `ok`, 8/8 healthy (nach Stabilitäts-Fixes) |
| DB | `~/.gnom-hub/data/gnomhub.db` ≈ **66 MB** |
| Queue | u. a. pending/processing unter Last (volatile) |
| CI (pre-push) | ~515 Tests grün; **21 Testmodule bewusst ignoriert** |

**Kernurteil:**  
Die Architektur ist **ambitioniert und erklärbar**, aber der **Betriebspfad ist überlastet durch Multi-Writer-SQLite + Prozess-Chaos + synchrone Chat-Pipeline**. In den letzten Tagen wurden schwere Symptome (Chat „Hub unreachable“, Zombie-Agenten, Doppel-Spawn) **teilweise behoben**. Die **strukturelle Ursache** (eine DB für Hub + 8 Writer + Heartbeats + Queue-Claim) bleibt **P0**.

---

## 2. Systemübersicht (Ist-Architektur)

```
┌─────────────┐     POST /api/chat      ┌──────────────────────┐
│  Browser UI │ ───────────────────────►│  Hub (uvicorn/FastAPI)│
│  static JS  │ ◄── poll chat/showbox ──│  Port 3002            │
└─────────────┘                         └──────────┬───────────┘
                                                   │ SQLite WAL
                                                   │ gnomhub.db
                      ┌────────────────────────────┼────────────────────────────┐
                      │                            │                            │
               ┌──────▼──────┐              ┌──────▼──────┐              ┌──────▼──────┐
               │  GeneralAG  │   … 8× …     │   CoderAG   │              │   SoulAG    │
               │ run_agent   │              │ run_agent   │              │ run_agent   │
               └──────┬──────┘              └──────┬──────┘              └──────┬──────┘
                      │ ask_router                 │                              │
                      ▼                            ▼                              ▼
               MiniMax / OpenRouter free / Ollama lokal
```

| Schicht | Pfad | Rolle |
|---------|------|--------|
| API | `api/app.py`, `api/endpoints/*` | Chat, Registry, Showbox, LLM-Keys, Health |
| Chat-Pfad | `api/endpoints/chat_legacy.py` | **Produktiver** `POST /api/chat` |
| Queue | `agents/swarm/swarm_comms.py` | `agent_messages`, `BEGIN IMMEDIATE` Claim |
| Agent-Loop | `agents/agent_base.py` | Register → HB → fetch → LLM → Actions → POST Chat → Ack |
| Prozess | `infrastructure/process/process_manager.py` | Spawn/Kill/Restart, PID-Dateien |
| LLM | `infrastructure/router/*` | Provider-Kette, Free-Model-Rotation |
| Security | `core/security/*`, `db/permissions_repo.py` | Path-Sandbox, Grants, Injection |
| UI | `frontend/*.js` | Dashboard, Chat, Showbox (ohne Bundler) |
| Memory | `memory/`, `memory_tkg/` | FAISS optional, Kuzu/TKG optional |

**Datenfluss Chat (vereinfacht):**  
User → `POST /api/chat` → Injection-Check → `add_chat_message` → `dispatch` → `INSERT agent_messages` → Agent claimt mit `BEGIN IMMEDIATE` → `ask_router` → Actions → Agent postet Antwort wieder an `/api/chat` → Showbox-Extraktion → Frontend pollt.

**Default-Routing:** User ohne `@target` → **GeneralAG** (nicht SoulAG; `docs/ARCHITECTURE.md` ist hier veraltet).

---

## 3. Was kürzlich stabilisiert wurde

| Fix | Commit / Ort | Effekt |
|-----|--------------|--------|
| Doppel-Agenten (16 statt 8) | `7989023`, `process_manager._cmdline_is_agent` | Watchdog erkennt `run_agent` korrekt |
| Chat-Timeout / Thread-Starvation | `b050bdf`, `d4bbeab`, `GNOM_DB_BUSY_MS=800` | Fail-fast statt 60 s Busy-Wait |
| Soft Register/Heartbeat | `registry.py` | Agent-Loop stirbt nicht an DB-Lock |
| Heartbeat-Throttle | 1×/10 s statt ~2/s × 8 | Deutlich weniger Write-Storm |
| Queue-Preserve bei Restart | `processing → pending` | Jobs verschwinden nicht still |
| Silent Failures sichtbar | System-Chat bei leerem Dispatch / Router-Fehler | Weniger „stiller“ Schwarm |
| Path-Grants | Security außerhalb Workspace | Kein truthy-perms-Godmode mehr |

**Wichtig:** Das sind **Symptom- und Betriebsfixes**. Sie machen den Hub nutzbar, ersetzen aber keine Architektur-Migration.

---

## 4. Problemregister (mit Ursachen & Kritikalität)

### Skala

| Stufe | Bedeutung |
|-------|-----------|
| **P0** | Outage, Daten-/Job-Verlust, Chat unbrauchbar unter Last |
| **P1** | Hohes Zuverlässigkeitsrisiko, häufige Degradation |
| **P2** | Materieller Design-Debt, operativer Aufwand, Security-Rest |
| **P3** | Maintainability, Größe, Doku-Drift |

---

### P0 — Kritisch

#### P0.1 Multi-Writer-SQLite als Single Point of Contention

| | |
|--|--|
| **Symptom** | `database is locked`, Chat speichert nicht / Dispatch scheitert, Health flackert |
| **Ursache** | Eine Datei-DB für Hub-API + 8 Agenten + Heartbeats + Queue-Claims (`BEGIN IMMEDIATE`) + Audit/EO/Soul |
| **Evidenz** | `db/connection.py` (`busy_timeout` 800 ms); `swarm_comms.fetch_next_message`; Live-Logs |
| **Warum kritisch** | Jeder erfolgreiche Agent-Zyklus erzeugt konkurrierende Writes. Fail-fast rettet den Thread-Pool, **verliert aber Dispatch-Zuverlässigkeit**. |
| **Mitigation heute** | Kurze Timeouts, Soft-Fail, weniger Heartbeats — **kein echtes Write-Serialisieren** |

#### P0.2 Connection-Leaks (`with get_db_connection()` ohne Close)

| | |
|--|--|
| **Symptom** | Steigende FD-Anzahl auf `gnomhub.db`, anhaltende Locks trotz „leerer“ Last |
| **Ursache** | `sqlite3.Connection` als Context Manager **committet, schließt aber nicht**. Nur `get_db_conn()` ist leak-safe. |
| **Evidenz** | `connection.py` Docstring; Fehlmuster u. a. in OOP-`chat_repo`, `agent_health`, `schema.init`, Worker-Watch |
| **Warum kritisch** | Offene Connections halten WAL/SHM-State und verstärken P0.1 |

#### P0.3 LLM-Fehler werden als „done“ geackt

| | |
|--|--|
| **Symptom** | System-Warnung im Chat, Job verschwindet aus Queue, keine automatische Wiederholung |
| **Ursache** | Bei leerem Content / `[ROUTER-FEHLER]` → System-Post, dann trotzdem `ack_message` → `done` |
| **Evidenz** | `agent_base.py` (Erfolgs-Ack-Pfad auch bei `job_ok=False`) |
| **Warum kritisch** | Transient API-Blips (OpenRouter 429, leere Free-Models) = **permanenter Job-Verlust** |

---

### P1 — Hoch

#### P1.1 Cross-Process-Notify ist wirkungslos

| | |
|--|--|
| **Symptom** | Bis zu mehreren Sekunden Latenz bis Agent die Message sieht |
| **Ursache** | `threading.Event` in `swarm_comms` ist **prozesslokal**; Agenten laufen in eigenen Prozessen |
| **Evidenz** | `notify_agent()` + `fetch_next_message` Poll/Timeout |
| **Wirkung** | Unnötige DB-Polls, schlechtere UX, mehr Lock-Druck |

#### P1.2 `processing_since IS NULL` = sofort „stuck“

| | |
|--|--|
| **Symptom** | Queue-Thrashing, wiederholte Requeues |
| **Ursache** | Recovery-SQL: `processing AND (processing_since <= ? OR processing_since IS NULL)` |
| **Evidenz** | `swarm_comms.recover_stuck_messages` |
| **Wirkung** | Alte/inkonsistente Rows werden aggressiv angefasst |

#### P1.3 Prozess-Lifecycle-Races (residual)

| | |
|--|--|
| **Symptom** | Historisch: 16 Agenten, Zombies, PID-Datei-Spam |
| **Ursache** | Watchdog erkannte `run_agent`-Cmdline falsch → Restart via `agents.*AG` **ohne** Kill der Originale |
| **Status** | **Größtenteils gefixt** (`_cmdline_is_agent`, einheitlicher Restart) |
| **Residual** | Race bei parallelem Start/Watchdog; offene Log-Handles bei Popen |

#### P1.4 Free-LLM-Kaskade fragil

| | |
|--|--|
| **Symptom** | Lange Latenzen, leere Antworten, „Alle Gleise offline“ |
| **Ursache** | OpenRouter free (429/Rotation) → Ollama nur wenn lokal da; MiniMax optional |
| **Evidenz** | `openrouter_free.py`, `router.py` Resolve-Kette |
| **Wirkung** | Zusammen mit P0.3: schlechte UX + stille Job-Verluste |

#### P1.5 Heartbeat überschreibt Status

| | |
|--|--|
| **Symptom** | `busy` vs `online` inkonsistent |
| **Ursache** | Heartbeat setzt immer `status='online'` |
| **Wirkung** | Health/UI und Routing-Logik rauschen |

---

### P2 — Mittel

#### P2.1 Queue-Design stark, Enforcement weich

- **Stärken:** Prioritäten, Depth-Cap, DLQ, Dependency-Timeout, Restart-Requeue  
- **Schwächen:** `MAX_CONCURRENT` soft (loggt, blockt nicht hart); Offline-Mentions verworfen; Dual-Init Schema/Migrations  
- **Evidenz:** `swarm_comms.py`, `schema.py`

#### P2.2 Frontend-Megamonolith

| Datei | ~LOC |
|-------|------|
| `dashboard.js` | 4200+ |
| `index.html` | 3000+ |
| `chat.js` | 1280 |
| `showbox-module.js` | 1180 |
| `core.js` | 1110 |

- Kein Bundler/TypeScript  
- Gemischte `api()`- und rohe `fetch('/api/...')`-Pfade  
- Verdacht **Doppel-Prefix** `/api/api/workspace/...` in `workspace.js`  
- Ein Syntaxfehler legt große UI-Flächen lahm  

#### P2.3 Dualer Chat-Stack

- Produktiv: `chat_legacy.py` → `/api/chat`  
- Alternativ: `chat.py` / Orchestrator — **nicht** im Haupt-Router verdrahtet  
- Risiko: Refactors testen den toten Pfad  

#### P2.4 Security: besser, aber nicht multi-user-ready

- Path-Validator + Grants: spürbar gehärtet  
- Gatekeeper-Blockaden: **bewusst deaktiviert** (2026-07)  
- Admin-Auth / Workspace-Run: laut Projekt-Historie noch schwache Flächen  
- `granted_to='all'` und Godmode-Flag bleiben mächtig  

#### P2.5 Inkonsistente DB-Policies

- Nebendatenbanken (Memory, KPI, Passive, Coordination) mit eigenen Timeouts (bis 30 s)  
- Unterlaufen die Fail-fast-Politik des Hubs  

#### P2.6 Test-Ignorierliste

- **21+** Module in `pyproject.toml`/`local_ci` ignoriert (Browser, Stress, FAISS, E2E, Migrations, …)  
- CI ist grün, deckt aber **nicht** den echten Chat-E2E- oder Browser-Pfad ab  

---

### P3 — Niedrig / Maintainability

| Thema | Detail |
|-------|--------|
| Dateigröße Backend | `swarm_comms.py` ~930, `memory_layers.py` ~750, `agent_base.py` ~520 |
| Doku-Drift | `ARCHITECTURE.md` (SoulAG-Default) ≠ Code (GeneralAG) |
| `Await`-Wrapper | Sync/Async-Hybrid in Repos unklar |
| Doppelte DB-Dateinamen | `gnomhub.db` vs historische `gnom_hub.db` |
| Log-Rotation | schwer lesbar im Process-Manager |

---

## 5. Kritikalitäts-Matrix (Überblick)

| ID | Problem | Impact | Likelihood | Priorität |
|----|---------|--------|------------|-----------|
| P0.1 | SQLite Multi-Writer | Chat/Dispatch down | Hoch unter Agent-Last | **P0** |
| P0.2 | Connection Leaks | Lock-Eskalation | Mittel–Hoch | **P0** |
| P0.3 | ACK on LLM fail | Job-Verlust | Hoch bei Free-LLMs | **P0** |
| P1.1 | Fake Cross-Process Notify | Latenz, DB-Last | Immer | **P1** |
| P1.2 | Stuck-Recovery NULL | Queue-Thrash | Mittel | **P1** |
| P1.3 | Process Races | Doppel/Zombie | Niedrig (nach Fix) | **P1 residual** |
| P1.4 | Free LLM Fragility | Schlechte Antworten | Hoch ohne Paid-Key | **P1** |
| P1.5 | HB überschreibt Status | Falsche Health | Mittel | **P1** |
| P2.* | Frontend/Security/Tests | Geschwindigkeit, Risiko | Dauerhaft | **P2** |

---

## 6. Betriebsrisiken (nicht nur Code)

1. **Pre-Push CI + Live-Hub teilen dieselbe User-DB** → Tests können den laufenden Hub stressen.  
2. **66 MB SQLite ohne Write-Queue** skaliert nicht linear mit Agenten/Jobs.  
3. **OpenRouter free** ist kein SLAs-fähiger Default für produktive Demos.  
4. **Keine echte Isolation** zwischen Agent-Workspaces jenseits von Path-Checks.  
5. **Single-Host / localhost** — aktuell ok; Multi-User wäre ein anderes Produkt.

---

## 7. Stärken (nicht unterschlagen)

Trotz der Probleme hat Gnom-Hub substanziellen Wert:

- **Klare Agenten-Rollen** (General/Workers/Soul/Security/Watchdog)  
- **Persistente Queue** mit Priorität, DLQ, Dependencies (selten in Hobby-Orchestrierern)  
- **Showbox** als getrennte Präsentationsschicht  
- **Security-Grants** und Path-Sandbox (nach Fixes ernstzunehmend)  
- **Ehrliche Health-API** (zombie/stale, nicht nur DB-Flag)  
- **Provider-Abstraktion** + Free-Model-Rotation  
- **Breite Unit-Test-Basis** (500+ grüne Tests im CI-Pfad)  
- **Schnelle Iterationsgeschwindigkeit** (sichtbar an Commit-Historie Juli 2026)

---

## 8. Fazit Status

| Dimension | Note (1–5) | Kommentar |
|-----------|------------|-----------|
| Feature-Tiefe | **4.5** | Orchestrator + UI + Security + Memory |
| Stabilität unter Last | **2.5** | Besser nach Fixes, SQLite bleibt Dec |
| Observability | **3.0** | Logs + Health, wenig Tracing/Metrics-Produkt |
| Security (single-user local) | **3.5** | Gut für lokal; nicht multi-tenant |
| Maintainability | **2.5** | Monolithen, Legacy-Dual-Pfade |
| Zukunftsfähigkeit 2026 | **2.0 → 4.0*** | *wenn Strategieplan umgesetzt |

**Einzeiler:**  
Gnom-Hub ist ein **leistungsfähiger Prototyp-Produkt-Zwitter**, der an **SQLite-als-Message-Bus + Prozess-Wildwuchs** krankt — nicht an fehlenden Ideen.

→ Konkrete Modernisierungs-Roadmap: **[STRATEGY_PLAN_2026.md](./STRATEGY_PLAN_2026.md)**
