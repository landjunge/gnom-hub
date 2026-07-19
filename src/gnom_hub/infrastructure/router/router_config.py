import os

from dotenv import load_dotenv

from gnom_hub.core.config import CONFIG_DIR

_env = CONFIG_DIR / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))

OR_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY_FREE_1")
DS_KEY = os.getenv("DEEPSEEK_API_KEY")

# 2026-07: meta-llama/llama-3.3-70b-instruct:free is permanently 404 (paid-only).
# Prefer openrouter/free + currently working free slugs first.
AGENT_MODELS = {
    "generalag":   ["openrouter/free", "tencent/hy3:free", "google/gemma-4-31b-it:free", "openai/gpt-oss-120b:free"],
    "watchdogag":  ["openrouter/free", "tencent/hy3:free", "google/gemma-4-31b-it:free", "openai/gpt-oss-120b:free"],
    "securityag":  ["openrouter/free", "tencent/hy3:free", "google/gemma-4-31b-it:free", "openai/gpt-oss-120b:free"],
    "coderag":     ["openrouter/free", "tencent/hy3:free", "qwen/qwen3-coder:free", "google/gemma-4-31b-it:free"],
    "researcherag":["openrouter/free", "tencent/hy3:free", "arcee-ai/trinity-large-thinking:free", "google/gemma-4-31b-it:free"],
    "writerag":    ["openrouter/free", "tencent/hy3:free", "minimax/minimax-m2.5:free", "google/gemma-4-31b-it:free"],
    "editorag":    ["openrouter/free", "tencent/hy3:free", "minimax/minimax-m2.5:free", "google/gemma-4-31b-it:free"],
}
DEFAULT_MODELS = ["openrouter/free", "tencent/hy3:free", "google/gemma-4-31b-it:free", "openai/gpt-oss-120b:free"]

def get_key_for(agent_name):
    return OR_KEY
