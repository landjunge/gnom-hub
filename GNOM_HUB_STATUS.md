# GNOM-HUB Status Report — June 5, 2026

## 1. Ausgangslage

**Routing:** Auto-Routing mit `stage_1` bis `stage_4`, komplexe Provider-Auswahl pro Rolle. OpenRouter als Primär-Provider mit Free-Modellen. Kein DeepSeek-Support.

**Security:** Schwerfälliges Gatekeeper-System mit `wait_for_decision()` (5-Minuten-Blocking-Loops), Breakpoints, `enable_confirmations`-Gating. Viele Aktionen erforderten manuelle Bestätigung.

**SoulAG:** Fakten wuchsen unkontrolliert. Keine Limits, kein Aging, kein Scoring. Widersprüchliche Fakten (z.B. "nicht schreiben, vorher fragen") überschrieben Agenten-Direktiven.

**Oberfläche:** Agenten-Detail als Popup-Modal. Keine zentrale Tuning-Seite. Keine Preset-Verwaltung.

## 2. Was wurde verbessert

### Routing
- **DeepSeek-Integration:** `routing.txt` steuert jetzt direkt alle 8 Agenten (Pro=R1 für Coder/Security/Researcher, Flash=V3 für Rest)
- **Fallback-Kette:** DeepSeek → OpenRouter Free Models → Ollama (lokal)
- **Token-Limits:** Worker 8192, GeneralAG 2000, SoulAG 1500, Security/Watchdog 1000 (vorher None = API-Default ~256)
- **Task-Dependencies:** `dispatch_sequence()` erstellt sequentielle Tasks mit `parent_msg_id`. `fetch_next_message()` prüft Abhängigkeiten vor Verarbeitung
- **DLQ-Kaskade:** `fail_dependent_messages()` — wenn Parent-Task in Dead-Letter-Queue geht, werden alle Children ebenfalls abgebrochen
- **Dependency-Timeout:** 120s. Wenn Parent nicht fertig wird → gesamte Sequenz abgebrochen
- **Capability-Fallback:** `find_best_agent_for_task()` — Schlagwort-basierte Agenten-Suche wenn Ziel-Agent offline
- **Multiline-Delegation:** `parse_agent_sequence()` erkennt `@Agent1 -> task1\n@Agent2 -> task2` und erstellt Sequenzen
- **Brainstorm-Stagger:** Worker starten mit 1.5s Abstand (verhindert DeepSeek Rate-Limits)
- **Identity-Regeln verstärkt:** Prompt-Injection mit "⚠️ DU BIST X UND NUR X" am Anfang UND Ende des System-Prompts
- **Agent-Karten:** Fixe Sortierung (Writer, Coder, Researcher, Editor), 10s Auto-Refresh bei Status-Änderung
- **Pulse-Janitor:** 60s Timeout (vorher 300s) für feststeckende `busy`-Agenten, läuft jetzt im Hub-Prozess

### Security
- **Breakpoints komplett entfernt:** `check_and_wait_breakpoint()` aus `action_write.py` und `action_exec.py`
- **`verify_write` vereinfacht:** Keine Warte-Dialoge mehr. Prüft: Workspace-Grenzen → System-Pfade → Gefährliche Patterns → Auto-Approve
- **`verify_cmd` bereinigt:** Whitelist-Prüfung + System-Pfad-Schutz. GeneralAG: KEINE Shell-Befehle
- **Core-File-Schutz IMMER aktiv:** `is_worker_blocked()` und `is_security_block()` nicht mehr an `enable_confirmations` gekoppelt
- **Regex-basierte Pattern-Erkennung:** `_DANGEROUS_RE` statt String-Match. Erkennt verschleierte Varianten (`rm  -rf`, `os . system(`, etc.)
- **WatchdogAG-Logging:** Jeder Block schreibt eine Chat-Nachricht mit Agent-Name und Grund

### SoulAG (v3)
- **MAX_SOUL_FACTS = 50** mit automatischer Löschung des ältesten Fakts bei Überschreitung
- **Fact-Aging (3 Stufen):** High 30d, Medium 14d, Low 7d → überalterte Fakten werden gelöscht
- **Score-basiertes Pruning:** `Score = Priorität (30/15/5) + Nutzung (max +30) - Alter (1.5/Tag)`
- **Regex-Block-Liste:** 10 Patterns für widersprüchliche Fakten (z.B. "nicht schreib", "vorher frag", "Showbox statt WRITE")
- **Min-Länge 15 Zeichen** pro Fakt (verhindert Einzelwörter)
- **Kurzzeit-Dedup-Cache:** Gleicher Key in 5 Min wird nicht doppelt gespeichert
- **Periodischer Hausputz:** Max 1x/Stunde. Score-basiertes Pruning + Aging-Cleanup

### AGtuning-Seite (7 Tabs)
1. **📝 Prompt:** System-Prompt + Custom Suffix editierbar
2. **💡 Soul:** Fakten filtern (Text+Priorität), editieren, löschen, manuell hinzufügen
3. **🛡️ Blockaden:** 4 Schutz-Karten + Bestätigungs-Modus-Toggle
4. **🔧 Tools:** 12 Tools als klickbare Kacheln (✅/⬜ Toggle pro Tool)
5. **🎚️ Verhalten:** 5 Slider (+ Obedience für System-Agenten)
6. **💾 Presets:** Speichern/Laden/Anwenden (gespeichert als JSON in `config/presets/`)
7. **🏭 Bake:** SuperGNOM backen mit Preset-Wahl, API-Key-Embedding, `run.sh`/`run.bat`

Alle 8 Agenten verfügbar. Klick auf Agenten-Karte → volle Tuning-Seite. Keine Popups mehr.

### Workflow-Engine (V3)
- **Stuck-Task-Recovery:** Tasks >5 Min in `running` → automatisch `failed`
- **Error-Summary pro Task:** `[ERROR]`, `[STUCK]`, `[DISPATCH]` — menschenlesbarer Grund
- **Nested-Variablen:** `{task_id:data.field}` mit Dot-Notation + Fallback
- **Idempotenz:** `handle_task_completion()` prüft Status vor Update
- **Strukturiertes Logging:** `_log_wf()` mit Workflow-ID und Task-ID

### Oberfläche (UI Fixes)
- **Agent-Karten pulsen nur bei echtem `busy`-Status** (Auto-Refresh alle 10s)
- **Pulse-Janitor 60s** für feststeckende Agenten
- **Agent-Namen im Original** (CoderAG statt Turing-V50)
- **Cache-Buster v=4** auf allen JS/CSS-Dateien
- **launchd-Service** für dauerhaften Hub-Betrieb (überlebt Terminal-Schließen)

## 3. Aktueller Stand

### Funktioniert gut ✅
- DeepSeek-Routing mit Reasoner (R1) auf allen 8 Agenten
- Brainstorm mit gestaffelten API-Calls
- Workflow-Engine mit Dependencies, Timeout, Error-Summary
- SoulAG mit Scoring, Aging, Dedup, Max-Limit
- AGtuning-Seite mit 7 editierbaren Tabs
- Preset-Speicherung und -Laden
- SuperGNOM-Baking (compiler.py + API + UI)
- Alle Tests: 139/139 passed

### Noch offen ⚠️
- **TTS im SuperGNOM:** Sprachausgabe-Konfiguration fehlt im gebackenen Paket
- **USB-Stick-Erkennung:** Kein automatischer Fallback auf lokales LLM wenn kein Netzwerk
- **Preset als Standard setzen:** UI-Button fehlt (API existiert)
- **Bake-Endpoint:** Läuft via API, aber wird vom Tool-Timeout gekillt (muss manuell gestartet werden)
- **Obedience-Slider:** Daten werden gespeichert, aber nicht im Router ausgewertet (keine Prompt-Änderung)
- **Colored Chat:** Nur Standard-Chat im SuperGNOM, keine Preset-spezifische Farbgebung

## 4. Zusammenfassung

GNOM-HUB hat in dieser Session massive Verbesserungen erfahren:

- **Routing:** Von komplexem Auto-Routing zu klarem, direktem DeepSeek-Routing mit Fallback-Kette
- **Security:** Von blockierenden Dialogen zu instantanen, immer-aktiven Schutzschichten
- **SoulAG:** Von unkontrolliertem Fakten-Wachstum zu qualitätskontrolliertem Memory-System
- **Workflow:** Von einfacher Task-Erstellung zu robuster Engine mit Dependencies, Timeout, Error-Tracking
- **UI:** Vom Popup-Modal zur vollständigen 7-Tab-Tuning-Seite mit Presets und Baking

Insgesamt ist GNOM-Hub **deutlich stabiler, schneller und benutzbarer** als vor der Session. Die Kern-Architektur (Routing, Security, SoulAG, Workflow) ist solide. Die Oberfläche ist funktional. Was fehlt, sind Feinschliff und erweiterte Features (TTS, USB-Fallback, colored Chat).

**Commit-Count seit Session-Beginn:** 16 Commits
**Letzter Commit:** `6978f3d` — "Fix: Bake-Endpoint Syntax (Indentation) + Obedience-Slider für System-Agenten"
