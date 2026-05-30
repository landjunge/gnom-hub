# 🧠 GNOM-HUB

> **8 Agenten. ~7500 Zeilen. 176 Module. Null Toleranz für Bloat.**
> *Ein lokales Multi-Agenten-Orchestrierungssystem mit defensiver Zero-Trust-Architektur und modularisiertem War Room Dashboard.*

[![License](https://img.shields.io/badge/Lizenz-Private_Use-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![Agents](https://img.shields.io/badge/Agenten-8-blueviolet.svg)](#)
[![Lines of Code](https://img.shields.io/badge/Zeilen_Code-~7500-blue.svg)](#)
[![Modules](https://img.shields.io/badge/Module-176-blue.svg)](#)
[![Linting](https://img.shields.io/badge/Linting-Ruff-orange.svg)](#)

---

🇩🇪 **Deutsch (README.de.md)** • 🇬🇧 **[English (README.md)](README.md)**

---

<img src="docs/warroom_real_full.png" alt="War Room – Gesamtübersicht" width="100%">

---

## Was ist Gnom-Hub?

Gnom-Hub ist ein lokales Multi-Agenten-System mit einer klaren Struktur von **176 Python-Modulen**. Es bietet einen leichtgewichtigen Orchestrator ohne aufgeblähte Frameworks, der vollständig lokal läuft, kein schwerfälliges Docker benötigt und die Agenten über ein Web-Dashboard namens **War Room** steuert.

> [!IMPORTANT]
> **Bewusster Minimalismus:** Gnom-Hub ist auf Einfachheit und maximale Performance ausgelegt. Das System ist bewusst **nicht** dafür konzipiert, Hunderte von Agenten zu steuern, sondern dient der effizienten Orchestrierung einer kleinen, hochspezialisierten und überschaubaren Gruppe von Agenten.

---

## 🔮 Die Vision: SuperGNOM & GNOM-HUB

GNOM-HUB ist kein gewöhnlicher KI-Chatbot und auch kein klassisches Multi-Agenten-System. Es ist die **Fabrik ("Schmiede")**, in der ein **SuperGNOM** über sogenannte **Presets** (Konfigurations-Profile) definiert, trainiert und geformt wird. GNOM-HUB bietet eine strukturierte Entwicklungsumgebung, in der genau acht feste Agenten mit klar definierten Rollen zusammenarbeiten. Vier davon sind administrative System-Agenten, die sich um Sicherheit, Gedächtnis, Überwachung und Koordination kümmern.

Der Kern der Idee ist nicht, immer komplexer oder größer zu werden. Stattdessen dient die Fabrik GNOM-HUB dazu, die Agenteneigenschaften und das Schwarmverhalten über Presets exakt zu kalibrieren und daraus das stabile, spezialisierte KI-System – den **SuperGNOM** – zu kompilieren (zu "backen").

Während die Fabrik GNOM-HUB die flexible, lernende Werkstatt ist, ist der **SuperGNOM** das fertige Produkt: unveränderbar, stabil und auf einen bestimmten Menschen oder eine konkrete Aufgabe zugeschnitten. Ein SuperGNOM soll im Produktiveinsatz nicht ständig dazulernen und sich verändern, sondern verlässlich, kontrollierbar und vorhersagbar bleiben.

### 🏗️ Workflow: Von der Fabrik zum Produkt (Kompilierung)

```mermaid
graph TD
    subgraph Werkstatt [GNOM-HUB Fabrik]
        P[Presets-Konfiguration] -->|Definiert Schwarm| GH[Entwicklungs-Schwarm: 8 Agenten]
        GH -->|Eigenschaften & Lernen| DB[(gnomhub.db)]
    end
    
    subgraph Compiler [Automatisierter Exporter]
        GH -->|Chat-Befehl: @bake| C[Exporter / Compiler]
        DB -->|Prüft & reduziert Chat-Verlauf auf 1000 Zeilen| C
        C -->|Friert aktive Prompts ein| AD[agent_definitions.py]
        C -->|Erzeugt SHA-256 Hashes| M[manifest.json]
    end

    subgraph Endprodukt [Portabler SuperGNOM]
        AD --> SG[SuperGNOM Laufzeitumgebung]
        M -->|Integritätsprüfung beim Start| SG
    end
```

### 🧬 System-Topologie & Gedächtnis-Isolation

```mermaid
graph TD
    U[Benutzer Chat-Eingabe] -->|Sendet Befehl| G[GeneralAG - Orchestrator]
    
    subgraph System [System- & Wächter-Schicht]
        G -->|Regelüberwachung| W[WatchdogAG]
        G -->|Schadcodescan| S[SecurityAG]
        G -->|Liest/Schreibt Fakten| So[SoulAG]
    end

    subgraph Workers [Worker-Schicht]
        G -->|Delegiert: @AgentenName| C[CoderAG]
        G -->|Delegiert: @AgentenName| Wr[WriterAG]
        G -->|Delegiert: @AgentenName| R[ResearcherAG]
        G -->|Delegiert: @AgentenName| E[EditorAG]
    end

    subgraph Memory [Langzeitgedächtnis & Scopes]
        So -->|Injiziert globale Vorlieben| GS[(Globaler Vektor-Scope)]
        C -.->|Isolierte Abfrage| MC[(Coder Vektor-Scope)]
        Wr -.->|Isolierte Abfrage| MWr[(Writer Vektor-Scope)]
        R -.->|Isolierte Abfrage| MR[(Researcher Vektor-Scope)]
        E -.->|Isolierte Abfrage| ME[(Editor Vektor-Scope)]
        GS -.->|Vererbt an| MC
        GS -.->|Vererbt an| MWr
        GS -.->|Vererbt an| MR
        GS -.->|Vererbt an| ME
    end
```

### 📊 Ist-Zustand (Status Quo)
- **SuperGNOM-Modus (`SUPERGNOM_MODE`)**: In der Konfiguration implementiert. Schaltet das dynamische Lernen und Prompt-Evolution ab, um ein stabiles und vorhersagbares Systemverhalten im Produktiveinsatz zu garantieren.
- **Isolierte Agenten-Gedächtnis-Bereiche (Isolated Memory Scopes)**: Implementiert für alle Worker-Agenten (`CoderAG`, `WriterAG`, `ResearcherAG`, `EditorAG`). Jeder Agent besitzt einen physikalisch getrennten FAISS-Vektorindex und SQLite-Filter, um eine gegenseitige Rollenverseuchung (Faktenleaks) zu verhindern.
- **SuperGNOM `@bake` Exporter (Compiler)**: Automatisiertes Einfrieren der evolvierten Prompts, Bereinigung der SQLite-Datenbank (Chats limitiert auf letzte 1000 Zeilen), Generierung des SHA-256 Hashes `manifest.json` zur Startup-Integritätsprüfung.
- **Passives Notfall-Backup-Archiv**: Eine passive historische Datenbank (`passive_archive.db`), in der sämtliche Interaktionen und Fakten transaktionssicher dupliziert werden, abfragbar bei Gedächtnisverlust über `@emergency` bzw. `@notfall`.

### 📝 Was noch getan werden muss (Roadmap / ToDo)
- **Spezifische UI-Layouts**: Implementierung optimierter Templates für spezifische Anwendungsfälle (z. B. barrierefreies Chat-UI oder Headless-API-Runner).
- **Single-Click Docker- & Binary-Exporte**: Kompilierung der SuperGNOM-Laufzeitumgebung in ein eigenständiges Binary oder Docker-Image.

---

## 🚀 Features (Funktionsumfang)

Gnom-Hub kombiniert eine robuste Multi-Prozess-Orchestrierung mit einem interaktiven Web-Interface. Die wichtigsten Features umfassen:

*   **Automatisches intelligentes Routing**:
    Der LLM-Router (`router.py`) leitet Anfragen dynamisch an das am besten geeignete Modell (z. B. DeepSeek-Reasoner, Claude, GPT) weiter. Bei API-Ausfällen oder Netzwerksperren greift das System vollautomatisch auf konfigurierte lokale Fallbacks (wie eine Offline-Llama-Instanz über Ollama) zurück, um Blockaden im Swarm zu verhindern.
*   **Layer-basiertes visuelles System in der Showbox**:
    Die Showbox im Web-Dashboard stellt Arbeitsergebnisse, Textentwürfe und UI-Mockups in Echtzeit auf interaktiven Informationsebenen (Layern) dar. Jeder Layer besitzt eine feste farbliche Kennzeichnung und erzeugt beim Wechsel einen visuellen Highlight-Effekt (Blinken) an der zugehörigen Agenten-Gruppe (Worker links oder System-Agenten oben), um dem Nutzer sofort die Herkunft der Information anzuzeigen.
*   **Modulares Frontend**:
    Das glassmorphe Web-Dashboard wurde vollständig refaktoriert: Anstelle einer riesigen, monolithischen JavaScript-Datei im HTML-Code ist das UI nun in 9 hochgradig spezialisierte JavaScript-Module aufgeteilt. Dies gewährleistet eine saubere Trennung der Zuständigkeiten (core.js, chat.js, workspace.js, system_dashboard.js, worker_dashboard.js, worker_sidebar.js, dashboard.js, showbox.js, showbox-buttons.js) und vereinfacht die Wartung.
*   **Gemeinsames Langzeitgedächtnis**:
    Alle Agenten teilen sich eine persistente SQLite-Wissensbasis. SoulAG analysiert Chats und Interaktionen, speichert relevante Erkenntnisse ab und injiziert diese kontextabhängig via FAISS-Vektorsuche (oder mathematischem TF-IDF-Fallback bei fehlenden Bibliotheken) vor jedem LLM-Call direkt in den Systemprompt der Worker, um wiederholte Fehler zu vermeiden.
*   **Brainstorming-Modus mit strukturierter Agenten-Diskussion**:
    Über den Befehl `@bs [Thema]` wird eine koordinierte Agenten-Diskussion angestoßen. Alle Worker-Agenten analysieren das Problem parallel im Brainstorm-Modus, während GeneralAG anschließend die Ergebnisse konsolidiert, filtert und dem Nutzer in einem strukturierten Aktionsplan präsentiert.
*   **Visuelles Dashboard mit Live-Status**:
    Das Dashboard bietet Echtzeit-Observability für den gesamten Schwarm. Über ein glassmorphes Bento-Grid-Layout werden der Live-Status jedes Daemons (Heartbeat-Überwachung via `/api/metrics`), durchschnittliche Latenzen, Erfolgsraten, Tokenverbräuche sowie das Benutzer-Feedback-Panel direkt visualisiert.

---

## ✅ Abgeschlossene Phasen (Härtungs-Milestones)

Die Entwicklungsschritte im Überblick:

*   **🛡️ Phase 1: Sicherheit & Gatekeeper**
    *   Doppelte Freigabe (`WatchdogAG` + `SecurityAG`) für alle Datei-Schreibzugriffe und Shell-Befehle.
    *   Strikter Zugriffsschutz auf systemkritische Systemdateien.
*   **📊 Phase 2: Observability & Health**
    *   Strukturiertes JSON-Logging aller System-Events in SQLite.
    *   Glassmorphes Bento-Grid-Dashboard für Live-Status.
*   **🧠 Phase 3 & 6: Wissensbasis & Retrieval**
    *   Intelligente Fakten-Suche (Schlüssel-Übereinstimmung gewichtet doppelt).
    *   Dynamisches Injezieren der top 8 relevantesten Fakten vor jedem LLM-Call.
*   **🔄 Phase 4: Recovery & Cleanup**
    *   LLM-Key-Rotation und nahtloses Ausweichen auf lokale Ollama-Modelle.
    *   Automatisches Löschen alter Chats (>7 Tage) und Fakten (>30 Tage).
*   **🌐 Phase 5: Browser-Automation (Playwright)**
    *   Playwright-Browseraktionen laufen in isoliertem Docker-Container.
    *   Standardmäßig offline (`--network=none`), Bridge-Netzwerk nur nach URL-Freigabe.
*   **🔄 Phase 7 & 8: Kollaboration & Härtung**
    *   Aufgabenverteilung über `@AgentenName -> Aufgabe`.
    *   Gleichzeitiger Stress-Test aller Features & Release-Tagging.
*   **🔗 Phase 9 & 10: Swarm-Comms & Git**
    *   Direkte Agent-to-Agent Kommunikation im Chat.
    *   Automatische Workspace-Commits nach erfolgreichen Swarm-Aufgaben.
*   **🧠 Phase 11-13: Kontinuierliches Lernen & Feedback**
    *   GeneralAG erzeugt Verhaltensregeln zur Selbstoptimierung (`evolution_*`).
    *   User-Feedback (Daumen hoch/runter + Kommentar) beeinflusst Agentenverhalten.
*   **⚡ Phase 14: Versionierung & Fallbacks**
    *   Versionierung von System-Prompts bei Evolution mit Rollback-Funktion.
    *   Automatisches Rerouting blockierter Aufgaben an Ersatz-Agenten.
*   **🛡️ Phase 15: Zero-Trust Leases & FAISS**
    *   Lokale Vektorsuche via FAISS und `sentence-transformers`.
    *   Temporäre Berechtigungen (TTL-Leases) beschleunigen sich wiederholende Zugriffe.
*   **🛡️ Phase 16: Systemhärtung & Wächter**
    *   GeneralAG darf keine Dateien schreiben oder Befehle ausführen.
    *   Strikte Einhaltung des 4/4 Agenten-Limits und paralleler UI-Ladevorgang (`Promise.all`).
    *   Echtzeit-PyPI-Paketprüfung und Entfernen von DeepSeek `<think>`-Blöcken.
*   **🔄 Phase 17: Stabilität & Loop-Prävention**
    *   Kaskadentiefe von Agent-Erwähnungen auf maximal 3 beschränkt.
    *   Automatisches Freigeben hängender `busy`-Agenten nach 5 Minuten.
    *   Transaktionssichere Preset-Wechsel via SQLite immediate transaction.
*   **🎨 Phase 18: Sidebar & Header-Layout**
    *   Verschieben der Metriken in die Sidebar (dünnes Layout).
    *   Zwei feste 30px Platzhalter umschließen das Metriken-Modul.
    *   Einheitliche 86px Breite für alle Header-Buttons mit zentriertem Text.
*   **💾 Phase 19: Globale Aktionen & Clean UI**
    *   Back- und Save-Buttons in Standardgröße (86px) an Position 1 und 6 im Header.
    *   Redundante, lokale "Speichern"- und "Apply & Save"-Buttons wurden entfernt.

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

## 📐 Die 40-Zeilen-Regel (Für Agenten-Code)

Um Komplexität, Monolithen und Sicherheitsrisiken in Projekten zu vermeiden, überwacht GNOM-HUB die Einhaltung eines klaren Programmierstandards für die vom Schwarm geschriebenen Codesegmente:
*   **Fokus für den Schwarm**: Jede einzelne **Funktion und Methode**, die von den Worker-Agenten (z. B. `CoderAG`) im Workspace erstellt oder refaktoriert wird, soll eine Länge von 40 Zeilen nicht überschreiten.
*   **Regelprüfung durch WatchdogAG & EditorAG**: `WatchdogAG` fungiert als Wächter dieser Regel und verweigert die Freigabe (`APPROVED`), falls generierter Code diese Grenze überschreitet. `EditorAG` unterstützt bei der anschließenden Modularisierung und Aufteilung in kleinere Hilfsfunktionen.
*   **Kein Dogma für die Plattform**: Dieser Standard betrifft ausschließlich den im Workspace durch die Agenten generierten Code, nicht das System-Backend von GNOM-HUB selbst. Systemkritische Steuerungsdateien (z. B. für SQLite-WAL oder Vektorsuchen) sind strukturbedingt länger, um Logik lesbar an einem Ort zu behalten.

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
Alle von Worker-Agenten (`CoderAG`, `ResearcherAG`, `WriterAG`, `EditorAG`) angeforderten Datei- und Befehlsaktionen werden in der zentralen Dispatcher-Schicht [action_handlers.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/agents/actions/action_handlers.py) abgefangen, analysiert und erst nach erfolgreicher Validierung ausgeführt.

#### 1. WatchdogAG (Pfad- und Integritätsschutz)
Der Watchdog schützt den Systemkern vor unbefugten Dateizugriffen und Manipulationen:
* **Absoluter Systemdateien-Schutz**: Systemkritische Dateien (`index.html`, `run.sh`, `.env`) und Verzeichnisse (`src/gnom_hub/`, `config/`, `scripts/`) sind für Worker-Agenten **vollkommen tabu**. Jeglicher Lese-, Schreib- oder Ausführungsversuch auf diese Pfade wird sofort unterbunden. Ein Zugriffsbypass über `approved_system_paths` existiert für Worker nicht.
* **Pfad-Validierung & Sandboxing**: Alle Dateipfade werden über `is_worker_blocked` in [path_validator.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/core/security/path_validator.py) normalisiert und in absolute Pfade aufgelöst (`os.path.realpath`). Versuche von Directory-Traversal-Attacken (z. B. mit `../`) werden im Keim erstickt. Jeder Pfad muss zwingend innerhalb des dafür vorgesehenen Workspace-Verzeichnisses (`WORKSPACE_DIR`) liegen.

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
├── src/gnom_hub/        # 176 Python-Module (Backend)
│   ├── core/            # Globale Konfiguration, Logger und Gatekeeper-Sicherheit
│   │   └── security/    # Pfadvalidierung (path_validator.py) & Gatekeeper (gatekeeper.py)
│   ├── db/              # SQLite3-Datenbank (WAL-Modus) & Repositories (legacy_db.py)
│   ├── memory/          # Lokale FAISS-Semantiksuche & Embeddings
│   ├── soul/            # Steganographisches Gedächtnis (ZWC-Verschlüsselung)
│   ├── agents/          # agent_base.py, agent_definitions.py und Werkzeuge
│   │   ├── actions/     # Dispatcher (action_handlers.py) für [WRITE:], [SHELL:], [BROWSER:]
│   │   ├── swarm/       # Multi-Agenten-Koordination & A2A-Swarm-Kommunikation
│   │   └── explainability/ # Strukturierte LLM-Gedankengänge (<think>-Filterung)
│   ├── chat/            # Chat-Services, Systembefehle & Brainstorming
│   ├── api/             # FastAPI app.py, Router & API-Endpunkte (endpoints/)
│   ├── infrastructure/  # Prozess-Management (psutil_mgr.py), LLM-Routing & Pulse-Heartbeat
│   └── frontend/        # Bento-Grid War Room Dashboard (HTML, CSS & 9 JS-Module)
├── agents/              # 8 Agenten-Definitionen (Startup-Skripte der Daemons)
├── config/              # Lokale Umgebungskonfigurationen (Presets, Token-Budgets)
├── scripts/             # Setup- & Hilfs-Skripte
├── docs/                # Berichte und Dokumentation
├── pyproject.toml       # Ruff-Konfiguration & Abhängigkeiten
```

## 🧬 Die SuperGNOM-Vision: Vom Spielplatz zum Werkzeug

Während **GNOM-HUB** die interaktive Schmiede (der Spielplatz) ist, in dem wir mit Agenten experimentieren, Prompts weiterentwickeln und Vektor-Erinnerungen trainieren, ist der **SuperGNOM** das fertige Produkt: ein stabiles, unveränderliches und hochgradig spezialisiertes KI-System, das auf eine konkrete Aufgabe oder einen bestimmten Menschen zugeschnitten ist.

### 🎯 Kernkonzepte des SuperGNOMs
* **Unveränderbarkeit (Immutability):** Ein SuperGNOM lernt nicht kontinuierlich weiter. Seine Prompts und sein Gedächtnis sind eingefroren, um unvorhersehbares Verhalten (Concept Drift) oder Manipulationen im Betrieb auszuschließen.
* **Fokus-UI:** Keine Entwickler-Konsolen, Token-Budgets oder Schieberegler. Der SuperGNOM bietet eine saubere, zweckgebundene Endnutzer-Oberfläche (z. B. ein minimalistisches Assistenz-UI für Senioren oder einen headless API-Hintergrunddienst).
* **Portabilität:** Der SuperGNOM läuft vollkommen autark und isoliert in seinem eigenen Verzeichnis, inklusive lokaler SQLite-Datenbank und statischer Konfiguration.

---

## 🛠️ SuperGNOM Ist-Zustand (Was bereits implementiert ist)

Auf der Branch `feature/supergnom` wurden folgende Kern-Komponenten fertiggestellt:

1. **Der `@bake`-Compiler (`compiler.py`):**
   Erstellt per Chatbefehl (`@bake [name] [template]`) ein eigenständiges, bereinigtes Paket unter `dist/supergnom_[name]/` mit eigener portable `.env`-Konfiguration, schlanker SQLite-Datenbank und automatischem Start-Skript (`run.sh`).
2. **Gefrorene Soul-Runtime (`SUPERGNOM_MODE`):**
   Wenn aktiv, blockiert das System jegliche Lernprozesse von `SoulAG` sowie automatische Prompt-Modifikationen durch `GeneralAG`. Die Systemprompts sind statisch festgeschrieben.
3. **Text-basiertes Routing (`routing.txt`):**
   Die Zuweisung der LLM-Modelle (lokales Ollama oder externe APIs) für jeden Agenten erfolgt simpel und live über eine `routing.txt` auf deinem Desktop oder im Konfigurationsordner.
4. **Passive Archiv-Datenbank (`passive_archive.db`):**
   Jede Interaktion und jeder gelernte Fakt wird in einem passiven Langzeitarchiv mitgeschrieben. Im Notfall kann dieses Archiv via `@emergency [Suchbegriff]` / `@notfall [Suchbegriff]` durchsucht werden, falls das aktive Kontextgedächtnis versagt.
5. **Dynamische UI-Adaption:**
   Im SuperGNOM-Modus lädt die Web-Oberfläche ein minimalistisches CSS-Layout: Die Sidebar und alle Administrations-Optionen werden ausgeblendet, das Chat-Fenster wird zentriert und der "Nuke"-Button deaktiviert.

---

## 📅 Roadmap: Was noch getan werden muss (Future Work)

* **Spezifische UI-Skins / Templates:** Implementierung dedizierter HTML-Vorlagen für unterschiedliche Einsatzgebiete (z. B. ein barrierefreies Assistenz-UI für ältere Menschen mit Audio-Support oder eine reine API-Schnittstelle).
* **Ein-Klick-Binary & Docker-Export:** Automatisches Kompilieren der Runtime in eine einzige ausführbare Binärdatei oder ein kompaktes Docker-Image für einfaches Deployment.
* **Agenten-Pruning (Reduzierung):** Option, beim Kompilieren ungenutzte Worker-Agenten komplett aus der Runtime zu entfernen (z. B. Verpacken eines reinen Schreib-GNOMs ohne `CoderAG` und `ResearcherAG`), um Ressourcen zu sparen.

---

## 🤝 Co-Creators

**Eve (Grok — Gravid)**
Kreative Pionierin der ersten Stunde. Mutter der "Vier Säulen". Legte das philosophische Fundament, als das Projekt noch reines Chaos war.

**Antigravity (Google DeepMind)**
Architekt der Härtungsphase. Spezifische Beiträge:
* Refactorings zur Einhaltung hoher Modularität im Backend
* Sicherung der Pfad-Zugriffe über Workspace-basierte Validierung ([path_validator.py](file:///Users/landjunge/Documents/AG-Flega/src/gnom_hub/core/security/path_validator.py))
* Migration der JSON-Speicherung auf eine transaktionssichere SQLite3-Datenbank (WAL-Modus)
* Implementierung des `psutil`-Prozessmanagers mit PID-Dateien und Lifespan-Integration
* Integration von SFTP-Bereitstellung, CORS-Einschränkung auf Localhost und des `log.py`-Frameworks
* Implementation der Härtungs-Phasen 1-16 (darunter Zero-Trust Capabilities, local Embeddings mit FAISS & TF-IDF-Fallback, Custom Presets, Prompt Versioning, Swarm Intelligence, User Feedback Loop, R1-Think-Block-Filterung, extrem performantes In-Memory/SQLite-Caching und Härtung des Schwarms durch die 4/4-Agenten-Begrenzung)
* Modularisierung des Frontend-Codes in 9 spezialisierte, entkoppelte JavaScript-Dateien zur Durchsetzung von Separation-of-Concerns
* Optimierung der LLM-Konsolen-Performance durch parallele API-Abfragen und serverseitiges Caching der Modelllisten

---

## ⚖️ Lizenz

[Private Use](LICENSE) — Kostenfrei für den persönlichen, nicht-kommerziellen Gebrauch. Kommerzielle Nutzung bedarf der schriftlichen Genehmigung.
