# 🧠 GNOM-HUB — Multi-Agenten-Plattform

Gnom-Hub ist eine modulare, asynchrone Multi-Agenten-Plattform, die auf robusten Clean-Architecture-Prinzipien basiert. Die Plattform zeichnet sich durch eine strikte Designregel aus: **Jedes interne Python-Backend-Modul ist auf maximal 40 Zeilen Code begrenzt** (die 40-Zeilen-Regel). Gnom-Hub orchestriert einen kooperativen Schwarm von Agenten und bietet ein visuell ansprechendes Web-Dashboard namens **War Room**.

---

## 🚀 Key Features

* **Zentralisiertes Agenten-Register**: Vollständige Definition des Schwarms in der zentralen Datei `src/gnom_hub/agent_definitions.py`.
* **Workflow-Preset-System**: 6 spezialisierte Preset-Modi direkt unter der Showbox im Dashboard steuerbar.
* **Automatische Prompt- & Modell-Injektion**: SoulAG und der Preset-Service passen das Verhalten und die System-Prompts der Worker-Agenten dynamisch an das gewählte Preset an.
* **Dynamisches Umschalten von LLM-Einstellungen**: Speichert individuelle Modellzuweisungen pro Preset und stellt diese beim Wechsel automatisch wieder her.
* **Rollenbasierte Werkzeug-Rechte**: System-Agenten erhalten Vollzugriff, während Worker restriktiv und sicher im Workspace arbeiten (CoderAG erhält erweiterte Rechte via `godmode`).
* **Relationaler SQLite-Speicher (WAL-Modus)**: Transaktionssichere und lock-freie Datenhaltung für parallele Agenten-Schreibzugriffe.

---

## 🤖 Die 8 Agenten
Der Schwarm ist in 4 koordinierende System-Agenten und 4 spezialisierte Worker-Agenten unterteilt (zentral definiert in `agent_definitions.py`):

### System-Agenten (Vollzugriff)
System-Agenten verwalten die Plattformsteuerung und besitzen umfassende Berechtigungen (`read`, `write`, `run`, `godmode`, `crawl`, `desktop`, `evolve`):
* **SoulAG**: Das zentrale Gedächtnis des Schwarms. Analysiert Chat-Inhalte im Hintergrund und injiziert persönliche Nutzer-Präferenzen kontextbezogen in Agenten-Prompts.
* **GeneralAG**: Der Hauptkoordinator. Analysiert komplexe Anfragen, delegiert Teilschritte an die Worker und synthetisiert die Ergebnisse.
* **WatchdogAG**: Überwacht die Integrität des Workspace und die Einhaltung der Systemgrenzen.
* **SecurityAG**: Führt Risikoprüfungen durch und signiert Workspace-Dateien kryptografisch.

### Worker-Agenten (Eingeschränkter Zugriff)
Worker-Agenten erledigen die eigentliche Arbeit im Workspace. Sie besitzen standardmäßig Lese- und Schreibberechtigungen im Workspace (`read`, `write`, `@job`):
* **CoderAG**: Entwickelt und debuggt Code (erhält durch `godmode` zusätzlich Terminal- und Browserrechte).
* **ResearcherAG**: Führt Recherchen durch, fragt Such-APIs ab und prüft Quellen.
* **WriterAG**: Erstellt Dokumentationen, Tutorials, Entwürfe und Texte.
* **EditorAG**: Korrigiert und poliert Texte und sichert die Qualität.

---

## 📖 Bedienungsanleitung für Presets

Das Preset-System erlaubt es Ihnen, den Fokus der Plattform mit einem einzigen Klick im Dashboard neu auszurichten.

### Die 6 Workflow-Modi
1. 💻 **Web Development**: Richtet Worker auf sauberen HTML, CSS, JavaScript-Code, Responsive Design und moderne Web-APIs aus.
2. 🎨 **Graphic Design**: Richtet Worker auf visuelle Ästhetik, Farbharmonien, Typografie und SVG-Generierung aus.
3. 🎵 **Audio Production**: Richtet Worker auf Sound-Synthese, Web Audio API, Audio-Processing und Soundeffekte aus.
4. 🎬 **Video Production**: Richtet Worker auf Video-Streaming, Canvas-Animationen, CSS-Transitions und visuelle Effekte aus.
5. ✍️ **Marketing & Copy**: Richtet Worker auf Conversion-Hooks, Werbetexte, SEO-Optimierung und Kampagnen aus.
6. 🔍 **Research & Analysis**: Richtet Worker auf tiefgehende Recherche, Datenanalyse, Faktenprüfung und strukturierte Berichte aus.

### Automatische Modell- und Prompt-Steuerung
* **Preset-Wechsel**: Wählen Sie ein Preset über das Dropdown-Menü unter der Showbox aus.
* **SoulAG-Prompt-Injektion**: SoulAG und der Preset-Service fangen den Wechsel ab und injizieren automatisch die passenden Prompts und Fokus-Modifikatoren für die 4 Worker-Agenten (`CoderAG`, `ResearcherAG`, `WriterAG`, `EditorAG`).
* **Dynamische LLM-Einstellungen**: 
  - Standardmäßig werden den Agenten optimale Routing-Stufen zugeteilt.
  - Wenn Sie im Einstellungsmenü (**LLM-Settings**) den Agenten andere Modelle zuweisen und speichern, merkt sich Gnom-Hub diese Konfiguration **spezifisch für das aktive Preset**.
  - Sobald Sie zu diesem Preset zurückwechseln, werden Ihre bevorzugten Modelle und Anbieter vollautomatisch geladen.

---

## 🚀 Schnellstart

Tragen Sie vor dem ersten Start Ihre API-Schlüssel in `config/.env` ein (z. B. DeepSeek oder OpenRouter).

### 1. Server und Agenten starten
Führen Sie das Startskript im Hauptverzeichnis aus:
```bash
chmod +x run.sh
./run.sh
```
Das Skript startet den FastAPI-Hub sowie alle 8 Hintergrund-Agenten parallel.

### 2. Dashboard öffnen
Öffnen Sie Ihren Browser unter: **[http://127.0.0.1:3002](http://127.0.0.1:3002)**

---

## 🛠️ Technologie-Stack
* **Backend**: FastAPI, Uvicorn, asynchrones Python 3.9+.
* **Datenhaltung**: SQLite3 (WAL-Modus für sicheren Concurrent-Schreibzugriff).
* **Prozess-Manager**: `psutil` zur zuverlässigen Überwachung und Steuerung über PID-Dateien.
* **Frontend**: Responsive HTML5, Vanilla CSS3 (HSL-Design, Glassmorphismus, CSS-Transitions) und pure JavaScript.
* **LLM-Integration**: Lokale Ollama-Instanzen sowie Cloud-Provider (DeepSeek, OpenRouter).