import os, logging; from pathlib import Path; from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
load_dotenv(CONFIG_DIR / ".env")

HOME = Path(os.getenv("GNOM_HUB_HOME", Path.home() / ".gnom-hub"))
GNOM_HUB_HOME = HOME
DATA_DIR, RUN_DIR = HOME / "data", HOME / "run"
WORKSPACE_DIR, FRONTEND_DIR = PROJECT_ROOT / "gnom_workspace", PROJECT_ROOT / "src" / "gnom_hub" / "frontend"
TOKENS_FILE, DB_PATH = CONFIG_DIR / ".gnom-hub-tokens.json", DATA_DIR / "gnomhub.db"

for d in (DATA_DIR, RUN_DIR, WORKSPACE_DIR, CONFIG_DIR): d.mkdir(parents=True, exist_ok=True)

class Config:
    BASE_DIR, DATA_DIR, LOG_DIR = PROJECT_ROOT, DATA_DIR, DATA_DIR / "logs"
    WORKSPACE_DIR, DB_PATH = WORKSPACE_DIR, DB_PATH
    DB_ECHO = os.getenv("DB_ECHO", "False").lower() == "true"
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    HOST, PORT = os.getenv("HOST", "127.0.0.1"), int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    PID_DIR = RUN_DIR
    ENABLE_WORKSPACE_SANDBOX = os.getenv("ENABLE_WORKSPACE_SANDBOX", "True").lower() == "true"
    SUPERGNOM_MODE = os.getenv("SUPERGNOM_MODE", "False").lower() == "true"
    SUPERGNOM_CONFIG = os.getenv("SUPERGNOM_CONFIG", "")

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
        "baidu/cobuddy:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "poolside/laguna-xs.2:free",
        "poolside/laguna-m.1:free",
        "deepseek/deepseek-v4-flash:free",
        "google/gemma-2-9b-it",
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "qwen/qwen2.5-7b-instruct",
        "deepseek/deepseek-chat",
        "llama3.2",
    ]

Config.LOG_DIR.mkdir(parents=True, exist_ok=True)
