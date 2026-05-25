# 🧠 GNOM-HUB — Minimalistisches Multi-Agenten-System

Gnom-Hub ist ein **lokal-first** Multi-Agenten-System mit fester Topologie. Statt dynamischer, schwer kontrollierbarer Agenten-Schwärme besteht das System aus **genau 8 Agenten** (4 System-Agenten + 4 Worker-Agenten). 

Jedes Backend-Modul unterliegt der strengen **40-Zeilen-Regel** (unter `src/gnom_hub/`). Dies erzwingt Klarheit, einfache Testbarkeit und verhindert monolithischen Code.

---

## 🎯 Philosophie

- **Local-First**: Alles läuft lokal. Keine Cloud-Orchestrierung.
- **Feste Topologie**: Nur 8 definierte Agenten — keine unkontrollierte Agenten-Explosion.
- **Defensive Architektur**: Clean Architecture + 40-Zeilen-Regel als hartes Prinzip.
- **Pragmatismus**: Keine autonomen Endlosschleifen. Der Mensch behält die Kontrolle.
- **Sicherheit durch Design**: System-Agenten überwachen und schützen, Worker arbeiten eingeschränkt.

---

## 🏗️ Architektur

```mermaid
graph TD
    User([Nutzer]) -->|POST /api/chat| Hub[FastAPI Hub]
    Hub -->|Asynchroner Thread| Soul[SoulAG]
    Soul -->|Fakten-Extraktion| DB[(SQLite)]
    Hub -->|Routing| Router[Smart Router]
    DB -->|Kontext-Injektion| Router
    State[(State)] -->|Aktives Preset| Router
    Router -->|LLM + Prompt| LLM[Ollama / OpenRouter / DeepSeek]
    Router -->|Tool-Ausführung| Action[Action Handlers]
    Action -->|Permission-Check| Perm[agent_definitions.py]
```

---

## 🤖 Die 8 Agenten (Topologie)

Die vollständige Definition aller Agenten-Eigenschaften, Prompts und Rechte erfolgt zentral in [agent_definitions.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/agent_definitions.py).

### System-Agenten (Administrative Rechte)
Diese Agenten steuern die Plattform und besitzen administrative Berechtigungen (`read`, `write`, `run`, `godmode`, `crawl`, `desktop`, `evolve`):
1. **SoulAG**: Das passive Gedächtnis des Schwarms. Lernt asynchron Präferenzen des Nutzers und stellt diese als Kontext bereit.
2. **GeneralAG**: Der zentrale Koordinator. Analysiert komplexe `@job`-Anfragen, warnt bei Regelverstößen und delegiert Aufgaben im Format `@AgentName -> Aufgabe`.
3. **WatchdogAG**: Überwacht zyklisch die Einhaltung der Dateigrenzen (40-Zeilen-Regel) und die Integrität des Workspace.
4. **SecurityAG**: Validiert die Integrität der Workspace-Dateien und führt Risikoprüfungen durch.

### Worker-Agenten (Eingeschränkte Rechte)
Worker arbeiten ausschließlich im Workspace und besitzen standardmäßig nur Lese-, Schreib- und Chat-Berechtigungen (`read`, `write`, `@job`):
5. **CoderAG**: Entwickelt und debuggt Code. Besitzt als einziger Worker den `godmode`-Status, welcher die Playwright-Browsersteuerung und die Ausführung von Shell-Befehlen freischaltet.
6. **ResearcherAG**: Recherchiert im Web, crawlt Dokumentationen und prüft Quellen.
7. **WriterAG**: Erstellt strukturierte Entwürfe, Dokumentationen und Texte.
8. **EditorAG**: Übernimmt Lektorat, Korrekturschleifen und die finale Qualitätskontrolle.

---

## 🎛️ Das Preset-System (6 Modi)

Das Preset-System erlaubt das Umschalten des gesamten Schwarms auf ein bestimmtes Aufgabengebiet. Die Auswahl erfolgt über das Dropdown-Menü im Dashboard.

### Die 6 vordefinierten Workflow-Modi:
1. 💻 **Web Development**: Fokus auf semantisches HTML5, native Web-APIs, Barrierefreiheit (ARIA) und performantes CSS.
2. 🎨 **Graphic Design**: Fokus auf SVGs, Layout-Grids, Typografie und harmonische Farbpaletten (HSL).
3. 🎵 **Audio Production**: Fokus auf Web Audio API, DSP-Algorithmen und Sound-Synthese.
4. 🎬 **Video Production**: Fokus auf Canvas-Animationen, CSS-Transitions und Render-Pipelines.
5. ✍️ **Marketing & Copy**: Fokus auf SEO-Keywords, AIDA-Modelle und zielgruppengerechte Tonalität.
6. 🔍 **Research & Analysis**: Fokus auf Faktenprüfung, akademische Quellen und statistische Datenanalyse.

### Technische Umsetzung:
* Der Preset-Wechsel speichert den aktuellen Modus in der Tabelle `state` in der SQLite-Datenbank.
* Bei jeder LLM-Anfrage lädt der Router den passenden Prompt-Modifikator aus der Konfiguration und stellt ihn dem System-Prompt des Workers voran.
* LLM-Einstellungen und Modell-Auswahlen werden pro Preset benutzerdefiniert gespeichert und beim Umschalten automatisch wiederhergestellt.

---

## 🧠 SoulAG: Technisches Gedächtnis & Asynchroner Kontext-Injektor

[soul.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/soul.py) arbeitet passiv im Hintergrund und greift nicht direkt in den Chatverlauf ein. Der Ablauf ist vollkommen asynchron gestaltet:

1. **Passives Mitlesen**: Sobald eine Nachricht des Typs `user` im Chat registriert wird, startet ein entkoppelter Hintergrund-Thread (`threading.Thread`).
2. **Extraktion per LLM**: Der Thread sendet die Nachricht an das LLM mit der strikten Anweisung, wichtige Fakten, Vorlieben und Dateipfade zu extrahieren und ausschließlich als JSON-Array zurückzugeben:
   ```json
   [{"key": "fact_key", "value": "fact_value"}]
   ```
3. **Relationale Persistenz**: In [db.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/db.py) werden diese Fakten in der Tabelle `soul_memory` gespeichert:
   ```sql
   CREATE TABLE IF NOT EXISTS soul_memory (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       key TEXT NOT NULL,
       value TEXT NOT NULL,
       timestamp TEXT NOT NULL,
       UNIQUE(key)
   );
   ```
   Dank `UNIQUE(key)` überschreibt ein neuerer Fakt mit demselben Schlüssel den alten Wert atomar (`INSERT OR REPLACE`).
4. **Kontext-Injektion**: Vor jeder Anfrage an einen Worker-Agenten ruft der Router die bis zu 20 neuesten Einträge aus `soul_memory` ab und hängt sie strukturiert an das System-Prompt an:
   ```
   === RELEVANTE INFORMATIONEN ===
   - user_name: Max Mustermann
   - prefer_language: German
   - active_preset: Web Development
   ```
   Dadurch wissen alle Worker-Agenten sofort über den aktuellen Kontext Bescheid, ohne dass dieser manuell im Chat wiederholt werden muss.
5. **Preset-Interaktionen**: Auch Preset-Wechsel werden über `save_soul_fact("active_preset", preset)` als Fakt in `soul_memory` abgelegt, sodass nachfolgende Worker-Agenten über den Kontext-Injektor den aktuellen System-Fokus mitgeteilt bekommen.

---

## 🛡️ Sicherheit & Schutzmechanismen

Sicherheit ist in Gnom-Hub kein nachträgliches Add-on, sondern ein **fundamentales Architekturprinzip**. Da das System autonom agierende Agenten mit weitreichenden Werkzeugen ausstattet, wird jede Aktion über eine strikte, mehrstufige Sicherheitsbarriere geleitet.

```mermaid
graph TD
    Worker[Worker-Agent: z.B. CoderAG] -->|Aktion angefordert| Dispatcher[action_handlers.py]
    Dispatcher -->|Pfad- & Integritäts-Check| Watchdog[WatchdogAG]
    Dispatcher -->|Code- & Pattern-Check| Security[SecurityAG]
    
    Watchdog -->|Verstoß erkannt| Block[Aktion blockieren + Chat-Warnung an @user & @SoulAG]
    Security -->|Gefahr erkannt| Block
    
    Watchdog -->|Pfad ok / Freigabe| Exec[Sichere Ausführung im Workspace]
    Security -->|Inhalt ok / Freigabe| Exec
```

---

### 👮‍♂️ Aktive Gatekeeper: WatchdogAG & SecurityAG
Alle von Worker-Agenten (`CoderAG`, `ResearcherAG`, `WriterAG`, `EditorAG`) angeforderten Datei- und Befehlsaktionen werden in der zentralen Dispatcher-Schicht [action_handlers.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/action_handlers.py) abgefangen, analysiert und erst nach erfolgreicher Validierung ausgeführt.

#### 1. WatchdogAG (Pfad- und Integritätsschutz)
Der Watchdog schützt den Systemkern vor unbefugten Dateizugriffen und Manipulationen:
* **Absoluter Systemdateien-Schutz**: Systemkritische Dateien (`index.html`, `run.sh`, `.env`) und Verzeichnisse (`src/gnom_hub/`, `config/`, `scripts/`) sind für Worker-Agenten **vollkommen tabu**. Jeglicher Lese-, Schreib- oder Ausführungsversuch auf diese Pfade wird sofort unterbunden.
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
3. **Manuelle Freigabe**: Eine Ausführung blockierter Ressourcen ist ausschließlich über manuelle Einträge in der SQLite-Datenbank (Tabelle `state`) durch den Administrator möglich:
   * `approved_system_paths`: Whitelist für geschützte Pfade.
   * `approved_security_writes`: Whitelist für geprüfte Dateiinhalte.
   * `approved_security_commands`: Whitelist für autorisierte Terminal-Befehle.

---

### 🔒 Immunität der System-Agenten (Preset-Isolation)
Das Preset-System (zur Fokus-Ausrichtung des Schwarms) ist strikt auf der Anwendungsebene isoliert:
* **Fokus-Wechsel nur auf Worker-Ebene**: Ein Preset-Wechsel verändert die Prompt-Modifikatoren und LLM-Modelle **ausschließlich** für die 4 Worker-Agenten (`ResearcherAG`, `WriterAG`, `EditorAG`, `CoderAG`).
* **Unantastbare Systemebene**: Die 4 administrativen System-Agenten (`SoulAG`, `GeneralAG`, `WatchdogAG`, `SecurityAG`) behalten permanent ihre feste Konfiguration (Standardmodelle auf High-End-Tier `stage_3`, unveränderliche System-Prompts, unbeschränkte Systemrechte). Ein Preset-Wechsel kann somit niemals die Kontrollinstanzen der Plattform manipulieren oder schwächen.

---


## 🚦 Entwicklungsstand (Ehrlich & Konkret)

### Was voll funktionsfähig ist:
* [x] **Prozessmanagement**: Zuverlässiger Start, Stopp und Statusabgleich der 8 Hintergrund-Agenten via `psutil` und PID-Dateien unter `~/.gnom-hub/run/`.
* [x] **Datenkonsistenz**: Transaktionssichere Speicherung aller Chats, Agenten-Zustände und Fakten in SQLite (WAL-Modus).
* [x] **Preset-Steuerung**: Dynamische Anpassung von Prompts und LLM-Modellen je nach Preset ohne Server-Neustart.
* [x] **Gedächtnis (SoulAG)**: Asynchrones Mitlernen von Benutzereingaben und automatische Kontext-Injektion.
* [x] **Ausführungsschutz**: Validierung von Dateipfaden auf den aktiven Workspace.

### Was in Arbeit / geplant ist:
* [ ] **MCP-Erweiterung**: Dynamische Registrierung und Anbindung externer Model Context Protocol (MCP) Server ist noch rudimentär.
* [ ] **Erweiterte Sandbox**: Derzeit sind Dateizugriffe außerhalb des Workspace selbst für den `godmode` des CoderAG stark eingeschränkt.
* [ ] **Browser-Automation**: Die Playwright-Schnittstelle im Backend ist vorbereitet, im Standard-Setup jedoch deaktiviert.

---

## 🚀 Schnellstart

1. **API-Schlüssel eintragen**:  
   Kopieren Sie `config/.env.example` nach `config/.env` und tragen Sie Ihre API-Schlüssel (z. B. für OpenRouter oder DeepSeek) ein.

2. **Server & Agenten starten**:  
   Führen Sie das Start-Skript [run.sh](file:///Users/landjunge/Documents/AG-Flega/run.sh) aus:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

3. **Dashboard aufrufen**:  
   Öffnen Sie im Webbrowser: **[http://127.0.0.1:3002](http://127.0.0.1:3002)**

---
**Projektstatus:** Mai 2026 — Experimenteller, funktionsfähiger Prototyp für Entwicklung und Forschung.