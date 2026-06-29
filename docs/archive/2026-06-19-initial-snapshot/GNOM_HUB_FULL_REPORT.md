> ⚠️ HISTORISCH — Stand 19.06.2026, NICHT synchron mit Code.
> Aktuelle Source of Truth: docs/ARCHITECTURE.md

# GNOM-HUB Vollständiger Systembericht
## Generiert: 9. Juni 2026
## Ziel: Übergabe an eine andere KI zur sofortigen Weiterarbeit

---

## 1. WAS IST GNOM-HUB?

Ein **minimalistischer Multi-Agenten-Orchestrator** (FastAPI + SQLite + 8 Subprozess-Agenten).
User chattet mit GeneralAG, der Aufgaben an spezialisierte Worker delegiert.

### Architektur
```
User → FastAPI (Port 3002) → LLM-Router (DeepSeek) → 8 Agent-Subprozesse
  ├── GeneralAG     — Koordinator (zerlegt Aufgaben, delegiert)
  ├── SoulAG        — Gedächtnis (extrahiert Fakten → FAISS-Embeddings)
  ├── WatchdogAG    — Dateischutz, Regelpatrouille
  ├── SecurityAG    — Code-Scanning auf gefährliche Patterns
  ├── CoderAG       — Code schreiben, Shell ausführen
  ├── WriterAG      — Texte, Dokumentation
  ├── ResearcherAG  — Web-Recherche (curl, Browser)
  └── EditorAG      — Qualitätsprüfung, Review
```

### Kommunikation: Agenten sprechen NUR über eine SQLite-Message-Queue (`agent_messages`)
```
GeneralAG → dispatch_mention() → INSERT INTO agent_messages
Ziel-Agent → fetch_next_message() → POLL → verarbeitet → ack_message()
```

### LLM-Provider: DeepSeek (Primär) → OpenRouter Free → Ollama (Fallback)

---

## 2. AKTUELLER ZUSTAND

### Metriken (Live-DB)
| Metrik | Wert |
|--------|------|
| Agenten-Status | 8/8 online ✅ |
| Chat-Nachrichten | 963 |
| Verarbeitete Agent-Messages | 573 |
| Soul-Fakten | 140 (116 high, 19 med, 5 low) |
| Blockade-Logs | 91 |
| Workspace-Dateien | ~31 |
| Tests gesamt | 154 (davon 152 pass, 2 intentional fail) |

### Letzte 15 Commits
Letzter: `48b27d9` — GeneralAG liefert Ergebnisse via SHOWBOX:user
Enthalten: SoulAG-Heartbeat, Whitelist-Erweiterung, Prompt-Überarbeitung,
ZWC-Direktiven, Event-basierter Gatekeeper, Stress-Tests

### Ungestagede Änderungen (12 Dateien)
- **agent_definitions.py**: Permissions erweitert (godmode für alle Worker,
  GeneralAG write/run)
- **path_validator.py**: Workspace-Confinement aufgehoben
- **gatekeeper.py**: Workspace-Pfad-Blockade + GeneralAG-Shell-Verbot entfernt
- **pulse.py**: letzte Anpassungen
- **soul.py**: Optimierungen
- **config/**: JSON-Slider angepasst
- **chat.js**: Frontend-Änderungen
- **tests/**: Test-Anpassungen

---

## 3. TEST-ERGEBNISSE (152/154 pass)

```
tests/test_gnom_hub.py ..............  [ 9%]
tests/test_security_suite.py ........ [ 87%]
tests/test_stability.py ............. [ 97%]
tests/test_state.py ................. [100%]
----------------------------------------
2 FAILED (intentional, siehe unten)
```

### 2 Intentional Failures
| Test | Grund |
|------|-------|
| `test_unsafe_path_instant_blocked` | `_safe()` erlaubt jetzt Pfade außerhalb Workspace |
| `test_generalag_shell_blocked` | GeneralAG darf jetzt Shell-Befehle |

**MÜSSEN aktualisiert werden:** Tests erwarten altes restriktives Verhalten.

---

## 4. KRITISCHE PROBLEME (muss gefixt werden)

### 🔴 PULSE-JANITOR BUG (pulse.py:32-40)
```python
for name in AGENTS:
    proc = _get_proc(name)
    status = "running" if proc else "stopped"  # ← FALSCH!
    agent = repo.get_by_name(name)
    if agent:
        if agent.status != status:  # Überschreibt "online"/"busy" mit "running"!
            agent.status = status
            repo.save(agent)
```
**Effekt:** Alle 30s werden Agent-Status auf "running" gesetzt, egal ob busy/online.
Dadurch erkennt `@@free` keine "busy"-Agenten mehr. Betrifft auch UI-Anzeige.

**Fix:** `status = "online" if proc else "offline"` oder Zeile 32-40 ganz entfernen
(duales Monitoring durch monitor.py v2).

### 🔴 MONITOR SCRIPT LÄUFT NOCH MIT PYTHON 3.8 (PID 9135 - tot?)
- Alter Monitor ist gekillt
- Neuer Monitor läuft: PID 37536, `/tmp/gnom-monitor.py`
- Start bei Hub-Neustart nicht automatisch → muss in `run.sh` integriert werden

### 🔴 WEAZYPRINT NUR IM VENV, NICHT IM PATH
- `which weasyprint` → Python 3.8 (kaputt)
- `/Users/landjunge/gnom-hub/.venv/bin/weasyprint` → funktioniert
- Agenten nutzen System-Python → finden kein funktionierendes weasyprint
- **Fix:** Symlink setzen oder `weasyprint` im PATH ergänzen

---

## 5. SCHWERWIEGENDE INKONSISTENZEN

### ⚠️ `pyproject.toml` vs Realität
- `requires-python = ">=3.9"` aber Tests laufen mit Python 3.8 (default)
- `sentence-transformers`, `faiss-cpu`, `transformers` in Dependencies
  → sehr große Pakete, werden nur von SoulAG für Embeddings gebraucht
  → Kein Hinweis dass diese optional sind

### ⚠️ `agent_base.py:99` — SoulAG-Memory-Injection
```python
soul_instance.inject_context(agent_name, chat_history)
```
Importiert `soul_instance` global → wenn SoulAG nicht läuft, crasht BaseAgent.
Kein try/except.

### ⚠️ dispatch_mention() — Circular Import Risiko
`router.py:232` hat Workaround mit Local Import:
```python
from gnom_hub.agents.swarm.swarm_comms import process_swarm_mentions
```
Das schreit nach Refactoring. Funktioniert, aber ist zerbrechlich.

### ⚠️ Kein automatischer Agenten-Neustart bei @@free
`@@free` setzt nur DB-Status zurück, killt/restartet NICHT den Prozess.
Wenn Agent-Prozess gehängt ist, bleibt er tot — freed im Kreis ohne Wirkung.

---

## 6. DOKUMENTIERTE FEATURES vs REALITÄT

| Feature | Dokumentiert in | Realität |
|---------|----------------|----------|
| **154 Tests** | README, CHANGELOG | ✅ 154 Tests, 2 intentional fail |
| **Event-basierter Gatekeeper** | CHANGELOG v1.1.1 | ✅ Existiert |
| **ZWC-Direktiven** | CHANGELOG v1.1.1 | ✅ Existiert |
| **SoulAG v3 (Scoring, Aging)** | GNOM_HUB_STATUS.md | ✅ Existiert |
| **AGtuning 7 Tabs** | GNOM_HUB_STATUS.md | ✅ Im Frontend |
| **Workflow Engine V3** | GNOM_HUB_STATUS.md | ⚠️ DB-Tabellen leer (0 workflows) |
| **Preset-System** | GNOM_HUB_STATUS.md | ✅ config/presets/ |
| **SuperGNOM-Baking** | GNOM_HUB_STATUS.md | ✅ Tests pass |
| **Phase 16 (Agent Inspector)** | PHASE_16_IDEA.md | ❌ Nur Konzept, kein Code |
| **TTS Integration** | MASTER_BRIEFING.md | ❌ Fehlt |
| **USB-Stick-Erkennung** | GNOM_HUB_STATUS.md | ❌ Fehlt |
| **Obedience-Slider** | GNOM_HUB_STATUS.md | ⚠️ Daten gespeichert, nicht ausgewertet |

---

## 7. OFFENE FEATURES (laut Planung)

### Phase 16 — Agent Inspector & Live Optimizer (komplett fehlend)
Geplant in `PHASE_16_IDEA.md`:
- [ ] Persönlichkeits-Slider (formell↔locker, knapp↔ausführlich)
- [ ] Gedächtnisstärke-Anzeige
- [ ] Risikobereitschaft-Slider
- [ ] Export/Import von Agenten als JSON
- [ ] Aus Agenten Presets erzeugen
- [ ] Experten-Modus (Prompt, Token, Reasoning-Chain)

### MASTER_BRIEFING.md Genannte Features (fehlend/unvollständig)
- [ ] TTS (ElevenLabs + Browser SpeechSynthesis)
- [ ] Nuke-Button (CRT + Godzilla + pkill)
- [ ] Multi-Provider-Router mit Fallback-Kette ✅ (teilweise)
- [ ] Plugin-System für neue Agententypen
- [ ] Hot-Reload der Agenten-Konfiguration

---

## 8. WORKSPACE-DATEIEN (gnom_workspace/default/)

```
index.html                     — Mariusz Borysow Website DE
index_pl.html                  — Mariusz Borysow Website PL
iphone12pro_preise.html        — iPhone 12 Pro Preisvergleich
iphone12pro_preise.pdf         — PDF (260K)
julius_email_signatur.html     — Email Signatur Julius
julius_email_signatur_v2.html  — Email Signatur v2
reset_android11_notfall.html   — Android 11 Reset DE
reset_android11_notfall_pl.html— Android 11 Reset PL
reset_android11_notfall_pl.pdf — PDF (500K)
mariusz_borysow_website.pdf    — PDF (16K)
mariusz_borysow_website_pl.pdf — PDF (432K)
security_monitor.py            — Sicherheitsmonitor
security_monitor_v2.py         — Sicherheitsmonitor v2
sicherheitsueberwachung_richtlinie.md — Security Policy
sicherheits_pruefbericht_editorag.md  — Audit Report
mariusz_borysow_website_inhalte_de.txt — Website Texte DE
mariusz_borysow_website_inhalte_pl.txt — Website Texte PL
okitel_unlock_complete.html    — Okitel Unlock DE
okitel_unlock_pl.html          — Okitel Unlock PL
okitel_unlock_methods.md       — Unlock Methoden
android11_reset_diagnose.html  — Android Diagnose
reset_android11_notfall.md     — Android Notfall
```

---

## 9. INFRASTRUKTUR

### Läuft aktuell
- **Hub**: Port 3002, Python 3.10 (.venv)
- **8 Agenten**: Alle subprocess (Python 3.10)
- **Monitor v2**: PID 37536, `/tmp/gnom-monitor.py` (freed nach 2min busy)
- **DB**: `~/.gnom-hub/data/gnomhub.db`
- **Logs**: `/Users/landjunge/gnom-hub/logs/`

### Wichtige Pfade
```
Projekt-Root:  /Users/landjunge/gnom-hub/
venv:          /Users/landjunge/gnom-hub/.venv/
Python:        /Users/landjunge/gnom-hub/.venv/bin/python3.10
Config:        /Users/landjunge/gnom-hub/config/.env
DB:            ~/.gnom-hub/data/gnomhub.db
Agent-Logs:    /Users/landjunge/gnom-hub/logs/logs_*.txt
Monitor:       /tmp/gnom-monitor.py
Monitor-Log:   /tmp/gnom-monitor-v2.log
Hub-Log:       /tmp/gnom-hub-restart.log
```

---

## 10. PRIORISIERTE TODO-LISTE

### 🔴 SOFORT (bugs/blockers)
1. **Fix pulse.py:32-40** — `status = "running"` → `"online"`
2. **Monitor in run.sh integrieren** — startet nicht automatisch mit Hub
3. **Tests aktualisieren** — 2 Intentional Failures fixen
4. **weasyprint symlink** — `ln -sf .venv/bin/weasyprint /usr/local/bin/`

### 🟡 DRINGEND (stabilität)
5. **agent_base.py:99 try/except** — SoulAG-Import nicht gecrasht wenn offline
6. **@@free restart** — Auch Agent-Prozess killen+neustarten
7. **dispatch_mention circular import** — Refactoring der Import-Struktur

### 🟢 NORMAL (features)
8. **Phase 16 beginnen** — Agent Inspector Backend-API
9. **Obedience-Slider auswerten** — Prompt-Änderung im Router
10. **Bake-Tool-Timeout fixen** — Endpunkt läuft, wird vom Timeout gekillt

### 🔵 NIEDRIG (nice-to-have)
11. **TTS Integration**
12. **Plugin-System**
13. **Hot-Reload Agent Config**
14. **Colored Chat**
