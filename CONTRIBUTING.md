# Contributing to Gnom-Hub

## 🏗️ Projekt-Struktur

```
AG-Flega/
├── src/gnom_hub/     # Python-Backend (FastAPI)
│   ├── config.py     # Zentrale Pfad-Konfiguration
│   ├── db.py         # JSON-Datenbank mit File-Locking
│   ├── hub_app.py    # FastAPI App & Router-Mounting
│   ├── router.py     # LLM-Routing (DeepSeek → OpenRouter → Ollama)
│   ├── routes_*.py   # API-Endpunkte
│   ├── agent_base.py # Agent-Basisklasse
│   └── log.py        # Logging-Framework
├── agents/           # Agent-Definitionen (je ~8 Zeilen)
├── frontend/         # Vanilla HTML/CSS/JS
├── config/           # .env Dateien (NICHT committen!)
├── scripts/          # Setup & Utility-Scripts
└── docs/             # Dokumentation & Postmortems
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

### Die 40-Zeilen-Regel
- Jede Python-Datei sollte **maximal ~40 Zeilen** haben
- Wenn eine Datei zu groß wird, aufteilen in logische Module
- **Aber:** Lesbarkeit geht vor Kürze. Keine kryptischen Einzeiler!

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
