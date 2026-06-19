# Gnom-Hub Architecture Reference

> Kompakte technische Dokumentation für eine andere KI, die das System verstehen, weiterentwickeln oder debuggen will.

**Version:** 2.0.0
**Git Commit:** `8c14e71`
**Python:** 3.10+
**Stack:** FastAPI + SQLite + FAISS + uvicorn + MiniMax M3

---

## 1. Was ist Gnom-Hub?

Local-first Multi-Agent-Orchestrator. FastAPI-App mit 8 KI-Agenten die miteinander kommunizieren, Aufgaben delegieren, Tools nutzen.

**Kernidee:** 4+4 fixe Agent-Topologie. User ist Souverän, Agents sind Werkzeuge.

---

## 2. Architektur

```
Browser (index.html, 9 JS-Module)
       │ HTTP
FastAPI Hub (uvicorn :3002, 121 Endpoints)
       │
8 Agent-Prozesse (subprocess.Popen)
       │
6 SQLite-DBs (WAL) + FAISS Vector-Index
```

---

## 3. Die 8 Agenten

| Agent | Rolle | Farbe | Cap | Hauptaufgabe |
|---|---|---|---|---|
| **SoulAG** | Souverän | Cyan | `@soul` | Einziger User-Kontakt, exklusive DBs, delegiert an GeneralAG |
| **GeneralAG** | Dirigent | Blau | `@job` | Delegiert an 4 Worker, kennt keine System-Agents |
| **WatchdogAG** | Sicherheitsfilter | Rot | `@watchdog` | Pragmatischer Blocker, Showbox-Rückfragen |
| **SecurityAG** | System Operator | Lila | `@security` | FS-Operator, LLM/TTS-Zuweisung, Backup |
| **CoderAG** | Coder | Orange | `@code` | Code via Showbox |
| **WriterAG** | Writer | Grün | `@write` | Texte via Showbox |
| **ResearcherAG** | Researcher | Gelb | `@research` | Web-Recherche via Showbox |
| **EditorAG** | Editor | Pink | `@edit` | QA via Showbox |

**Kommunikations-Hierarchie:** User ↔ SoulAG ↔ GeneralAG ↔ Worker (4). Niemals umgehen.

---

## 4. SoulAG — 4 exklusive Datenbanken

SoulAG ist der **einzige** Agent mit Schreibzugriff auf:

| DB | Zweck |
|---|---|
| `soul_memory.db` | Aktive Fakten, gelerntes Wissen |
| `context.db` | Session-Kontext, Kurzzeitgedächtnis |
| `soul_passive.db` | Archiv für alte Informationen |
| FAISS Vector DB | Semantische Ähnlichkeitssuche |

**SoulAG-Prompt (gekürzt):**
```python
"Du bist SoulAG — der SOUVERÄN. Du denkst laut (TTS).
 Du bist der EINZIGE Agent der mit dem User kommuniziert.
 Du antwortest AUSSCHLIESSLICH über das Showbox-Tool:
 [SHOWBOX:name]{'slides': [...], 'buttons': [...]}
 Du darfst NIEMALS rohes HTML direkt in den Chat schreiben.
 Du hast exklusiven Schreibzugriff auf 4 Datenbanken
 (soul_memory, context, soul_passive, FAISS Vector).
 Andere Agenten dürfen nur lesen. Farbe: Cyan."
```

---

## 5. GeneralAG-Prompt (gekürzt)

```python
"Du bist GeneralAG — der DIRIGENT. Reiner Delegator.
 Du erhältst Aufträge ausschließlich von SoulAG.
 Du weißt nicht, dass WatchdogAG/SecurityAG existieren.
 Du delegierst nur an 4 Worker (Coder, Writer, Researcher, Editor).
 Du erstellst KEINEN Code, Text oder Recherche.
 Keine Schreibrechte. Farbe: Blau."
```

---

## 6. Showbox-Tool-Syntax

Agenten kommunizieren **ausschließlich** über Showbox:

```xml
<SHOWBOX:name>
{"slides": ["<html>...</html>"], "buttons": [{"id":"b1","label":"OK","onClick":"send:..."}]}
</SHOWBOX>
```

**Backend-Filter** (`chat_legacy.py`): Entfernt `<SHOWBOX>` aus Agent-Outputs, speichert in `showbox_presentations` DB, aktiviert. Im Chat erscheint nur `[→ Showbox: name]`.

---

## 7. LLM-Routing

Bei `provider=minimax` (Default für alle 8 Agenten):

```
1. minimax/MiniMax-M3       (primär)
2. openrouter/Free Models   (Fallback)
3. lokal/llama3 (Ollama)    (Notnagel)
```

Code in `src/gnom_hub/infrastructure/router/router.py` (`_resolve`).

---

## 8. Datenbanken — Vollständige Topologie

`~/.gnom-hub/data/` enthält **6 SQLite-DBs + FAISS + Hilfsdateien**, alle im WAL-Mode.

### 8.1 `gnomhub.db` (~70 MB) — Hub-Hauptdatenbank

| Tabelle | Zweck | Owner |
|---|---|---|
| `agents` | 8 Agent-Definitionen | Hub |
| `chat` | Chat-Verlauf | User+Agents |
| `state` | Key-Value (llm_agents, blockade_level, active_showbox) | Alle |
| `soul_memory` | SoulAG-Fakten | **NUR SoulAG** |
| `audit_log` | LLM-Calls | Router |
| `agent_capabilities`, `capabilities` | Tool-Registry | Tool-Registry |
| `agent_messages` | User→Agent-Queue | Swarm-Comms |
| `swarm_callbacks` | Swarm-Kommunikation | GeneralAG |
| `showbox_presentations` | Slides + 8 Buttons | Alle Agents |
| `explainable_outputs` | EO-Wrapper | Router |
| `blockade_log` | Watchdog-Blocks | WatchdogAG |
| `token_budget_logs`, `token_budget_alerts` | Token-Tracking | Router |
| `graceful_degradation_failures` | Fallback-Fehler | Router |
| `workflows`, `workflow_tasks` | Workflow-Engine | GeneralAG |
| `prompt_versions` | Prompt-Evolution v2 | Evolution |

### 8.2 `soul_passive.db` (~561 KB) — SoulAG-Archiv

| Tabelle | Zweck |
|---|---|
| `soul_archive` | Ausgelagerte/alte SoulAG-Fakten |

**Zugriff:** Nur SoulAG.

### 8.3 `context.db` (~713 KB) — Session-Kontext

| Tabelle | Zweck |
|---|---|
| `contexts` | Aktive Kontext-Sessions |
| `context_events` | Events in Session |

**Zugriff:** SoulAG schreibt, andere lesen.

### 8.4 `coordination.db` (~598 KB) — Worker-Koordination

| Tabelle | Zweck |
|---|---|
| `delegation_rules` | Welcher Worker bekommt welche Aufgabe |
| `worker_stats` | Performance-Metriken pro Worker |
| `job_history` | Vergangene Delegations-Jobs |

**Zugriff:** GeneralAG exklusiv.

### 8.5 `passive_archive.db` (~27 MB) — Passiv-Archiv

| Tabelle | Zweck |
|---|---|
| `archive_log` | Langzeit-Archiv alter Chat-Nachrichten |

### 8.6 `rules.db` (~33 KB) — Sicherheitsregeln

| Tabelle | Zweck |
|---|---|
| `rules` | Permanente Blockier-Regeln (User-definiert) |

**Zugriff:** WatchdogAG schreibt, SecurityAG liest.

### 8.7 FAISS Vector Index — `emb_cache.json` (~24 MB)

- Datei-basiert + Binary-Indizes in `~/.ollama/`
- Satz-Embeddings via `sentence-transformers/all-MiniLM-L6-v2`
- Indiziert `soul_memory` für semantische Deduplizierung (`has_similar(text, threshold=0.85)`)
- **Zugriff:** Nur SoulAG

### 8.8 Hilfsdateien

| Datei | Zweck |
|---|---|
| `domains.json` (218 B) | Domain-Mapping |
| `.hub_secret` (32 B, chmod 600) | Hub-interner Secret |
| `audio/` | TTS-MP3-Cache (1-Min-TTL) |

### 8.9 DB-Zugriffs-Matrix

| DB | SoulAG | GeneralAG | WatchdogAG | SecurityAG | Worker |
|---|---|---|---|---|---|
| gnomhub.db (außer soul_memory) | RW | RW | RW | RW | R |
| soul_memory (in gnomhub.db) | **RW** | R | R | R | R |
| soul_passive.db | **RW** | R | R | R | R |
| context.db | **RW** | R | R | R | R |
| coordination.db | R | **RW** | R | R | R |
| rules.db | R | R | **RW** | R | R |
| passive_archive.db | R | R | R | RW | R |
| emb_cache.json (FAISS) | **RW** | R | R | R | R |

**RW = exklusiv, RW = gemeinsam, R = nur lesen**

### 8.10 DB-Lifecycle

1. **Init:** `init_database()` in `db/schema.py` (idempotent)
2. **WAL:** `PRAGMA journal_mode=WAL` für parallel reads/writes
3. **VACUUM:** täglich via `scripts/optimize_dbs.py`
4. **Backup:** alle 5 Min via `scripts/scheduled_backup.sh`
5. **Verify:** nach jedem Backup via `scripts/verify_dbs.py`
6. **Log-Rotation:** bei >10MB (max 3 Backups in `logs/`)

---

## 9. Sicherheit

`blockade_level = 0` (alles offen für Entwicklung). Production sollte 3 setzen.

**Alle Block-Patterns deaktiviert:**
- `path_validator.py`: `is_system_path()` → False, `is_worker_blocked()` → False, `_HIGH_RISK_RE`/`_MEDIUM_RISK_RE` matchen nichts
- `action_exec.py`: `SHELL_BLOCK` Pattern entfernt
- `gatekeeper.py`: `verify_cmd` lässt alles durch

**Secrets:** Ausgelagert nach `~/.gnom-hub/secrets/minimax.key` (chmod 600).

---

## 10. Operations-Scripts

| Script | Zweck |
|---|---|
| `scripts/scheduled_backup.sh` | Daemon: Backup alle 5 Min, kein Overwrite |
| `scripts/verify_dbs.py` | SQLite-Integrität checken |
| `scripts/optimize_dbs.py` | WAL + VACUUM + ANALYZE |
| `scripts/backup_all_dbs.sh` | Manuelles Backup (Trigger: manual/cleanAll/pre-push/scheduled5min) |

**Backup-Verzeichnis:** `~/Desktop/gnom_dev/backups_datenbanken/<timestamp>_<trigger>/`

---

## 11. Bake-System

`bake_supergnom(name, template, selected_models=None)` exportiert als portablen USB-Stick:

```bash
POST /api/admin/bake/start
{"name": "my_agents", "template": "chat", "selected_models": ["llama3.2:1b"]}
```

- `models-info.json`: Liste der gewählten Modelle
- `run.sh`: macht `ollama pull` automatisch beim ersten Start
- Keine toten Symlinks (Stick funktioniert auf jedem Mac)

---

## 12. Health-Endpoint

`GET /api/admin/health`:

```json
{
    "status": "ok",
    "db_ok": true,
    "db_size_mb": 69.62,
    "agents_total": 8,
    "agents_online": 8,
    "memory": 2058,
    "last_backup_ago_min": 195.0
}
```

---

## 13. Wichtige Dateien

- `src/gnom_hub/api/app.py` — FastAPI-Lifespan, spawnt 8 Agenten
- `src/gnom_hub/agents/agent_definitions.py` — 8 Agent-Prompts (Single Source of Truth)
- `src/gnom_hub/agents/agent_base.py` — Agent-Run-Loop (register, heartbeat, fetch_next_message)
- `src/gnom_hub/soul/soul.py` — SoulAG-Klasse mit Fakten-Extraktion
- `src/gnom_hub/db/showbox_repo.py` — Showbox-DB-Operations + `ensure_default_showbox()`
- `src/gnom_hub/infrastructure/router/router.py` — LLM-Routing (`ask_router`)
- `src/gnom_hub/infrastructure/router/router_stage.py` — SmartRouter (`get_best_specific_assignment`)
- `src/gnom_hub/infrastructure/process/process_manager.py` — Agent-Spawn via `agents.run_agent`
- `src/gnom_hub/chat/brainstorm/brainstorm.py` — GeneralAG-Delegation (`dispatch`)
- `src/gnom_hub/core/security/gatekeeper.py` — verify_cmd, blockade_rules
- `src/gnom_hub/core/utils/compiler.py` — Bake-System
- `src/gnom_hub/frontend/showbox.js` — 3-Layer-Showbox-System
- `src/gnom_hub/frontend/dashboard.js` — Bake-UI mit Modell-Auswahl
- `config/routing.txt` — Agent→LLM-Mapping
- `config/.env` — API-Keys (nicht committen)

---

## 14. TODO / Bekannte Probleme

- TTS: Aktuell nur Stub (ElevenLabs-Key fehlt), Browser-Web-Speech als Fallback
- Bake-Selected-Models: Auto-Detect (embedded/linker) noch zu implementieren
- Agenten-Prompts sind alt im Cache — nach Code-Änderungen Restart nötig

---

**Stand:** 2026-06-18
**Letzter Commit:** `8c14e71` "feat(core): security overhaul + soulag 4-dbs + showbox filter + minimax routing + ops scripts"