import os
import socket
from pathlib import Path

# ── Basis-Verzeichnis ──
# Nutzt GNOM_HUB_HOME, falls gesetzt, ansonsten ~/.gnom-hub/
GNOM_HUB_HOME = Path(os.environ.get("GNOM_HUB_HOME", Path.home() / ".gnom-hub"))

# ── Strukturierte Unterordner ──
CONFIG_DIR = GNOM_HUB_HOME / "config"
DATA_DIR = GNOM_HUB_HOME / "data"
LOGS_DIR = GNOM_HUB_HOME / "logs"
RUN_DIR = GNOM_HUB_HOME / "run"

def init_directories():
    """
    Initialisiert die Basis-Verzeichnisstruktur.
    Wird beim Import automatisch ausgeführt.
    """
    # parents=True erstellt auch ~/.gnom-hub, falls es nicht existiert
    # exist_ok=True verhindert Fehler, wenn die Ordner schon da sind
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

# Direkt beim Laden des Moduls initialisieren
init_directories()

def get_base_dir() -> Path:
    """Gibt das absolute Basisverzeichnis zurück."""
    return GNOM_HUB_HOME

def get_data_dir() -> Path:
    """Gibt das Verzeichnis für Datenbank-JSON-Dateien zurück."""
    return DATA_DIR

def get_logs_dir() -> Path:
    """Gibt das Verzeichnis für System- und Agenten-Logs zurück."""
    return LOGS_DIR

def get_run_dir() -> Path:
    """Gibt das Verzeichnis für PID-Dateien und temporäre Runtime-Dateien zurück."""
    return RUN_DIR

def get_config_path() -> Path:
    """Gibt den Pfad zur Haupt-Konfigurationsdatei zurück."""
    return CONFIG_DIR / "gnom-hub.toml"

def get_agents_dir() -> Path:
    """
    Gibt den Pfad zum agents-Ordner zurück.
    Wird NICHT automatisch initialisiert, sondern von der Datenbank
    bei der Registrierung des ersten Agenten angelegt.
    """
    return DATA_DIR / "agents"

def format_display_path(path: Path) -> str:
    """
    Gibt den Pfad als String zurück und ersetzt das Home-Verzeichnis durch ~,
    damit Ausgaben sauber und nutzerunabhängig bleiben.
    """
    try:
        home_str = str(Path.home())
        path_str = str(path)
        if path_str.startswith(home_str):
            return path_str.replace(home_str, "~", 1)
        return path_str
    except Exception:
        return str(path)

def find_free_port(start_port: int = 3000, end_port: int = 4000) -> int:
    """
    Sucht nach einem freien Port im angegebenen Bereich.
    """
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Kein freier Port im Bereich {start_port}-{end_port} gefunden.")
