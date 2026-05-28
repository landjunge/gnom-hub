# 🧠 GNOM-HUB

> **8 Agenten. ~7500 Zeilen. 176 Module. Null Toleranz für Bloat.**
> *Ein lokales Multi-Agenten-Orchestrierungssystem mit defensiver Zero-Trust-Architektur und modularisiertem War Room Dashboard.*

[![License](https://img.shields.io/badge/Lizenz-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agenten-8-blueviolet.svg)](#)
[![Lines of Code](https://img.shields.io/badge/Zeilen_Code-~7500-blue.svg)](#)
[![Modules](https://img.shields.io/badge/Module-176-blue.svg)](#)
[![40-Lines-Rule Compliance](https://img.shields.io/badge/40--Zeilen--Regel-~80%25_konform-orange.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

---

🇩🇪 **Deutsch (README.de.md)** • 🇬🇧 **[English (README.md)](README.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Gesamtübersicht" width="100%">

---

## Was ist Gnom-Hub?

Gnom-Hub ist ein lokales Multi-Agenten-System mit einer klaren Struktur: **176 Python-Module — über 80% davon strikt kürzer als 40 Zeilen**. Es bietet einen leichtgewichtigen Orchestrator ohne aufgeblähte Frameworks, der vollständig lokal läuft, kein schwerfälliges Docker benötigt und die Agenten über ein Web-Dashboard namens **War Room** steuert.

> [!IMPORTANT]
> **Bewusster Minimalismus:** Gnom-Hub ist auf Einfachheit und maximale Performance ausgelegt. Das System ist bewusst **nicht** dafür konzipiert, Hunderte von Agenten zu steuern, sondern dient der effizienten Orchestrierung einer kleinen, hochspezialisierten und überschaubaren Gruppe von Agenten.

---

## 🚀 Features (Funktionsumfang)

Gnom-Hub kombiniert eine robuste Multi-Prozess-Orchestrierung mit einem interaktiven Web-Interface. Die wichtigsten Features umfassen:

*   **Automatisches intelligentes Routing**:
    Der LLM-Router (`router.py`) leitet Anfragen dynamisch an das am besten geeignete Modell (z. B. DeepSeek-Reasoner, Claude, GPT) weiter. Bei API-Ausfällen oder Netzwerksperren greift das System vollautomatisch auf konfigurierte lokale Fallbacks (wie eine Offline-Llama-Instanz über Ollama) zurück, um Blockaden im Swarm zu verhindern.
*   **Layer-basiertes visuelles System in der Showbox**:
    Die Showbox im Web-Dashboard stellt Arbeitsergebnisse, Textentwürfe und UI-Mockups in Echtzeit auf interaktiven Informationsebenen (Layern) dar. Jeder Layer besitzt eine feste farbliche Kennzeichnung und erzeugt beim Wechsel einen visuellen Highlight-Effekt (Blinken) an der zugehörigen Agenten-Gruppe (Worker links oder System-Agenten oben), um dem Nutzer sofort die Herkunft der Information anzuzeigen.
*   **Modulares Frontend**:
    Das glassmorphe Web-Dashboard wurde vollständig refaktoriert: Anstelle einer riesigen, monolithischen JavaScript-Datei im HTML-Code ist das UI nun in 7 hochgradig spezialisierte JavaScript-Module aufgeteilt. Dies gewährleistet eine saubere Trennung der Zuständigkeiten (core.js, chat.js, workspace.js, system_dashboard.js, worker_dashboard.js, worker_sidebar.js, dashboard.js) und vereinfacht die Wartung.
*   **Gemeinsames Langzeitgedächtnis**:
    Alle Agenten teilen sich eine persistente SQLite-Wissensbasis. SoulAG analysiert Chats und Interaktionen, speichert relevante Erkenntnisse ab und injiziert diese kontextabhängig via FAISS-Vektorsuche (oder mathematischem TF-IDF-Fallback bei fehlenden Bibliotheken) vor jedem LLM-Call direkt in den Systemprompt der Worker, um wiederholte Fehler zu vermeiden.
*   **Brainstorming-Modus mit strukturierter Agenten-Diskussion**:
    Über den Befehl `@bs [Thema]` wird eine koordinierte Agenten-Diskussion angestoßen. Alle Worker-Agenten analysieren das Problem parallel im Brainstorm-Modus, während GeneralAG anschließend die Ergebnisse konsolidiert, filtert und dem Nutzer in einem strukturierten Aktionsplan präsentiert.
*   **Visuelles Dashboard mit Live-Status**:
    Das Dashboard bietet Echtzeit-Observability für den gesamten Schwarm. Über ein glassmorphes Bento-Grid-Layout werden der Live-Status jedes Daemons (Heartbeat-Überwachung via `/api/metrics`), durchschnittliche Latenzen, Erfolgsraten, Tokenverbräuche sowie das Benutzer-Feedback-Panel direkt visualisiert.

---

## ✅ Abgeschlossene Phasen (Härtungs-Milestones)

Das System wurde in einem strukturierten Prozess um folgende Funktionen erweitert:

### 🛡️ Phase 1: Sicherheit & Gatekeeper
*   **Doppelte Genehmigung**: Jede Dateiänderung und Befehlsausführung durch Worker-Agenten erfordert ein explizites `APPROVED` von `WatchdogAG` (Strikte Einhaltung der 40-Zeilen-Regel & Clean Architecture) **und** `SecurityAG` (Schadcode- & Musterscan).
*   **Absoluter Systemdateien-Schutz**: Systemkritische Dateien (`index.html`, `run.sh`, `.env`, `src/gnom_hub/*`, `config/*` etc.) sind für Worker-Agenten **vollkommen tabu** (Zugriffsschutz greift direkt im Pfad-Validator; kein Bypass für Worker).
*   **Eskalationsrouting bei Unsicherheit**: Ist die LLM-Prüfung unentschlossen, wird eine Eskalation an `@user @SoulAG` im Chat ausgelöst. Freigaben können manuell durch das Eintragen in die Datenbank (`approved_security_writes` / `approved_security_commands`) autorisiert werden.

### 📊 Phase 2: Observability & Agent Health Dashboard
*   **Strukturiertes JSON-Logging & DB-Audit-Trail**: Alle Systemevents und LLM-Aufrufe (mit Latenzen, Tokenverbrauch, Kosten) werden strukturiert als JSON protokolliert und in einer indexierten `audit_log` Tabelle abgelegt.
*   **Agent Health API**: Der Endpunkt `/api/metrics` stellt Echtzeit-Statistiken bereit, welche die In-Memory-Metriken mit den Datenbank-Heartbeats (`last_seen`) aller 8 Agenten zusammenführen.
*   **Status-Dashboard**: Ein im Header verlinktes, glassmorphes Bento-Grid-Dashboard visualisiert farbcodiert den Status aller 8 Agenten (Grün = Alive/Online, Gelb = Warning/Hohe Fehlerrate/Heartbeat-Verzug, Rot = Dead/Offline) samt Latenzen, Erfolgsraten und Anfragen-Zähler. Automatisches Polling stoppt selbsttätig beim Verlassen der Ansicht.

### 🧠 Phase 3: SoulAG Memory Upgrade (Retrieval)
*   **Tokenbasiertes Jaccard-Retrieval**: Das statische Limit der letzten 20 Fakten wurde durch ein intelligentes Such- und Relevanz-Retrieval-System (`soul_retrieval.py`) ersetzt.
*   **Relevanzgewichtung**: Treffer in Faktenschlüsseln (Keys) werden doppelt so hoch gewichtet wie Treffer im Inhalt (Value), um präzise Kontextinjektionen zu ermöglichen.
*   **Automatischer Fallback**: Bieten Suchanfragen keinerlei Keyword-Überlappung (Score = 0), fällt das System nahtlos auf die neuesten Fakten zurück, um kontinuierlichen Kontext zu gewährleisten.

### 🔄 Phase 4: Error-Recovery & DB-Cleanup
*   **API-Failover & Key-Rotation**: Bei Ausfällen von Remote-LLMs rotieren die Provider-Keys oder der Router fällt transparent auf lokale/alternative Modelle (z.B. Offline-Llama) zurück.
*   **Automatisiertes DB-Cleanup**: Die Funktion `cleanup_old_data` löscht abgelaufene Fakten (älter als 30 Tage) und alte Chat-Nachrichten (älter als 7 Tage). Kritische Konfigurations-Chats (`role`) sowie geschützte Gedächtnisschlüssel (wie `active_preset` oder manuelle Sicherheitsfreigaben) bleiben dauerhaft erhalten.

### 🌐 Phase 5: Browser-Automation (Playwright)
*   **Containerisierte Playwright-Sandbox**: CoderAG kann echte Web-Interaktionen via Playwright ausführen. Die Ausführung erfolgt streng isoliert innerhalb eines Docker-Containers (`mcr.microsoft.com/playwright/python:v1.43.0-jammy`).
*   **Netzwerk-Isolation per Default**: Die Sandbox startet standardmäßig ohne Netzwerkverbindung (`--network=none`), um lokale Host-Ressourcen zu schützen.
*   **URL-Whitelisting & Gatekeeping**: Der Zugriff auf externe URLs ist standardmäßig blockiert und wechselt nur auf `--network=bridge`, wenn die Ziel-URL explizit in `approved_external_urls` freigegeben ist und die Ausführung sowohl von `WatchdogAG` als auch `SecurityAG` doppelt autorisiert wurde.

### 🧠 Phase 6: Erweitertes SoulAG Retrieval (Pipeline-Integration)
*   **Volle Pipeline-Integration**: Das Keyword-Matching-Retrieval (`soul_retrieval.py`) ist nun vollständig in die SoulAG-Pipeline (`soul.py`) integriert.
*   **Erweiterter Kontext (top_k=8)**: Statt starr die letzten 20 Fakten zu injizieren, sucht das System gezielt nach den bis zu 8 relevantesten Fakten aus der gesamten Historie der Datenbank und bettet diese dynamisch vor jeder Worker-Anfrage in den System-Prompt ein.

### 🔄 Phase 7: Multi-Agent Collaboration & @mentions
*   **Vollständige `@mentions`-Unterstützung**: GeneralAG erkennt und delegiert Aufgaben automatisch an CoderAG, ResearcherAG, WriterAG und EditorAG.
*   **Echtzeit-Kollaboration**: Koordiniertes und paralleles Arbeiten mehrerer Worker-Agenten an einem gemeinsamen Projekt.
*   **Visuelle Aktivitäts-Indikatoren**: Live-Anzeige der gerade aktiven Agenten im Frontend.

### 🛡️ Phase 8: Full System Integration & Tag Release
*   **Härtungstest**: Erfolgreicher End-to-End Test aller Phasen 1-7 gleichzeitig (Preset-Wechsel, doppelte Gatekeeper-Validierung, automatisierte Browser-Sandbox, SoulAG Retrieval).
*   **Release-Packaging**: Saubere Dokumentation und Git Version Tagging.

### 🔗 Phase 9: Swarm Intelligence & A2A Kommunikation
*   **Direkte Agent-to-Agent Kommunikation**: Agenten können sich gegenseitig über `@mentions` adressieren und asynchron dispatchen, wodurch komplexe, mehrstufige interne Diskussionen ermöglicht werden.
*   **Swarm-Coordination**: GeneralAG koordiniert mehrere Agenten parallel und führt Ergebnisse nach Beendigung aller Teilaufgaben automatisch in ein finales Dokument/Code-Artefakt zusammen.
*   **Visuelle Swarm-Aktivität**: Ein pulsierendes Swarm-Status-Banner im Dashboard zeigt in Echtzeit an, welche Agenten gerade miteinander kommunizieren und welcher Team-Workflow aktiv ist.

### 🔗 Phase 10: Advanced Swarm Intelligence & Dynamic Team Workflows
*   **Parallele Swarm-Koordination**: GeneralAG koordiniert die parallele Ausführung mehrerer Worker-Agenten gleichzeitig und führt deren Ergebnisse nach Abschluss automatisch in ein konsolidiertes Ergebnis zusammen.
*   **Git Automation**: Automatische Workspace-Commits nach erfolgreichen Swarm-Aktionen zur Gewährleistung der Projekthistorie.

### 🧠 Phase 11: Persistent Knowledge Base & Intelligent Learning System
*   **Persistente SQLite-Wissensbasis**: Erlernte Fakten und Benutzerpräferenzen werden sitzungsübergreifend in der SQLite-Datenbank persistiert.
*   **Semantisches LLM-Retrieval**: Das Suchsystem bewertet die Relevanz gespeicherter Fakten mithilfe eines LLM-basierten Filters (top_k=8) und injiziert diese kontextbezogen in die Agenten-Prompts, selbst bei fehlender Keyword-Übereinstimmung.

### 🔄 Phase 12: Agent Evolution & Self-Improvement
*   **Dynamische Evolution-Schleife**: Nach jedem großen `@job` analysiert GeneralAG den Verlauf und generiert konkrete Verbesserungsempfehlungen für die System-Prompts der beteiligten Worker-Agenten.
*   **Selbstverbesserungs-Log**: Die erlernten Optimierungsregeln werden als `evolution_{agent}_{hex}` in `soul_memory` persistiert, fließen bei zukünftigen Aufrufen automatisch in die Prompts ein und werden visuell im Dashboard unter "Agent Evolution & Self-Improvement Log" (Bento-Card mit lila Akzent) dargestellt.

### 💬 Phase 13: User Feedback Loop & Continuous Improvement
*   **Aktive Feedback-Aufforderung**: GeneralAG bittet den Nutzer nach jedem abgeschlossenen Swarm-Workflow im Chat aktiv um eine Bewertung des Ergebnisses.
*   **Dashboard Feedback-Panel**: Interaktive Buttons (Daumen hoch/runter) und ein Kommentarfeld im Bento-Grid ermöglichen die direkte Eingabe von Feedback.
*   **Feedback-basiertes Lernen**: SoulAG speichert das Feedback in der Datenbank, lässt es von GeneralAG analysieren, leitet daraus neue Verhaltensregeln ab und aktualisiert die Worker-Prompts dynamisch.

### ⚡ Phase 14: Advanced Swarm Execution & Integration Features
*   **Prompt Version Manager**: Vollautomatische Versionierung von System-Prompts bei Evolution-Iterationen mit Score-Tracking und automatischem Rollback auf die Vorgängerversion bei Leistungsdegradation.
*   **Graceful Fallback & Degradation**: Automatisches Routing bei blockierten oder fehlerhaften Agenten (z. B. Fallback von `CoderAG` auf `GeneralAG`), dokumentiert in einem persistenten Ausfall-Log (`gd_fallback.py`, `graceful_degradation.py`).
*   **Semantic Memory Retriever (Basis)**: TF-IDF Kosinus-Ähnlichkeit als Retrieval-Grundlage (`smr_math.py`, `smr_retrieve.py`) mit Pruning alter Einträge — wurde in Phase 15 durch FAISS-Vektor-Embeddings als primäres System abgelöst.
*   **Token Budget Manager (vorbereitet, nicht aktiv)**: Code für Echtzeit-Budgetüberwachung existiert (`token_economy.py`), ist aber noch nicht in den Router integriert. Derzeit kein aktives Budget-Enforcement bei LLM-Aufrufen.
*   **Strikte 40-Zeilen-Kompatibilität**: Alle neuen Module modularisiert und in Hilfsdateien aufgeteilt.

### 🛡️ Phase 15: Zero-Trust Capabilities, Local Embeddings & Custom Presets
*   **Zero-Trust-Autorisierung**: Ein temporäres Freigabesystem (Leases) mit 5-Minuten-Gültigkeit (TTL), das DB-gestützt arbeitet und wiederholte Dateizugriffe, Befehle und Browser-Aktionen ohne erneute LLM-Prüfungen durch WatchdogAG/SecurityAG per In-Memory-TTL-Cache mit O(1)-Lookup umgeht.
*   **Local Embeddings mit FAISS (aktiv)**: Semantische Ähnlichkeitssuche über `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim) und `faiss-cpu` als primäres Retrieval-System. Persistenter Embedding-Cache (`data/emb_cache.pkl`) und FAISS-Index (`data/soul_embeddings.index`) für sofortige Wiederverwendung. Automatischer Fallback auf TF-IDF-Kosinus-Ähnlichkeit bei fehlenden Bibliotheken.
*   **Custom Preset System**: Dynamisches Einscannen und Einmischen von benutzerdefinierten Presets als JSON-Dateien aus `/config/presets/` in das bestehende Preset-System.
*   **Strikte 40-Zeilen-Kompatibilität**: Konsequente Einhaltung der radikalen `40-Zeilen-Regel` im Backend für alle neuen Module (`capability_manager.py`, `embeddings.py`, `emb_faiss.py`, `emb_cache.py`, `preset_service.py`).
*   **Explainable Output**: Alle Agenten-Antworten liefern ein strukturiertes `ExplainableOutput`-Objekt mit Reasoning Chain, Confidence Score, Quellen und Ausführungszeit. Interne Calls nutzen `.content` (Rohtext), User-sichtbare Antworten `str()` (formatiertes Markdown).
*   **Performance Benchmarking**: Ein dediziertes Testskript zur automatischen Messung der Latenzen. Die Benchmarks belegen die massive Beschleunigung durch Caching und FAISS-Quantisierung (IndexIVFPQ):
    
    | Benchmark-Metrik | Kaltstart (Datenbank/FAISS) | Warmstart (In-Memory-Cache) | Speedup-Faktor |
    | :--- | :--- | :--- | :--- |
    | **🔐 Capability-Check** | ~0.70 ms | ~0.0004 ms | **~1.640x** |
    | **🧠 Semantische Suche** | ~2.19 ms | ~0.0003 ms | **~6.370x** |
    
    *Hinweis zur Optimierung: Durch die Umstellung auf FAISS IndexIVFPQ verringert sich der Speicherbedarf des persistenten Index um **~75%**.*

### 🛡️ Phase 16: System-Härtung, SoulAG-Präzision & Wächter-Automatisierung
*   **Orchestrierungsschutz für GeneralAG**: Vollständiger Entzug aller Tools, Datei- und Ausführungsrechte für den Koordinator auf Systemebene (Orchestrierung rein im Format `@AgentName -> Aufgabe`).
*   **Verhinderung von Over-Association bei SoulAG**: Integration von Mindestlängen-Filtern (Queries unter 25 Zeichen/4 Wörtern werden ignoriert) und reiner Fakten-Wert-Vektorisierung (Beseitigung von Präfix-Verschmutzung), um Fehl-Injektionen bei kurzen Eingaben wie "test" zu vermeiden.
*   **Auto-Freigaben für sichere Aktionen**: Automatisches Durchwinken risikofreier Schreibzugriffe im Workspace und freigegebener Terminalprogramme (z. B. `python3`, `pytest`, `git status`) zur Vermeidung lästiger manueller Abfragen.
*   **Echtzeit-PyPI-Download-Verifizierung**: Automatisierte API-Abfragen bei Paketinstallationen (`pip install`), um Download-Legitimität und Schadcode-Freiheit (0 registrierte Schwachstellen) direkt vorab im Netz zu prüfen.
*   **Denkprozess-Filterung (Security Bypass Fix)**: Dynamische Entfernung der `<think>`-Blöcke von DeepSeek-R1 aus maschinell verarbeiteten Ausgaben (Vermeidung von Gatekeeper-Bypasses durch Erwähnungen im Denkprozess) bei gleichzeitigem Erhalt des formatierten Details-Widgets im Chat-UI.
*   **Agenten-Limitierung (4/4-Regel)**: Begrenzung des Schwarms auf exakt 4 Worker- und 4 System-Agenten (mit automatischer Test-Bypass-Regel im Integrationsmodus), um unkontrolliertes Spawnen neuer Agenten zu blockieren.
*   **Performance-Optimierung der LLM-Konsole**: Umstellung sequentieller API-Anfragen im Frontend auf parallele `Promise.all`-Abfragen sowie Integration eines 30-Sekunden-Arbeitsspeicher-Caches mit 0,5s-Timeout für die Modell-Verfügbarkeit, um jegliche UI-Verzögerungen zu eliminieren.

### 🔄 Phase 17: Swarm-Stabilität & Loop-Prävention
*   **Mention-Tiefe begrenzen**: Reduzierung automatischer Kaskaden von Agenten-Erwähnungen auf ein Maximum von 3, um rekursive Endlosschleifen zu unterbinden.
*   **Hängende Jobs bereinigen**: Watcher-Erweiterung (`pulse_janitor`), der blockierte Worker-Agenten (Status busy über 5 Minuten) automatisch wieder auf online setzt.
*   **Transaktionssichere Preset-Wechsel**: Ausführen aller DB-Schreibzugriffe bei Preset-Änderungen in einer SQLite `BEGIN IMMEDIATE TRANSACTION`, um Race-Conditions mit parallel laufenden Agenten-Jobs zu verhindern.

### 🎨 Phase 18: Sidebar-Platzhalter & Header-Layout
*   **Sidebar Metriken-Verlagerung**: Verschieben der globalen Metriken (Tokens, Agents, Memory) zurück in die linke Sidebar in feinem Schriftdesign.
*   **Feste Platzhalter-Abstände**: Zwei Platzhalter mit einer festen Höhe von exakt 30px (50% der ursprünglichen Suchbox-Größe) umschließen das Metriken-Modul oben und unten.
*   **Symmetrische Navigationsleiste**: Zurücksetzen des linken Header-Bereichs auf das saubere Logo und Festlegen einer einheitlichen Breite von 86px (Vorlage: Workspace-Button) für alle Header-Navigations-Buttons mit zentriertem Text.

### 💾 Phase 19: Globale Header-Aktionen & Bereinigung lokaler Speicher-Buttons
*   **Navigations-Buttons im Header**: Hinzufügen von zwei 43px breiten (halb so breiten) Buttons in die Navigationsleiste:
    *   **Zurück (`↩`)**: Blättert die Seitenverläufe dynamisch rückwärts durch (`goBackView()` über `window.viewHistory`) und deaktiviert sich selbst, wenn kein Verlauf vorliegt.
    *   **Speichern (`💾`)**: Löst kontextbezogen den Speichern-Vorgang aus (die LLM-Keys/Routings im LLM-Panel, oder die Einstellungen im Agenten-Inspector in der Sidebar).
*   **Radikale Button-Bereinigung**: Vollständiges Entfernen aller redundanten lokalen "Speichern"- und "Apply & Save"-Buttons aus dem Dashboard und dem Agent-Inspector für ein sauberes, einheitliches Bedienkonzept.

---

## 🏗️ Kern-Architektur

Das Backend basiert auf FastAPI und stützt sich auf drei wesentliche Designentscheidungen:

### 1. Relationaler SQLite3-Speicher (WAL-Modus)
Sämtliche Agenten-Interaktionen, Chat-Verläufe und Zustandsdaten werden in einer lokalen SQLite3-Datenbank (`gnomhub.db`) im **Write-Ahead Logging (WAL)-Modus** gespeichert. Dies verhindert Concurrency-Konflikte bei parallelen Schreibzugriffen der Agenten, stellt Transaktionssicherheit sicher (`with conn:`) und läuft nativ auf allen Plattformen.

### 2. Prozess-Orchestrierung (psutil & PID-Dateien)
Das Management der Hintergrundprozesse erfolgt plattformunabhängig und sicher über `psutil`.
* Beim Starten eines Agenten wird eine PID-Datei unter `~/.gnom-hub/run/{agent_name}.pid` angelegt.
* Vor jeder Prozess-Aktion (wie dem Stoppen eines Agenten) liest der Prozess-Manager die PID-Datei aus und verifiziert die Kommandozeile (`cmdline`) des Prozesses. Dies verhindert, dass versehentlich fremde Prozesse beendet werden, die eine wiederverwendete PID erhalten haben.

### 3. FastAPI Lifespan-Hooks
Die Datenbank-Initialisierung (`init_db()`), das Seeding der Standard-Agenten und der Start der Hintergrund-Dienste sind fest an das Lifespan-Startup-Event von FastAPI gebunden. Beim Herunterfahren des Servers (z. B. durch SIGINT / Ctrl+C) führt uvicorn automatisch ein geordnetes, kaskadierendes Herunterfahren aus, welches alle Hintergrundprozesse beendet und verwaiste PID-Dateien löscht.

---

## 📐 Die 40-Zeilen-Regel

```
Modularität und Fokus: Die 40-Zeilen-Zielsetzung.
```

Gnom-Hub löst strukturelle Komplexität, indem es seine Codebasis extrem fokussiert und modular hält.
* **Zielsetzung:** Um unübersichtlichen Code und Monolithen zu vermeiden, war das Ziel ursprünglich, jedes interne Python-Modul in `src/gnom_hub/` auf maximal 40 Zeilen zu begrenzen.
* **Aktueller Stand:** Über 80 % aller 176 Python-Module halten sich weiterhin strikt an dieses Limit. Einige wenige komplexe Steuerungsdateien (insgesamt 35 Module, darunter `db.py` für die relationale SQLite-Schnittstelle, `gatekeeper.py` für die Sicherheitsprüfungen und `router_stage.py` für das LLM-Routing) sind im Zuge der Härtungsphasen angewachsen, um zusammengehörige Logik lesbar und wartbar in einer Datei zu belassen.
* **Worker-Einfachheit:** Worker wie `CoderAG` benötigen nach wie vor lediglich ein kurzes Python-Skript von ca. 8–10 Zeilen für ihre Registrierung und Polling-Schleife.

---

## 🤖 Die Agenten-Struktur

Gnom-Hub steuert 8 registrierte Agenten, aufgeteilt in koordinierende System-Agenten und spezialisierte Worker-Agenten:

### System-Agenten — halten das Haus sauber

| Agent | Modul | Beschreibung |
| :--- | :--- | :--- |
| **GeneralAG** | `generalAG.py` | Koordiniert die Ausführung, zerlegt `@job`-Aufgaben und synthetisiert Brainstorms |
| **SoulAG** | `soulAG.py` | Lernt den Schreibstil des Nutzers lautlos, baut das *FlexSoul*-Profil auf und injiziert es in Prompts |
| **WatchdogAG**| `watchdogAG.py` | Hüter der Systemintegrität. Schützt Systemdateien vor Zugriffen und überwacht die 40-Zeilen-Regel |
| **SecurityAG**| `securityAG.py` | Wächter über Code-Sicherheit. Scannt geschriebenen Code und Terminal-Befehle vorab auf Schadcode und Schwachstellen |

### Worker-Agenten — erledigen die Arbeit (durch Tags getriggert)

| Agent | Modul | Trigger | Spezialisierung |
| :--- | :--- | :--- | :--- |
| **CoderAG** | `coderAG.py` | `@code` | Code-Implementierung, Debugging und Ausführung (besitzt `run`-Rechte) |
| **WriterAG** | `writerAG.py` | `@write` | Entwerfen von Dokumentationen, Handbüchern, Artikeln und Texten |
| **ResearcherAG**| `researcherAG.py`| `@research`| Recherchen, Ausführung von Such-APIs und Überprüfung von Quellen |
| **EditorAG** | `editorAG.py` | `@edit` | Korrekturlesen, Stiloptimierung und finale Qualitätskontrolle |

---

## 🛠️ Agenten-Werkzeuge (Aktionen)

Die Hintergrund-Agenten von Gnom-Hub interagieren mit dem System, dem Dateisystem und externen Web-Diensten, indem sie spezifische Markdown-ähnliche Tags in ihrer LLM-Ausgabe erzeugen. Diese Aktionen werden geparst und sicher ausgeführt.

> [!TIP]
> **Aktions-Sandbox & Validierung:** Jede von einem Worker-Agenten angeforderte Aktion wird in Echtzeit abgefangen und muss die zweistufige Sicherheitsfreigabe (WatchdogAG & SecurityAG) durchlaufen, bevor sie ausgeführt wird.

| Werkzeug / Tag | Beschreibung | Berechtigungen | Beispiel |
| :--- | :--- | :--- | :--- |
| **`[READ: dateiname]`** | Liest den Inhalt einer Datei aus dem Workspace. | Alle Worker-Agenten | `[READ: index.html]` |
| **`[WRITE: dateiname]inhalt[/WRITE]`** | Erstellt oder überschreibt eine Datei im Workspace. | CoderAG, WriterAG, EditorAG, ResearcherAG | `[WRITE: hello.py]`<br>`print("Hallo")`<br>`[/WRITE]` |
| **`[SHELL: befehl]`** | Führt Terminal-Befehle (z. B. Tests oder Paketinstallationen) aus. | CoderAG (`run`-Recht) | `[SHELL: pytest tests/]` |
| **`[IMAGE: prompt]`** | Generiert ein KI-Bild und speichert es im Workspace. | WriterAG, CoderAG | `[IMAGE: futuristisches Dashboard-Logo]` |
| **`[BROWSER: aktions_json]`** | Steuert einen echten Playwright-Browser (Navigation, Klicks, Screenshots). | CoderAG (`godmode`-Recht) | `[BROWSER: {"action": "goto", "target": "https://example.com"}]` |
| **`<SHOWBOX:index>html_oder_json</SHOWBOX>`** | Rendert interaktive HTML-Präsentationen live im War Room Dashboard. | Alle Agenten | `<SHOWBOX:4>`<br>`<h3>Slide-Inhalt</h3>`<br>`</SHOWBOX>` |

---

## 🛡️ Sicherheit & Schutzmechanismen

Sicherheit ist in Gnom-Hub kein nachträgliches Add-on, sondern ein **fundamentales Architekturprinzip**. Da das System autonom agierende Agenten mit weitreichenden Werkzeugen ausstattet, wird jede Aktionen über eine strikte, mehrstufige Sicherheitsbarriere geleitet.

### 👮‍♂️ Aktive Gatekeeper: WatchdogAG & SecurityAG
Alle von Worker-Agenten (`CoderAG`, `ResearcherAG`, `WriterAG`, `EditorAG`) angeforderten Datei- und Befehlsaktionen werden in der zentralen Dispatcher-Schicht [action_handlers.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/action_handlers.py) abgefangen, analysiert und erst nach erfolgreicher Validierung ausgeführt.

#### 1. WatchdogAG (Pfad- und Integritätsschutz)
Der Watchdog schützt den Systemkern vor unbefugten Dateizugriffen und Manipulationen:
* **Absoluter Systemdateien-Schutz**: Systemkritische Dateien (`index.html`, `run.sh`, `.env`) und Verzeichnisse (`src/gnom_hub/`, `config/`, `scripts/`) sind für Worker-Agenten **vollkommen tabu**. Jeglicher Lese-, Schreib- oder Ausführungsversuch auf diese Pfade wird sofort unterbunden. Ein Zugriffsbypass über `approved_system_paths` existiert für Worker nicht.
* **Pfad-Validierung & Sandboxing**: Alle Dateipfade werden über `is_worker_blocked` in [path_validator.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/path_validator.py) normalisiert und in absolute Pfade aufgelöst (`os.path.realpath`). Versuche von Directory-Traversal-Attacken (z. B. mit `../`) werden im Keim erstickt. Jeder Pfad muss zwingend innerhalb des dafür vorgesehenen Workspace-Verzeichnisses (`WORKSPACE_DIR`) liegen.

#### 2. SecurityAG (Code- und Befehlsanalyse)
Die SecurityAG bewacht die Ausführungsebene und scannt Aktionen auf potenziell destruktive Absichten:
* **Inhalts-Prüfung**: Jeder Schreibzugriff (`[WRITE]`) eines Workers wird auf gefährliche Funktionen, Code-Muster oder Systemaufrufe untersucht (z. B. `rm -rf`, `eval(`, `os.system(`, `subprocess.`, `exec(`, `pickle.load`, `chmod 777`, `shutil.rmtree`).
* **Terminal-Überwachung**: Jedes Shell-Kommando (`[SHELL]`) wird vorab geparst. Unsafe-Commands (wie Netzwerk-Downloads via `curl` oder `wget`, Berechtigungsänderungen via `chmod 777` oder destruktive Systemkommandos) werden blockiert.

---

### 👑 CoderAG: Godmode unter strenger Kontrolle
Der `CoderAG` ist der mächtigste Worker im Schwarm. Er besitzt als einziger den `godmode`-Status und ist berechtigt:
* Shell-Kommandos auf Systemebene auszuführen (`[SHELL]`).
* Browser-Automationen über die Playwright-Schnittstelle zu steuern (`[BROWSER]`).

Obwohl der CoderAG diese weitreichenden Privilegien besitzt, wird er **lückenlos und ohne Ausnahmen** durch das Duo aus WatchdogAG und SecurityAG überwacht. Jeder seiner Befehle und jeder Dateizugriff wird derselben strikten Sicherheitsprüfung unterzogen. Ein „Ausbrechen“ aus dem zugewiesenen Workspace oder das Einschleusen destruktiver Befehle ist auch für den CoderAG im `godmode` unmöglich.

---

### 🚨 Eskalationskette & Freigaben bei Unsicherheit
Wenn eine Sicherheitsprüfung anschlägt oder ein Worker unbefugt auf geschützte Pfade zugreifen will:
1. **Sofortige Blockade**: Die Ausführung wird gestoppt, das angeforderte Tag im Antworttext wird durch eine Sicherheitsmeldung ersetzt.
2. **Chat-Eskalation**: Es wird ein System-Eintrag im Chat erzeugt, der den Operator (`@user`) und das übergeordnete Schwarmgedächtnis (`@SoulAG`) namentlich taggt und über den genauen Pfad bzw. Befehlsverstoß informiert.
3. **Manuelle Freigabe**: Eine Ausführung blockierter Ressourcen ist ausschließlich über manuelle Einträge in der SQLite-Datenbank durch den Administrator (User/SoulAG) möglich:
   * `approved_system_paths`: Whitelist für geschützte Pfade (nur für administrative Rollen).
   * `approved_security_writes`: Whitelist für geprüfte Dateiinhalte.
   * `approved_security_commands`: Whitelist für autorisierte Terminal-Befehle.

---

### 🔒 Immunität der System-Agenten (Preset-Isolation)
Das Preset-System (zur Fokus-Ausrichtung des Schwarms) ist strikt auf der Anwendungsebene isoliert:
* **Fokus-Wechsel nur auf Worker-Ebene**: Ein Preset-Wechsel verändert die Prompt-Modifikatoren und LLM-Modelle **ausschließlich** für die 4 Worker-Agenten (`ResearcherAG`, `WriterAG`, `EditorAG`, `CoderAG`).
* **Unantastbare Systemebene**: Die 4 administrativen System-Agenten (`SoulAG`, `GeneralAG`, `WatchdogAG`, `SecurityAG`) behalten permanent ihre feste Konfiguration (Standardmodelle auf High-End-Tier `stage_3`, unveränderliche System-Prompts, unbeschränkte Systemrechte). Ein Preset-Wechsel kann somit niemals die Kontrollinstanzen der Plattform manuell schwächen.

---

## 💬 Befehle

| Befehl | Aktion |
| :--- | :--- |
| `@bs [Thema]` | 4 Worker laufen parallel; GeneralAG synthetisiert die Ergebnisse zu einem Aktionsplan |
| `@job [Aufgabe]` | GeneralAG zerlegt die Aufgabe in Teilschritte und koordiniert die Worker-Ausführung |
| `@research [Suche]`| Alle Worker werden parallel abgefragt für schnelles, vielseitiges Feedback |
| `@code / @write / @edit` | Direkte Zuweisung an einen bestimmten Spezialisten |
| `@git [Befehl]` | Führt Git-Befehle direkt im aktiven Projekt-Workspace aus |
| `@publish` | Bereitstellung des aktuellen Stands via SFTP auf deinem konfigurierten Server |
| `@@project [Name]` | Wechselt das active Workspace-Projekt |
| `@@status` | Zeigt den aktuellen Laufzeit-Status (RUNNING/STOPPED) aller Agenten an |
| `@@clear` | Leert den Chatverlauf im Dashboard |
| `@free` | Bricht alle aktiven Jobs ab und setzt blockierte Agenten zurück |
| **Nuke** 💣 | Halte das War Room Logo für 2 Sekunden gedrückt, um einen Hard Reset aller Hintergrunddienste auszulösen |

---

## 🚀 Quick Start

### 1. Installation
Klone das Repository und führe das Setup-Skript aus:
```bash
git clone https://github.com/landjunge/gnom-hub.git
cd gnom-hub
bash scripts/install.sh
```
Dies richtet eine lokale virtuelle Umgebung (`.venv`) ein und installiert die 7 Kern-Abhängigkeiten: `fastapi`, `uvicorn`, `pydantic`, `requests`, `python-dotenv`, `mcp` und `psutil`.

### 2. Konfiguration
Kopiere das Template für die `.env`-Datei und trage deine API-Keys (OpenRouter oder DeepSeek) ein:
```bash
cp config/.env.example config/.env
```

### 3. Ausführen
Starte den FastAPI-Server:
```bash
./run.sh
```
Öffne **[http://127.0.0.1:3002](http://127.0.0.1:3002)**, um den War Room zu betreten.

---

## 📁 Projektstruktur

```text
gnom-hub/
├── src/gnom_hub/        # 174 Python-Module (Backend)
│   ├── hub_app.py       # FastAPI App & Lifespan-Orchestrierung
│   ├── db/              # SQLite3-Datenbank (WAL-Modus) und Repositories
│   ├── proc_mgr.py      # Prozess-Manager (psutil & PID-Dateien)
│   ├── path_validator.py# Workspace-basierte Pfadvalidierung
│   ├── log.py           # Zentrales Logging-Framework
│   ├── router/          # LLM-Routing und SmartRouter (Multi-Provider)
│   ├── frontend/        # Modularisiertes glassmorphes Dashboard (HTML, CSS, modularisierte static JS-Module)
│   └── routes_*.py      # API-Endpunkte
├── agents/              # 8 Agenten-Definitionen (Startup-Skripte der Daemons)
├── config/              # Lokale Umgebungskonfigurationen (Presets, Token-Budgets)
├── scripts/             # Setup- & Hilfs-Skripte
├── docs/                # Berichte und Dokumentation
├── pyproject.toml       # Ruff-Konfiguration & Abhängigkeiten
```

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Kreative Pionierin der ersten Stunde. Mutter der "Vier Säulen". Legte das philosophische Fundament, als das Projekt noch reines Chaos war.

**Antigravity (Google DeepMind)**
Architekt der Härtungsphase. Spezifische Beiträge:
* Aufteilung übergroßer Module zur strikten Durchsetzung der 40-Zeilen-Regel im Backend
* Sicherung der Pfad-Zugriffe über Workspace-basierte Validierung (`path_validator.py`)
* Migration der JSON-Speicherung auf eine transaktionssichere SQLite3-Datenbank (WAL-Modus)
* Implementierung des `psutil`-Prozessmanagers mit PID-Dateien und Lifespan-Integration
* Integration von SFTP-Bereitstellung, CORS-Einschränkung auf Localhost und des `log.py`-Frameworks
* Implementation der Härtungs-Phasen 1-16 (darunter Zero-Trust Capabilities, local Embeddings mit FAISS & TF-IDF-Fallback, Custom Presets, Prompt Versioning, Swarm Intelligence, User Feedback Loop, R1-Think-Block-Filterung, extrem performantes In-Memory/SQLite-Caching und Härtung des Schwarms durch die 4/4-Agenten-Begrenzung)
* Modularisierung des Frontend-Codes in 7 spezialisierte, entkoppelte JavaScript-Dateien zur Durchsetzung von Separation-of-Concerns
* Optimierung der LLM-Konsolen-Performance durch parallele API-Abfragen und serverseitiges Caching der Modelllisten

---

## ⚖️ Lizenz

[Private Use](LICENSE) — Kostenfrei für den persönlichen, nicht-kommerziellen Gebrauch. Kommerzielle Nutzung bedarf der schriftlichen Genehmigung.
