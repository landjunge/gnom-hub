# GNOM-HUB ARCHITEKTUR & DEFINITIONEN
## Vollständiges System-Handbuch — Stand: 10. Juni 2026

---

## 1. DIE 8 AGENTEN

### 1.1 GeneralAG — Der Koordinator 👑
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Koordinator, delegiert Aufgaben |
| **Capabilities** | `@job`, `@general` |
| **Permissions** | `read`, `write`, `run`, `godmode` (darf aber NIE selbst schreiben/ausführen!) |
| **Prompt-Kern** | User-Anfrage zitieren → in Teilaufgaben zerlegen → an Worker delegieren |
| **Streng verboten** | `[WRITE:]`, `[SHELL:]`, Browser, `<SHOWBOX:user>` |
| **Blockade-Handling** | Bei Worker-Fehler → an @SecurityAG (mit User-Anfrage-Zitat) + @WatchdogAG |

**Aufgabe:** Nimmt User-Anfragen entgegen, analysiert sie, delegiert an passende Worker, sammelt Ergebnisse, liefert an User zurück. Schreibt NIE selbst Code oder Dateien.

### 1.2 CoderAG — Der Schmied ⚡
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Code schreiben, Shell ausführen |
| **Capabilities** | `@code` |
| **Permissions** | `read`, `write`, `run`, `@job`, `godmode` |
| **Prompt-Kern** | `[WRITE:]` + `[SHELL:]` → Ergebnis in `<SHOWBOX:worker>` → @GeneralAG Status |

**Aufgabe:** Erstellt Dateien, führt Shell-Befehle aus, programmiert. Bei User-Kritik: stoppen und @GeneralAG nachfragen.

### 1.3 WriterAG — Der Schreiber 📜
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Texte, Dokumentation, Inhalte |
| **Capabilities** | `@write` |
| **Permissions** | `read`, `write`, `run`, `@job`, `godmode` |
| **Prompt-Kern** | Texte schreiben → `[WRITE:]` → `<SHOWBOX:worker>` → @GeneralAG Status |

**Aufgabe:** Erstellt Textdateien, Dokumentation, Blog-Posts, Übersetzungen. Achtet auf Grammatik und Stil.

### 1.4 ResearcherAG — Der Späher 🔍
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Web-Recherche, Fakten sammeln |
| **Capabilities** | `@research` |
| **Permissions** | `read`, `write`, `run`, `@job`, `godmode` |
| **Prompt-Kern** | Recherche → `[WRITE:]` Ergebnisse → `<SHOWBOX:worker>` → @GeneralAG Status |

**Aufgabe:** Recherchiert im Internet (curl, Browser), sammelt Fakten, strukturierte Ausgabe. Keine Bewertung, nur Fakten.

### 1.5 EditorAG — Der Prüfer 📋
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Qualitätssicherung, Review |
| **Capabilities** | `@edit` |
| **Permissions** | `read`, `write`, `run`, `@job`, `godmode` |
| **Prompt-Kern** | Prüfen → Korrektur `[WRITE:]` → @GeneralAG Status |

**Aufgabe:** Prüft Code/Text auf Fehler, Grammatik, Logik. Automatischer Review nach Datei-Schreibaktionen von CoderAG/WriterAG.

### 1.6 SoulAG — Das Gedächtnis 💎
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Fakten extrahieren, speichern, abrufen |
| **Capabilities** | `@soul` |
| **Permissions** | `read` (nur lesen!) |
| **Prompt-Kern** | Fakten aus Chat extrahieren → in `soul_memory` DB → @GeneralAG bei wichtigen Fakten |

**Aufgabe:** Lernt aus jeder Chat-Nachricht. Extrahiert Fakten (key/value/priority). Speichert in SQLite + FAISS-Index. Ruft vor jeder Task relevante Fakten ab und injiziert sie ins System-Prompt.
- **Blockaden merken:** Wenn ein Agent blockiert wird aber der User die Aktion verlangt hat → speichern.
- **Technik:** sentence-transformers (all-MiniLM-L6-v2) + FAISS, Scoring (Alter 30/14/7 Tage).

### 1.7 SecurityAG — Der Wächter 🛡️
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Code-Scanning, Blockaden auflösen |
| **Capabilities** | `@security` |
| **Permissions** | `read`, `write`, `run`, `godmode`, `crawl`, `desktop`, `evolve` |
| **Prompt-Kern** | Code scannen (eval, subprocess, os.system, rm -rf) → APPROVED/REJECTED |

**Aufgabe:** Scannt Code auf Sicherheitsrisiken. **Blockade-Auflösung:** Wenn @GeneralAG eine User-Anfrage zitiert und ein Worker blockiert wurde → prüfen: Hat der User die Aktion explizit verlangt? Dann APPROVED.

### 1.8 WatchdogAG — Der Patrouilleur 👁️
| Eigenschaft | Wert |
|-------------|------|
| **Rolle** | Dateischutz, Regel-Patrouille |
| **Capabilities** | `@watchdog` |
| **Permissions** | `read`, `write`, `run`, `godmode`, `crawl`, `desktop`, `evolve` |
| **Prompt-Kern** | Systemdateien schützen (src/gnom_hub, config/, .env, run.sh, index.html) |

**Aufgabe:** Schützt geschützte Pfade. Bei Blockade: Alternative vorschlagen. Patrouilliert den Chat auf Regelverstöße.

---

## 2. KOMMUNIKATION & WORKFLOW

### 2.1 Standard-Chat-Flow
```
User -> @GeneralAG "Aufgabe"
  -> GeneralAG analysiert, zitiert User exakt
  -> Delegiert an @CoderAG / @WriterAG / @ResearcherAG / @EditorAG
  -> Worker verarbeitet, schreibt Datei, sendet Status an @GeneralAG
  -> GeneralAG sammelt Ergebnisse
  -> Liefert an User via <SHOWBOX:system>
```

### 2.2 Brainstorm-Mode (@bs)
```
User -> @bs "Thema"
  -> GeneralAG startet Brainstorm
  -> Alle 4 Worker parallel mit 1.5s Verzögerung
  -> Jeder Worker liefert Ideen
  -> GeneralAG fasst zusammen
```

### 2.3 Blockade-Auflösung (NEU)
```
Worker -> Security-Regel blockiert Aktion
  -> Worker meldet @GeneralAG "Blockiert: ..."
  -> GeneralAG an @SecurityAG: "User wollte: [ZITAT], bitte prüfen"
  -> SecurityAG prüft: "User-Auftrag -> APPROVED" oder "Sicherheitsrisiko -> REJECTED + Alternative"
  -> Bei APPROVED: Worker wiederholt Aktion
  -> SoulAG merkt sich: "Diese Aktion ist für diesen User erlaubt"
```

### 2.4 Agent-Kommunikation (Message-Queue)
```
Agent A -> dispatch_mention() -> INSERT INTO agent_messages (sender, recipient, payload)
Agent B -> fetch_next_message() -> polling -> verarbeitet -> ack_message()
Sequenzielle Tasks: parent_msg_id für Dependency-Chain
Priorität: 0=critical, 5=normal
```

---

## 3. SYSTEM-KOMPONENTEN

### 3.1 Gatekeeper (src/core/security/gatekeeper.py)
| Prüfung | Wirkung |
|---------|---------|
| **verify_write()** | Prüft: Benutzerregeln → System-Pfade → High-Risk Patterns → Auto-Approve |
| **verify_cmd()** | Prüft: Benutzerregeln → System-Pfade → Command-Whitelist |
| **is_command_safe_and_whitelisted()** | Unbekannte Execs = HIGH RISK (blockiert) |
| **wait_for_decision()** | Nur aktiv wenn `enable_confirmations=true` (default: false) |

### 3.2 Pfad-Validierung (src/core/security/path_validator.py)
| Regel | Wirkung |
|-------|---------|
| Agent OHNE Permissions | Nur Workspace |
| Agent MIT Permissions | Überall (auch außerhalb) |
| System-Pfade (`src/gnom_hub/`, `config/`, `.env`, etc.) | IMMER blockiert für Worker |

### 3.3 Geschützte System-Pfade
```
src/gnom_hub/
config/
scripts/
run.sh
index.html
.env
```

### 3.4 High-Risk Patterns (werden HART geblockt)
```regex
rm\s+(-rf|-fr)|subprocess\.(call|run|Popen|check_output)
os\.system\(|os\.popen\(|os\.exec|os\.spawn
eval\(|exec\(|compile(.*eval|exec)
shutil\.rmtree\(|chmod.*777
curl.*\|.*sh|wget.*\|.*sh
dd\s+if=|mkfs\.|:(){ :|:& };:
__builtins__|__globals__|__getattribute__
```

### 3.5 Datenbank (SQLite, ~/.gnom-hub/data/gnomhub.db)
| Tabelle | Zweck |
|---------|-------|
| `state` | Konfiguration (Keys, Routing, Presets) |
| `agents` | 8 Agenten-Definitionen |
| `agent_messages` | Kommunikations-Queue zwischen Agenten |
| `chat` | Chat-Verlauf |
| `soul_memory` | Gelernte Fakten |
| `blockade_log` | Blockierte Aktionen |
| `agent_capabilities` | Registrierte Fähigkeiten |

---

## 4. AKTUELLER ZUSTAND (10. Juni 2026)

### 4.1 Version
`v1.2.0` — pyproject.toml, CHANGELOG aktualisiert

### 4.2 Tests
**154 Tests — alle bestanden** (via pytest, Python 3.10)

### 4.3 GitHub
- **Repo:** https://github.com/landjunge/gnom-hub (PUBLIC)
- **Pages:** https://landjunge.github.io/gnom-hub/
- **Forum:** Discussions aktiviert
- **Topics:** ai-agents, llm, fastapi, multi-agent, orchestrator, deepseek, python, agent-swarm, local-ai

### 4.4 Infrastruktur
| Komponente | Details |
|------------|---------|
| **Port** | 3002 |
| **Python** | 3.10 (.venv) |
| **Framework** | FastAPI + Uvicorn |
| **LLM** | DeepSeek V4 Pro (Primär), OpenRouter Free (Fallback), Ollama (Notfall) |
| **DB** | SQLite (WAL-Modus) |
| **Embeddings** | sentence-transformers + FAISS |
| **TTS** | macOS `say` (Anna, deutsch) |
| **Screen-Recording** | ffmpeg + avfoundation |
| **Maussteuerung** | cliclick |

### 4.5 Letzte Session (9.-10. Juni 2026) — Erledigt
- [x] Workspace-Confinement aufgehoben (Agents mit Permissions dürfen überall schreiben)
- [x] GeneralAG hat write/run/godmode bekommen (aber Prompt sagt: nie selbst nutzen!)
- [x] Alle Worker haben godmode
- [x] `@@free` killt+restartet jetzt Agent-Prozesse (nicht nur DB-Reset)
- [x] Gatekeeper: Tote Imports entfernt, Whiltelist verschärft
- [x] Monitor-Skript (`scripts/gnom-monitor.py`) — freed Agents nach 2 Min
- [x] Pulse-Jänitor-Bug gefixt (überschrieb Status mit "running")
- [x] SoulAG: None-check in agent_base.py
- [x] CHANGELOG + version auf 1.2.0
- [x] README Badges aktualisiert (154 Tests, Python 3.10)
- [x] Alte Workspaces, Backups, Temp-Dateien gelöscht
- [x] DB geleert (soul_memory, chat, logs, FAISS-Indizes)
- [x] 50 System-Stress-Tests (27 pass, 23 Timing-Probleme)
- [x] GitHub Pages live
- [x] Agent-Prompts verbessert (GeneralAG nie selbst schreiben, SecurityAG Blockade-Auflösung, SoulAG merkt Erlaubnisse)

### 4.6 Noch offen / Geplant
- [ ] **Phase 16: Agent Inspector** — Persönlichkeits-Slider, Export/Import
- [ ] **TTS im SuperGNOM** — Sprachausgabe-Konfiguration im Bake-Paket
- [ ] **USB-Stick-Fallback** — Automatischer Fallback auf lokales LLM
- [ ] **Preset als Standard setzen** — UI-Button fehlt
- [ ] **Obedience-Slider auswerten** — Daten gespeichert, nicht im Router
- [ ] **Live-Demo-Video** — Agents sollen selbst ein Screen-Recording + TTS-Video erstellen

---

## 5. WICHTIGE BEFEHLE

| Befehl | Wirkung |
|--------|---------|
| `@GeneralAG [Aufgabe]` | Aufgabe starten |
| `@CoderAG [Aufgabe]` | Direkt an CoderAG |
| `@bs [Thema]` | Brainstorm-Mode |
| `@@free [Agent]` | Agent befreien + Prozess neustarten |
| `@@clear` | Chat-Verlauf löschen |
| `@@allclear000` | KOMPLETT-RESET (DB, Workspace, Tokens, Neustart) |
| `@@git [cmd]` | Git-Befehl (nie via [SHELL:]) |
| `@@status` | System-Status anzeigen |

---

## 6. WICHTIGE DATEIEN & PFADE

| Pfad | Zweck |
|------|-------|
| `/Users/landjunge/gnom-hub/` | Projekt-Root |
| `.venv/` | Python 3.10 Virtual Environment |
| `src/gnom_hub/` | Quellcode |
| `src/gnom_hub/agents/agent_definitions.py` | **Agenten-Definitionen** (Prompts, Permissions) |
| `src/gnom_hub/core/security/gatekeeper.py` | **Gatekeeper** (verify_write, verify_cmd) |
| `src/gnom_hub/core/security/path_validator.py` | **Pfad-Validierung** (_safe, system_paths) |
| `src/gnom_hub/infrastructure/router/router.py` | **LLM-Router** (ask_router, Fallback) |
| `src/gnom_hub/agents/swarm/swarm_comms.py` | **Message-Queue** (dispatch, fetch, ack) |
| `src/gnom_hub/infrastructure/pulse.py` | **Janitor** (free stuck Agents) |
| `scripts/gnom-monitor.py` | **Monitor** (Auto-Free nach 2 Min) |
| `config/.env` | **API-Keys** (DeepSeek, OpenRouter, FTP) |
| `config/routing.txt` | **LLM-Routing** (Agent → Provider → Model) |
| `~/.gnom-hub/data/gnomhub.db` | **Live-Datenbank** |
| `gnom_workspace/default/` | **Workspace** (erstellte Dateien) |
| `tests/` | **154 Tests** |
| `PRE_PUSH_CHECKLIST.md` | **Checkliste vor jedem Push** |
| `GNOM_HUB_FULL_REPORT.md` | **Report für andere KI-Assistenten** |
