> ⚠️ HISTORISCH — Stand 19.06.2026, NICHT synchron mit Code.
> Aktuelle Source of Truth: docs/ARCHITECTURE.md

# 🧠 Ehrliche Technische Dokumentation: Gnom-Hub

Dieses Dokument beschreibt die **reale** Architektur, Dateistruktur, Datenbankschemata und Systemmechanismen des Gnom-Hub-Projekts. Es verzichtet bewusst auf Wunsch-Architekturen oder geschönte Darstellungen und dokumentiert den tatsächlichen Zustand der Codebasis (Stand: Mai 2026), inklusive bekannter Bugs.

---

## 1. Reale Verzeichnisstruktur

Das Projekt ist in eine administrative Wurzelstruktur (Root) und das eigentliche Kernpaket (`src/gnom_hub/`) aufgeteilt. 

### 1.1 Wurzelverzeichnis (Root)
Im Projekt-Root (`/Users/landjunge/Documents/AG-Flega`) befinden sich:
*   **`agents/`**: Enthält die 8 ausführbaren Start-Skripte für die Hintergrund-Agenten (`coderAG.py`, `editorAG.py`, `generalAG.py`, etc.). Diese Dateien sind minimalistische Wrapper (~10-20 Zeilen), die die `BaseAgent`-Klasse konfigurieren und ausführen.
*   **`config/`**: Enthält die Konfigurationsdaten (wie `.env` und `.gnom-hub-tokens.json`) sowie den Ordner `presets/`.
*   **`data/`**: Enthält die Vektordatenbank (`soul_embeddings.index`), ID-Mappings (`soul_fact_ids.pkl`) und einen Cache für Embeddings (`emb_cache.pkl`). *Hinweis: Die hier liegende `gnomhub.db` ist eine ungenutzte 0-Byte-Datei.*
*   **`docs/`**: Enthält Entwickler-Reports und Markdown-Konzepte.
*   **`frontend/`**: **Vollständig leerer Ordner.** Die tatsächlichen Frontend-Dateien liegen tief im Quellcode-Paket.
*   **`gnom_workspace/`**: Der eigentliche Arbeitsordner, in dem Worker-Agenten Lese- und Schreibrechte besitzen.
*   **`logs/`**: Speicherort für Anwendungs- und Prozess-Logs.
*   **`scratch/`**: Test- und Hilfsskripte.
*   **`scripts/`**: Systemskripte zur Installation und Einrichtung.
*   **`src/`**: Enthält das Hauptpaket `gnom_hub` und den ungenutzten, leeren Ordner `workspace/`.

### 1.2 Das Kernpaket (`src/gnom_hub/`)
Entgegen älteren Dokumenten (wie [PROJECT_STRUCTURE.md](file:///Users/landjunge/Documents/AG-Flega/PROJECT_STRUCTURE.md)), die eine idealized Clean Architecture mit Schichten wie `domain/` oder `application/` beschreiben, existieren diese Schichten im Code **nicht**. Stattdessen ist `src/gnom_hub/` in exakt 9 pragmatische Unterordner unterteilt:

```
src/gnom_hub/
├── core/             # Konfiguration, Logger und systemweite Utilities (z.B. Audio, Presets)
│   └── security/     # Sicherheitsprüfungen, Whitelists und Pfad-Validierung
├── db/               # SQLite-Repository-Klassen (z.B. agent_repo.py, chat_repo.py)
├── memory/           # Lokale FAISS-Semantiksuche, Embeddings und Cache
├── soul/             # Kernlogik für steganographisches Gedächtnis (zwc_soul.py) und SoulAG-Instanz
├── agents/           # BaseAgent-Klasse, Rollen-Prompts und Tool-Definitionen
│   ├── actions/      # Parser für Aktions-Tags wie [WRITE:], [SHELL:] und [CRAWL:]
│   ├── swarm/        # Koordinations- und Kommunikationslogik für Multi-Agenten-Tasks
│   └── explainability/ # Formatierung und Speicherung von Gedankengängen (<think>-Tags)
├── chat/             # Chat-Services, Brainstorm-Helper und Command-Handler
├── api/              # FastAPI Server-Konfiguration, Endpunkte und Abhängigkeiten
├── infrastructure/   # Prozess-Steuerung, Sandbox-Umgebung (Playwright) und Token-Budgeting
└── frontend/         # Die tatsächliche Single-Page-Anwendung (index.html, showbox.js, showbox.css)
```

---

## 2. Das Datenbanksystem (SQLite)

In älteren Architekturdokumenten wird behauptet, Gnom-Hub nutze eine dateibasierte JSON-Datenbank mit `fcntl`-Dateisperren. **Das entspricht nicht der Realität.** 

Gnom-Hub nutzt eine relationale **SQLite-Datenbank** im WAL-Modus (`PRAGMA journal_mode=WAL`), um concurrent Schreib- und Lesezugriffe abzusichern.

### 2.1 Speicherort der Datenbank
Die aktive Live-Datenbank befindet sich im Home-Verzeichnis des Nutzers unter:
`~/.gnom-hub/data/gnomhub.db`
Alle Datenbankänderungen und Chat-Verläufe werden dort persistiert. Andere `gnomhub.db`-Dateien im Repository (z.B. im Root oder unter `src/data/`) sind inaktiv und dienen als Überbleibsel oder lokale Testdatenbanken.

### 2.2 Doppelte Schema-Initialisierung
Beim Start der FastAPI-Anwendung in `src/gnom_hub/api/app.py` wird die Datenbank über zwei separate Mechanismen initialisiert:
1.  **`create_tables()`** (importiert aus `gnom_hub.db.schema`): Erstellt 6 Basistabellen.
2.  **`init_db()`** (importiert aus `gnom_hub.db` / `legacy_db`): Erstellt 8 Tabellen (teilweise überlappend) und führt das Seeding der Standard-Agenten und der Demohistorie durch.

Dadurch entsteht eine Mischung aus insgesamt **11 aktiven Tabellen** in der SQLite-Datenbank:
*   `state`: Globale Konfigurationsschlüssel (z. B. `active_project`, `language`, `active_showbox`, `pending_decisions`).
*   `agents`: Registrierte System- und Worker-Agenten inklusive Port, Status, Fähigkeiten und Rollen.
*   `chat`: Der eigentliche Chatverlauf im War Room.
*   `chat_messages`: Eine redundante Tabelle für LLM-Nachrichtenverläufe (aus `schema.py`).
*   `flexsoul`: Eine redundante Tabelle zur Speicherung von Kurz- und Langzeitgedächtnissen pro Agent (aus `schema.py`).
*   `soul_memory`: Flache Schlüssel-Wert-Tabelle für semantische Fakten, verwaltet von `SoulAG`.
*   `audit_log`: Systemereignisse, Token-Verbräuche und API-Latenzen für Monitoring.
*   `prompt_versions`: Gespeicherte Prompt-Evolutionen und Performance-Scores zur Evaluierung.
*   `capabilities`: TTL-basierter Cache für temporäre Freigaben von Pfaden/Befehlen (Capability Leases).
*   `showbox_presentations`: Gespeicherte HTML-Slides für die Showbox.
*   `explainable_outputs`: Strukturierte Gedankengänge der Agenten (erstellt in `eo_store.py`).

---

## 3. Showbox-Architektur: Die Wahrheit über die 3 Layer

Das vorherige Dokument beschrieb die Showbox als eine in drei klar getrennte Layer unterteilte Komponente im Backend und in der Datenbank. **Das ist geschönt.** 

Im Backend und der Datenbank gibt es keinerlei logische Schichten für die Showbox. Die Datenbank speichert Präsentationen flach in der Tabelle `showbox_presentations`. Die Dreiteilung existiert **ausschließlich im Client-seitigen JavaScript** (`src/gnom_hub/frontend/showbox.js`):

### 3.1 Dynamisches Client-seitiges Routing
Wenn der Client (`index.html`) per API neue Showbox-Präsentationen empfängt, entscheidet die JavaScript-Funktion `resolveTargetLayer` anhand des Senders und des Inhalts der Folien, in welche visuelle Spalte (Layer) die Slide sortiert wird:

```javascript
function resolveTargetLayer(sender, name, slides) {
  const s = (sender || '').toLowerCase().trim();
  const n = (name || '').toLowerCase().trim();
  const slideStr = JSON.stringify(slides).toLowerCase();

  // Layer 3 (User / Entscheidung): Kritische Blockaden, manuelle Genehmigungen (grüne/rote Buttons)
  if (s === 'user' || s === 'you' || n.startsWith('blockade:') || slideStr.includes('@@approve_decision') || slideStr.includes('@@reject_decision')) {
    return 3; 
  }

  // Layer 1 (System-Agenten): Logs und Statusmeldungen von GeneralAG, SoulAG, SecurityAG, WatchdogAG
  if (['generalag', 'soulag', 'securityag', 'watchdogag', 'system', ''].includes(s)) {
    return 1;
  }

  // Layer 2 (Worker): Inhalte, Code-Snippets, Berichte von CoderAG, WriterAG, ResearcherAG, EditorAG
  return 2;
}
```

### 3.2 Rendern und Layout-Anpassung
*   Die Folien-Inhalte werden als rohe HTML-Strings per `innerHTML` in den Layer-Body geschrieben.
*   **Auto-Fit-Heuristik**: Um Scrollbalken zu vermeiden und Inhalte in das starre Dashboard-Gitter einzupassen, reduziert die JavaScript-Funktion `autoFitText(layerIdx)` iterativ die Schriftgröße des HTML-Bodys von 40px herunter bis minimal 11px, bis der Inhalt komplett in den Container passt.

---

## 4. Agenten-Architektur & Polling-Schleife

Alle Hintergrund-Agenten laufen in einer Polling-Schleife, die auf der Klasse `BaseAgent` (`src/gnom_hub/agents/agent_base.py`) basiert.

1.  **Registrierung**: Der Agent sendet ein POST an `/api/agents/register`.
2.  **Polling**: Alle 5 bis 15 Sekunden (je nach Konfiguration) ruft der Agent `/api/chat?limit=10` ab.
3.  **Filterung**: Der Agent vergleicht die IDs mit seinem lokalen Set `self.seen`. Findet er eine neue Nachricht von `user` oder `GeneralAG`, die seinen Trigger (z. B. `@code`, `@write`) oder `@all` enthält, wechselt sein DB-Status auf `busy`.
4.  **Verarbeitung**:
    *   `SoulAG` sucht semantische Erinnerungen über die FAISS-Vektordatenbank und hängt diese an den System-Prompt an (`inject_context`).
    *   Das LLM-Modell wird über den internen `ask_router` aufgerufen.
    *   Der Antworttext wird nach Aktions-Tags durchsucht und die Aktionen (`process_actions`) ausgeführt.
    *   DeepSeek-Denkprozesse (`<think>`-Blöcke) werden extrahiert und der Antwort vorangestellt.
    *   Das Ergebnis wird per POST an `/api/chat` übermittelt.
    *   Der Status wechselt zurück auf `online`.

---

## 5. Sicherheitsmechanismen: Das Gatekeeper-System

Das Double-Approval-System in `gatekeeper.py` schützt das System vor unautorisierten Aktionen der Worker-Agenten.

### 5.1 Prüfablauf bei Datei-Schreibzugriffen (`[WRITE:]`)
Bevor ein Worker eine Datei schreiben darf, prüft `verify_write`:
1.  **Rollen-Sperre**: Ist der Sender `GeneralAG` oder hat er die Rolle `general`, wird der Schreibzugriff prinzipiell abgelehnt (Koordinatoren dürfen keinen Code schreiben).
2.  **Capability Lease**: Ist die Pfad-Schreibberechtigung für diesen Agenten bereits im Cache (`check_capability`), wird die Aktion sofort erlaubt.
3.  **Pfad-Validierung**: Verweist der Pfad aus dem Arbeitsverzeichnis heraus? Liegt er in geschützten Systempfaden (`src/gnom_hub`, `config/`, etc.)? Falls ja, wird eine Sicherheitsblockade ausgelöst.
4.  **Schadcode-Scan**: Enthält der zu schreibende Inhalt gefährliche Python/JS-Muster? Falls ja, Blockade.
5.  **Auto-Approval**: Ist der Pfad sicher und liegt innerhalb des Workspaces, wird die Freigabe erteilt und im Capability Cache hinterlegt.

### 5.2 Prüfablauf bei Shell-Befehlen (`[SHELL:]`)
Bevor ein Worker einen Befehl ausführen darf, prüft `verify_cmd`:
1.  **Whitelist-Prüfung**: Befehle werden in ihre Bestandteile zerlegt. Nur folgende Programme sind erlaubt: `python3`, `python`, `pytest`, `git`, `pip`, `pip3`, `npm`, `npx`, `node`, `ls`, `echo`, `cat`, `tail`.
2.  **Spezifische Argument-Validierung**:
    *   `pip install`: Blockiert Pakete mit bekannten Sicherheitslücken, indem live die PyPI JSON API abgefragt wird.
    *   `npm install`: Erlaubt ausschließlich eine kleine, statisch definierte Liste sicherer Pakete (`vite`, `react`, `vue`, `next`).
    *   `git`: Erlaubt nur unkritische Subkommandos (`status`, `log`, `diff`, `commit`, `add`, `checkout`, `reset`, `init`, `config`).

### 5.3 Der Blockade-Workflow
Verletzt ein Befehl oder Schreibzugriff eine Regel, startet `wait_for_decision`:
1.  Der anfordernde Agent wird in der Datenbank in den Status `paused` gesetzt.
2.  `WatchdogAG` (bei Pfadfehlern) oder `SecurityAG` (bei Schadcode) formulieren per LLM eine kurze Blockade-Begründung.
3.  `SoulAG` steuert historische Benutzerkontexte bei, und `GeneralAG` generiert eine Empfehlung.
4.  In **Layer 3 (User/Entscheidung)** der Showbox wird eine interaktive Slide mit Genehmigungs-Buttons geladen.
5.  **Der Agent wartet blockierend**: Der Ausführungsthread des Agenten blockiert in einer `while True`-Schleife mit `time.sleep(0.5)`, bis die API durch einen Benutzerklick den Zustand des Entscheidungs-Schlüssels in der DB auf `approved` oder `rejected` ändert.

---

## 6. Kritische Code-Bugs (Wichtige Entwickler-Hinweise)

Bei der Code-Analyse wurden zwei kritische Fehler in der Polling-Schleife der Hintergrundprozesse identifiziert, die die Ausführung von Werkzeugen (Aktions-Tags) komplett blockieren:

### 6.1 Fehlerhafte Importpfade in `agent_base.py`
In `src/gnom_hub/agents/agent_base.py` werden zwei Funktionen erst lazy innerhalb der `run`-Schleife importiert, sobald ein Agent getriggert wird (Zeilen 34-35):

```python
from gnom_hub.action_handlers import process_actions
from gnom_hub.brainstorm_helpers import get_workspace_dir
```

Diese Importe sind **fehlerhaft**, da die Module an diesen Pfaden nicht existieren. Sie führen bei der ersten Ausführung eines Aktions-Tags durch einen Hintergrund-Agenten zu einem sofortigen Programmabsturz (`ModuleNotFoundError`):
*   `process_actions` muss aus `gnom_hub.agents.actions.action_handlers` importiert werden.
*   `get_workspace_dir` muss aus `gnom_hub.chat.brainstorm.brainstorm_helpers` importiert werden.
