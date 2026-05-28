# Contributing to Gnom-Hub

## 🏗️ Projekt-Struktur

```text
gnom-hub/
├── agents/             # Minimalistische Start-Skripte für die 8 Hintergrund-Agenten
├── config/             # Konfigurationsdateien (.env, Presets, Token-Budgets)
├── data/               # Lokale FAISS-Indizes, Vektor-Datenbank und Cache
├── docs/               # Technische Berichte und Entwickler-Dokumentationen
├── gnom_workspace/     # Das Arbeitsverzeichnis, in dem Worker-Agenten agieren
├── logs/               # Logdateien der Hintergrundprozesse und des Servers
├── scratch/            # Testskripte, Demos und temporäre Skripte
├── scripts/            # Installations- und Setup-Skripte
├── src/                # Quellcode-Paket
│   └── gnom_hub/       # Kernpaket von Gnom-Hub mit 9 funktionalen Modulen:
│       ├── agents/     # BaseAgent, Actions-Handler, Swarm-Koordination
│       ├── api/        # FastAPI Server, Router und Endpunkte
│       ├── chat/       # Chat-Services und Brainstorming
│       ├── core/       # Globale Konfiguration, Logging, Security Gatekeeper
│       ├── db/         # SQLite-Datenbankschnittstelle und Schema
│       ├── frontend/   # Visuelles Bento-Grid Dashboard (War Room index.html, JS, CSS)
│       ├── infrastructure/ # Heartbeat (Pulse), Playwright Sandbox, LLM Routing
│       ├── memory/     # Lokale FAISS-Indizierung und semantische Suche
│       └── soul/       # Steganographisches ZWC-Gedächtnis (Zero-Width Characters)
├── gnomhub.db          # Inaktive 0-Byte SQLite-Datei (Live-DB liegt unter ~/.gnom-hub/)
├── pyproject.toml      # Paket-Konfiguration und Python-Abhängigkeiten
└── run.sh              # Start-Skript für Server und Hintergrund-Agenten
```

## 🚀 Setup für Entwickler

```bash
# 1. Repository klonen
git clone <repo-url>
cd AG-Flega

# 2. Python venv erstellen
python3 -m venv .venv
source .venv/bin/activate

# 3. Dependencies installieren
pip install -e ".[dev]"

# 4. Credentials konfigurieren
cp config/.env.example config/.env
# → API-Keys und FTP-Credentials eintragen

# 5. Starten
python -m gnom_hub
```

## 📏 Code-Konventionen

### Code-Struktur & Lesbarkeit
- Versuche Dateien klein und fokussiert zu halten, wo es sinnvoll ist.
- Wenn das Aufteilen einer Datei jedoch die Übersicht oder Lesbarkeit verschlechtert, belasse die Logik in einer Datei. Eine Datei darf dann auch deutlich länger als 40 Zeilen sein.
- Die oberste Priorität ist guter, wartbarer und verständlicher Code — nicht das Einhalten einer willkürlichen Zeilenzahl.

### Namenskonventionen
- Agent-Namen: **immer lowercase** in Code (`coderag`, `generalag`)
- Agent-Display-Names: CamelCase (`CoderAG`, `GeneralAG`)
- Funktionsnamen: beschreibend, nicht kryptisch (`extract_content` statt `_ext`)

### Pfade
- **Niemals** absolute Pfade hardcoden
- Verwende `config.py` Konstanten: `PROJECT_ROOT`, `WORKSPACE_DIR`, `FRONTEND_DIR`, `CONFIG_DIR`

### Logging
- Verwende `from .log import get_logger; logger = get_logger("modul_name")`
- **Kein** `print()` in Produktionscode

### Error Handling
- **Kein** bare `except:` — immer `except Exception:` oder spezifischer
- Fehler loggen, nicht verschlucken

### Sicherheit
- **Keine** Credentials im Code — immer über `.env` / Umgebungsvariablen
- **Kein** `godmode` — Workspace-basierte Pfadvalidierung verwenden
- HTML-Output immer escapen (XSS-Schutz)

## 🔧 Linting

```bash
# Ruff installieren
pip install ruff

# Linting ausführen
ruff check src/ agents/

# Auto-Fix
ruff check --fix src/ agents/
```

## 🧪 Tests

Tests werden mit `pytest` geschrieben:

```bash
pip install pytest
pytest tests/
```

## 📝 Git-Workflow

1. Feature-Branch erstellen: `git checkout -b feature/mein-feature`
2. Änderungen committen mit beschreibender Message
3. Pull Request erstellen
4. **Vor dem Merge:** Sicherstellen, dass keine Secrets im Code sind!

## ⚠️ Wichtige Hinweise

- `config/.env` wird **nicht** committed (siehe `.gitignore`)
- Agent-Prozesse laufen als **separate Subprocesses** — JSON-DB hat File-Locking
- Das Frontend ist aktuell ein Monolith (`index.html`, ~4000 Zeilen)
- Plattform: Primär macOS, Linux-Kompatibilität in Arbeit
