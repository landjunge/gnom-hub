import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv()

HOME = Path(os.getenv("GNOM_HUB_HOME", Path.home() / ".gnom-hub"))
DATA_DIR, RUN_DIR = HOME / "data", HOME / "run"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WORKSPACE_DIR, FRONTEND_DIR, CONFIG_DIR = PROJECT_ROOT / "gnom_workspace", PROJECT_ROOT / "frontend", PROJECT_ROOT / "config"
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
