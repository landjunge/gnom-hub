import os
from dotenv import load_dotenv
from gnom_hub.core.config import CONFIG_DIR

_env = CONFIG_DIR / ".env"
if _env.exists():
    load_dotenv(dotenv_path=str(_env))

OR_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY_FREE_1")
DS_KEY = os.getenv("DEEPSEEK_API_KEY")

AGENT_MODELS = {
    "generalag":   ["meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"],
    "watchdogag":  ["meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"],
    "securityag":  ["meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"],
    "coderag":     ["qwen/qwen3-coder:free", "meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "google/gemma-4-31b-it:free"],
    "researcherag":["arcee-ai/trinity-large-thinking:free", "meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "google/gemma-4-31b-it:free"],
    "writerag":    ["minimax/minimax-m2.5:free", "meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "google/gemma-4-31b-it:free"],
    "editorag":    ["minimax/minimax-m2.5:free", "meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "google/gemma-4-31b-it:free"],
}
DEFAULT_MODELS = ["meta-llama/llama-3.3-70b-instruct:free", "nousresearch/hermes-3-llama-3.1-405b:free", "openai/gpt-oss-120b:free", "google/gemma-4-31b-it:free"]

def get_key_for(agent_name):
    return OR_KEY
