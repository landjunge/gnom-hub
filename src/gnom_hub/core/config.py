import os
import logging
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
load_dotenv(CONFIG_DIR / ".env")

# Support running multiple instances simultaneously by isolating paths based on the port
port = os.getenv("GNOM_HUB_PORT", "3002")

if port == "3002":
    default_home = Path.home() / ".gnom-hub"
    # Default workspace: ~/gnom-Workspace (ausgelagert aus dem Gnom-Hub-Repo)
    default_workspace = Path.home() / "gnom-Workspace"
else:
    default_home = Path.home() / f".gnom-hub-{port}"
    # Mehrere Instanzen: separater Workspace-Pfad pro Port, parallel zu HOME
    default_workspace = Path.home() / f"gnom-Workspace-{port}"

HOME = Path(os.getenv("GNOM_HUB_HOME", default_home))
GNOM_HUB_HOME = HOME
DATA_DIR, RUN_DIR = HOME / "data", HOME / "run"
# Initial-Wert: env override > default. Der zur Laufzeit über die UI
# gesetzte Override wird via `Config.workspace_dir()` aufgelöst.
WORKSPACE_DIR = Path(os.getenv("GNOM_HUB_WORKSPACE", default_workspace))
FRONTEND_DIR = PROJECT_ROOT / "src" / "gnom_hub" / "frontend"
TOKENS_FILE = CONFIG_DIR / f".gnom-hub-tokens-{port}.json"
DB_PATH = DATA_DIR / "gnomhub.db"

for d in (DATA_DIR, RUN_DIR, WORKSPACE_DIR, CONFIG_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _state_workspace_override() -> Path | None:
    """Liest den via UI / API gesetzten Workspace-Pfad aus dem State-Store.

    Liefert None, wenn kein Override gesetzt ist oder der State-Store nicht
    verfügbar ist (z. B. während Migration / bei DB-Fehlern).
    """
    try:
        from gnom_hub.db import get_state_value
        v = get_state_value("workspace_dir_override")
        if v and isinstance(v, str) and v.strip():
            return Path(v).expanduser().resolve()
    except Exception:
        return None
    return None


class Config:
    BASE_DIR, DATA_DIR, LOG_DIR = PROJECT_ROOT, DATA_DIR, DATA_DIR / "logs"
    DB_PATH = DB_PATH
    DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY_FREE_1")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    HOST, PORT = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PID_DIR = RUN_DIR
    SUPERGNOM_MODE = os.getenv("SUPERGNOM_MODE", "False").lower() == "true"
    SUPERGNOM_CONFIG = os.getenv("SUPERGNOM_CONFIG", "")

    # ── Hot-reload-fähiger Workspace-Pfad ────────────────────────────────
    # Der Modul-Level WORKSPACE_DIR oben bleibt der Initialwert (Env > Default).
    # `workspace_dir()` löst zur Laufzeit zusätzlich einen via UI gesetzten
    # State-Override auf. Code, der `Config.workspace_dir()` benutzt, sieht
    # Änderungen sofort — Code, der das Modul-Level WORKSPACE_DIR importiert,
    # erst nach Neustart. Konvertierung wird schrittweise in den Aufrufern
    # vorgenommen.
    @classmethod
    def workspace_dir(cls) -> Path:
        override = _state_workspace_override()
        if override is not None:
            return override
        # Wenn der Modul-Initialwert ungültig ist (z. B. weil
        # GNOM_HUB_WORKSPACE leer war und Path("") = "." liefert),
        # fallen wir auf ~/gnom-Workspace zurück.
        if str(WORKSPACE_DIR) == "." or str(WORKSPACE_DIR) == "":
            return Path.home() / "gnom-Workspace"
        return WORKSPACE_DIR

    @classmethod
    def get_supergnom_template(cls) -> str:
        import json
        config_path = cls.BASE_DIR / "supergnom_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("template", "chat")
            except Exception as e:
                logging.getLogger(__name__).error('Fehler in get_supergnom_template: %s', e)
        return "chat"

    # OpenRouter Free-Modelle (zentral verwaltet)
    OPENROUTER_FREE_MODELS = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-coder:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "google/gemma-4-31b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openai/gpt-oss-120b:free",
    ]

try:
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logging.getLogger(__name__).warning("Log-Verzeichnis konnte nicht erstellt werden: %s", e)