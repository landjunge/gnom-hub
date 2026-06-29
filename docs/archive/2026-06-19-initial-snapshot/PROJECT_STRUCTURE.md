> ⚠️ HISTORISCH — Stand 19.06.2026, NICHT synchron mit Code.
> Aktuelle Source of Truth: docs/ARCHITECTURE.md

# 🧠 Gnom-Hub – Reale Projektstruktur & Architektur

Dieses Dokument beschreibt die tatsächliche Ordnerstruktur und die Kern-Komponenten von **Gnom-Hub**.

---

## Wurzelverzeichnis (Root)

Im Projekt-Root befinden sich die administrativen und betrieblichen Verzeichnisse:

```text
/
├── agents/             # Minimalistische Start-Skripte für die 8 Hintergrund-Agenten
├── config/             # Konfigurationsdateien (.env, Presets, Token-Budgets)
├── data/               # Lokale FAISS-Indizes, Vektor-Datenbank und Cache
├── docs/               # Technische Berichte und Entwickler-Dokumentationen
├── gnom_workspace/     # Das Arbeitsverzeichnis, in dem Worker-Agenten agieren
├── logs/               # Logdateien der Hintergrundprozesse und des Servers
├── scratch/            # Testskripte, Demos und temporäre Skripte
├── scripts/            # Installations- und Setup-Skripte
├── src/                # Quellcode-Paket
│   └── gnom_hub/       # Kernpaket von Gnom-Hub (siehe unten)
│
├── gnomhub.db          # Inaktive 0-Byte SQLite-Datei (Live-DB liegt unter ~/.gnom-hub/)
├── pyproject.toml      # Paket-Konfiguration und Python-Abhängigkeiten
└── run.sh              # Start-Skript für Server und Hintergrund-Agenten
```

---

## Das Kernpaket (`src/gnom_hub/`)

Die Anwendungslogik ist in **9 funktionale Module** gegliedert. Das Projekt folgt einer pragmatischen Struktur nach technischen Zuständigkeiten:

```text
src/gnom_hub/
├── agents/             # BaseAgent-Klasse, Rollen-Prompts, Tool-Registry und Actions-Parser
│   ├── actions/        # Handhabung von Worker-Aktionen ([WRITE:], [SHELL:], etc.)
│   ├── swarm/          # Swarm-Koordination und Agent-zu-Agent-Kommunikation
│   └── explainability/ # Strukturierung und Formatierung von LLM-Gedankengängen (<think>)
│
├── api/                # FastAPI Server-Konfiguration, Router und API-Endpunkte
│
├── chat/               # Chat-Services, Systembefehle und Brainstorm-Koordinierung
│
├── core/               # Globale Konfiguration, Logging-Definitionen und Exceptions
│   └── security/       # Gatekeeper (Double Approval), Whitelists und Pfad-Validierung
│
├── db/                 # Datenbankzugriff (SQLite), Schema-Definition und Repositories
│
├── frontend/           # Das visuelle Dashboard (War Room index.html, JS, CSS, Assets)
│
├── infrastructure/     # Daemon-Heartbeat (Pulse), Sandboxen und LLM-Key-Verwaltung
│   ├── process/        # Prozess- und Sandboxing-Management (Playwright)
│   ├── router/         # Modell-Routing und Multi-Provider-Ketten (Ollama/OpenRouter)
│   └── tokens/         # Token-Budget-Management und Latenz-Analysen
│
├── memory/             # Lokale FAISS-Indizierung, Embeddings und semantische Suche
│
└── soul/               # Steganographisches ZWC-Gedächtnis (Zero-Width Characters)
```
