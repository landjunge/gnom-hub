import os
from dotenv import load_dotenv
load_dotenv()

# === KEYS ===
OR_KEY = os.getenv("OPENROUTER_KEY_FREE_1")
DS_KEY = os.getenv("DEEPSEEK_API_KEY")

AGENT_MODELS = {
    "coderag":          ["deepseek/deepseek-v4-flash:free", "openai/gpt-oss-120b:free"],
    "writerag":         ["minimax/minimax-m2.5:free", "deepseek/deepseek-v4-flash:free"],
    "researcherag":     ["deepseek/deepseek-v4-flash:free", "minimax/minimax-m2.5:free"],
    "editorag":         ["openai/gpt-oss-120b:free", "minimax/minimax-m2.5:free"],
    "web_crawlerag":    ["openai/gpt-oss-20b:free", "nvidia/nemotron-nano-9b-v2:free"],
    "data_crawlerag":   ["openai/gpt-oss-20b:free", "deepseek/deepseek-v4-flash:free"],
    "smart_crawlerag":  ["nvidia/nemotron-nano-9b-v2:free", "openai/gpt-oss-20b:free"],
    "summarizerag":     ["openai/gpt-oss-20b:free", "nvidia/nemotron-nano-9b-v2:free"],
    "generalag":        ["deepseek/deepseek-v4-flash:free", "openai/gpt-oss-120b:free"],
}
DEFAULT_MODELS = ["deepseek/deepseek-v4-flash:free", "openai/gpt-oss-120b:free", "minimax/minimax-m2.5:free"]

def get_key_for(agent_name):
    """Holt den OpenRouter-Key für den Agenten."""
    return OR_KEY
