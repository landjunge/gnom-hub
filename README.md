# 🧠 GNOM-HUB — Pragmatische Multi-Agenten-Orchestrierung

Gnom-Hub ist kein Enterprise-Framework für hunderte Agenten und komplexe Workflows. Es ist ein minimalistisches, lokal-fokussiertes Orchestrierungssystem für genau **8 feste Agenten (4 System-Koordinatoren und 4 Worker-Spezialisten)** – nicht mehr, nicht weniger. Die Steuerung und Visualisierung erfolgt über das Web-Dashboard **War Room**.

---

## 🎯 Philosophie & Einsatzzweck

Die Plattform wurde nach folgenden technischen Leitlinien entworfen:
1. **Local-First & Datensparsamkeit**: Alle Agenteninteraktionen, Chatverläufe und Zustände werden in einer lokalen SQLite3-Datenbank abgelegt. Keine Abhängigkeiten von externen Cloud-Orchestrierungsdiensten.
2. **Defensive Architektur**: Jedes Python-Backend-Modul in `src/gnom_hub/` ist auf **maximal 40 Zeilen Code** begrenzt (Ausnahmen bestehen nur für `db.py` und `hub_app.py`). Diese Restriktion erzwingt kompromisslose Modularisierung und verhindert unübersichtlichen Spaghetticode.
3. **Pragmatismus**: Gnom-Hub verzichtet auf unkontrollierte autonome Schleifen. Aktionen sind nutzergesteuert und transparent. Die Plattform eignet sich hervorragend für Lehre, Forschung, Experimente mit Prompt-Injektionen und das Testen lokaler LLMs.

---

## 🤖 Der Agenten-Schwarm (8 Agenten)

Alle Agenteneigenschaften sind in der zentralen Konfigurationsdatei `src/gnom_hub/agent_definitions.py` hinterlegt.

### System-Agenten (Administrative Rechte)
System-Agenten besitzen erweiterte Zugriffsrechte (`read`, `write`, `run`, `godmode`, `crawl`, `desktop`, `evolve`):
* **SoulAG**: Das passive Gedächtnis. Analysiert die Nachrichten des Nutzers im Hintergrund asynchron, extrahiert Fakten oder Regeln und injiziert diese bei Folgeanfragen als Kontext in die System-Prompts.
* **GeneralAG**: Der Koordinator. Analysiert komplexe `@job`-Anfragen, teilt Aufgaben an Worker-Spezialisten zu und führt Ergebnisse zusammen.
* **WatchdogAG**: Überwacht die Integrität des Workspace und die Einhaltung der Dateigrenzen.
* **SecurityAG**: Führt Sicherheitsüberprüfungen durch und signiert Workspace-Dateien kryptografisch.

### Worker-Agenten (Eingeschränkte Rechte)
Worker-Agenten besitzen standardmäßig nur Lese- und Schreibrechte innerhalb ihres Workspace-Verzeichnisses (`read`, `write`, `@job`):
* **CoderAG**: Entwickelt und debuggt Code. Erhält über `godmode` zusätzliche Rechte für die Playwright-Browsersteuerung und terminalbasierte Befehlsausführung.
* **ResearcherAG**: Sucht Dokumentationen, liest Web-Inhalte via Crawling-APIs und validiert Quellen.
* **WriterAG**: Erstellt Entwürfe, Dokumentationen und Texte.
* **EditorAG**: Führt Lektorate, Korrekturlesen und Qualitätskontrollen durch.

---

## 🎛️ Das Preset-System (6 Modi)

Das Preset-System dient dazu, den Fokus und die Modelle der Worker-Agenten mit einem Klick an eine bestimmte Aufgabe anzupassen. Die Auswahl erfolgt über das Dropdown-Menü direkt unter der Showbox.

### Die 6 vordefinierten Modi:
1. 💻 **Web Development**: Fokus auf semantisches HTML5, native Web-APIs, Barrierefreiheit (ARIA) und CSS.
2. 🎨 **Graphic Design**: Fokus auf SVGs, Layout-Grids, Farbpaletten (HSL) und Kontraste.
3. 🎵 **Audio Production**: Fokus auf Web Audio API, DSP-Algorithmen und Sound-Synthese.
4. 🎬 **Video Production**: Fokus auf Canvas-Animationen, Render-Pipelines und Storyboards.
5. ✍️ **Marketing & Copy**: Fokus auf SEO-Keywords, AIDA-Textstrukturen und Call-to-Actions.
6. 🔍 **Research & Analysis**: Fokus auf Faktenprüfung, akademische Quellen und Python-Datenanalyse.

### Technische Funktionsweise:
* Bei einem Preset-Wechsel wird das Preset im State-Repository gespeichert.
* Der Router liest bei jeder Anfrage an einen Worker-Agenten die entsprechenden Prompt-Modifikatoren aus der `presets.json` aus und stellt diese dem System-Prompt voran.
* Zudem werden die LLM-Modelle der Worker dynamisch angepasst (z. B. spezialisierte Coder-Modelle bei Web Dev). Custom-LLM-Einstellungen, die der Nutzer im Einstellungsmenü speichert, werden an das jeweilige Preset gekoppelt und bei Auswahl automatisch wiederhergestellt.

---

## 🧠 SoulAG: Gedächtnis & Kontext-Injektor

SoulAG arbeitet im Hintergrund und greift nicht aktiv in die Konversation ein:
1. **Asynchrone Extraktion**: Jede Nachricht des Nutzers wird im Hintergrund analysiert. SoulAG extrahiert wichtige Fakten, Programmierpräferenzen oder Verhaltensregeln.
2. **Relationale Speicherung**: Die extrahierten Daten werden in der Tabelle `soul_memory` abgelegt.
3. **Kontext-Injektion**: Vor jedem Aufruf eines Workers fragt SoulAG relevante Fakten aus der Datenbank ab und hängt diese an das System-Prompt des aktiven Agenten an. So bleibt das System personalisiert, ohne den Chatverlauf unnötig zu belasten.

---

## 🏗️ Technische Entscheidungen & Architektur

* **Clean Architecture**: Strikte Aufteilung in Domain (Zustands- und Validierungsregeln), Application (Anwendungsfälle wie Senden/Brainstorming), Infrastructure (Datenbanken, Router, OS-Prozesse) und Presentation (FastAPI-Schnittstellen und Dashboard).
* **40-Zeilen-Regel**: Begrenzt Dateilängen im Backend drastisch. Dies zwingt Entwickler zu kompromissloser Modularisierung und verhindert monolithischen Code. Ausnahmen bestehen nur für die Datenbank-Konfiguration (`db.py`) und die Anwendungs-Initialisierung (`hub_app.py`).
* **Sichere Tool-Berechtigungen**: Werkzeug-Zugriffe (z. B. Dateisystem-Schreibzugriffe oder Shell-Befehle) werden in `action_handlers.py` in Echtzeit gegen die in `agent_definitions.py` definierten Rollen-Berechtigungen abgeglichen.

---

## 🚦 Entwicklungsstand (Ehrlich & Konkret)

### Was funktioniert:
* [x] Stabiles Prozessmanagement (Start/Stopp der 8 Hintergrundprozesse via `psutil` und PID-Dateien).
* [x] Datenpersistenz und Transaktionssicherheit über SQLite (WAL-Modus).
* [x] Vollständiger Preset-Wechsel inklusive dynamischer Prompt- und Modell-Anpassung.
* [x] Kontext-Injektion und automatisches Faktenlernen über SoulAG im Hintergrund.
* [x] Sandboxed Shell-Ausführung für CoderAG (mit Validierung gegen gefährliche Befehle).
* [x] UI-Skalierung (1/3 kleinere Schrift für bessere Übersicht bei langen Chats).

### Was noch in Arbeit / geplant ist:
* [ ] **Erweiterte MCP-Client-Unterstützung**: Derzeit sind nur Basisfunktionen integriert; die dynamische Registrierung externer MCP-Server ist in der Entwicklung.
* [ ] **Erweiterter Godmode**: Derzeit sind Dateizugriffe außerhalb des Workspace-Pfads auch bei `godmode`-Rechten stark reglementiert.
* [ ] **Playwright Browser-Automation**: Der Browser-Tag `[BROWSER:]` ist im Code vorbereitet, aber in der aktuellen Standardkonfiguration deaktiviert.

---

## 🚀 Schnellstart

Tragen Sie vor dem ersten Start Ihre API-Schlüssel in `config/.env` ein (z. B. DeepSeek oder OpenRouter).

1. **Server und Agenten starten**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
2. **Dashboard öffnen**:
   Navigieren Sie im Webbrowser zu: **[http://127.0.0.1:3002](http://127.0.0.1:3002)**

---
**Entwicklungsstand:** Mai 2026 — Experimenteller Prototyp.