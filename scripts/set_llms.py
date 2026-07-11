"""Konfiguriert LLM-Modelle für alle aktiven Agenten."""
import os

import requests

HUB_PORT = os.environ.get("GNOM_HUB_PORT", "3002")

config = {
    "generalag": {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash:free"},
    "coderag": {"provider": "openrouter", "model": "qwen/qwen3-coder:free"},
    "watchdogag": {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
    "securityag": {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
    "researcherag": {"provider": "openrouter", "model": "arcee-ai/trinity-large-thinking:free"},
    "editorag": {"provider": "openrouter", "model": "minimax/minimax-m2.5:free"},
    "writerag": {"provider": "openrouter", "model": "minimax/minimax-m2.5:free"},
    "soulag": {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash:free"},
}

r = requests.post(f"http://127.0.0.1:{HUB_PORT}/api/llm/agents", json=config)
print(r.status_code, r.text)
