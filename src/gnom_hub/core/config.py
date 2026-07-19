import logging
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
load_dotenv(CONFIG_DIR / ".env")

# Support running multiple instances simultaneously by isolating paths based on the port.
# Workspace ist IMMER port-unabhängig: ~/gnom-Workspace (oder env-override) — damit
# Agenten ihre Files nicht verlieren wenn man auf einem anderen Port startet. Nur das
# data_dir (DB) und run_dir (PIDs) sind port-spezifisch für echte Instanz-Isolation.
port = os.getenv("GNOM_HUB_PORT", "3002")

if port == "3002":
    default_home = Path.home() / ".gnom-hub"
else:
    default_home = Path.home() / f".gnom-hub-{port}"

# Workspace ist port-unabhängig (default ~/gnom-Workspace) — Files überleben
# Instanz-Wechsel, Auto-Route-Wechsel, Port-Sprünge.
default_workspace = Path.home() / "gnom-Workspace"

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

    # ── Context Offload (TencentDB-Agent-Memory port) ─────────────────────
    # Defaults mirror the upstream TencentDB plugin
    # (``openclaw.plugin.json::offload``) where they overlap. Offload is
    # additive and OFF by default — set OFFLOAD_ENABLED=true (or edit
    # the field) to activate.
    OFFLOAD_ENABLED = os.getenv("OFFLOAD_ENABLED", "False").lower() == "true"
    OFFLOAD_MILD_RATIO = float(os.getenv("OFFLOAD_MILD_RATIO", "0.5"))
    OFFLOAD_AGGRESSIVE_RATIO = float(os.getenv("OFFLOAD_AGGRESSIVE_RATIO", "0.85"))
    OFFLOAD_DATA_DIR = os.getenv("OFFLOAD_DATA_DIR", "data/offload")
    # Token budget used as the denominator for the two ratios above.
    # Matches the LLM context-window setting in ``router.py``; can be
    # overridden per-agent via the LLM provider's ``max_tokens`` later.
    OFFLOAD_MAX_TOKENS = int(os.getenv("OFFLOAD_MAX_TOKENS", "8000"))

    # ── TKG im Agent-Loop (S5 local-first) ────────────────────────────────
    # Auto-Recall: relevante TKG-Facts vor jedem LLM-Call in den System-
    # Prompt injizieren. Auto-Curate: aus extrahierten Thought-Facts auch
    # in den TKG schreiben. Beides best-effort, fail-open.
    TKG_AUTO_RECALL = os.getenv("TKG_AUTO_RECALL", "true").lower() in (
        "1", "true", "yes", "on",
    )
    TKG_AUTO_CURATE = os.getenv("TKG_AUTO_CURATE", "true").lower() in (
        "1", "true", "yes", "on",
    )

    # ── Routing-Determinism (opt-in Feature Flag) ─────────────────────────
    # Wenn aktiviert, läuft zusätzlich zum LLM-basierten ask_router ein
    # deterministischer Capability-Resolver
    # (:func:`gnom_hub.agents.routing.resolve_capability`) auf jedem
    # User-Prompt. Das Ergebnis wird geloggt + im State-Store unter
    # ``routing_resolution_<agent>_<ts>`` abgelegt — die existierende
    # ask_router-Pfadführung wird NICHT ersetzt, nur ergänzt.
    # Default: AUS, damit bestehende Verhalten garantiert unverändert
    # bleiben. Setzen via ``ROUTING_DETERMINISTIC_MODE=true`` oder
    # mutation von ``Config.ROUTING_DETERMINISTIC_MODE`` in Tests.
    ROUTING_DETERMINISTIC_MODE = os.getenv("ROUTING_DETERMINISTIC_MODE", "False").lower() == "true"
    # Logging-Level für Routing-Decisions (Info für Production-Beobachtung,
    # Debug für Entwicklung).
    ROUTING_LOG_LEVEL = os.getenv("ROUTING_LOG_LEVEL", "info").lower()
    # Welche Capabilities als "Fallback-Chain-Whitelist" gelten, wenn die
    # primäre Auflösung leer liefert. JSON-artige Komma-Liste.
    ROUTING_FALLBACK_CAPS = [
        c.strip().lower() for c in
        os.getenv("ROUTING_FALLBACK_CAPS", "general").split(",")
        if c.strip()
    ]
    # Maximale Anzahl Log-Einträge pro Agent im State-Store (Rotation).
    ROUTING_RESOLUTION_LOG_MAX = int(os.getenv("ROUTING_RESOLUTION_LOG_MAX", "50"))
    # Schwellwert (0.0–1.0) — Resolutionen unterhalb dieses Confidence-
    # Werts werden nur als INFO geloggt, nicht in den State-Store
    # geschrieben. Vermeidet Lärm bei No-Match-Fällen.
    ROUTING_RESOLUTION_LOG_MIN_CONF = float(os.getenv("ROUTING_RESOLUTION_LOG_MIN_CONF", "0.3"))

    @classmethod
    def get_supergnom_template(cls) -> str:
        import json
        config_path = cls.BASE_DIR / "supergnom_config.json"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("template", "chat")
            except Exception as e:
                logging.getLogger(__name__).error('Fehler in get_supergnom_template: %s', e)
        return "chat"

    # OpenRouter Free-Modelle (zentral verwaltet)
    OPENROUTER_FREE_MODELS = [
        "openrouter/free",  # Auto-router über Free-Pool
        "tencent/hy3:free",  # live-verified 2026-07
        "qwen/qwen3-coder:free",
        "openai/gpt-oss-20b:free",
        "meta-llama/llama-3.2-3b-instruct:free",
        # NOTE: meta-llama/llama-3.3-70b-instruct:free is permanently 404 (paid-only)
        # NOTE: nvidia/nemotron free slugs often 404/429 — deprioritized
    ]

try:
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logging.getLogger(__name__).warning("Log-Verzeichnis konnte nicht erstellt werden: %s", e)