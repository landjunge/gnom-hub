import requests

config = {
    "generalag": {"provider": "openrouter", "model": "deepseek/deepseek-v4-flash:free"},
    "coderag": {"provider": "openrouter", "model": "qwen/qwen3-coder:free"},
    "watchdogag": {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
    "securityag": {"provider": "openrouter", "model": "openai/gpt-oss-120b:free"},
    "researcherag": {"provider": "openrouter", "model": "arcee-ai/trinity-large-thinking:free"},
    "editorag": {"provider": "openrouter", "model": "minimax/minimax-m2.5:free"},
    "writerag": {"provider": "openrouter", "model": "minimax/minimax-m2.5:free"},
    "summarizerag": {"provider": "openrouter", "model": "qwen/qwen3-next-80b:free"},
    "web_crawlerag": {"provider": "openrouter", "model": "nvidia/nemotron-nano-9b-v2:free"},
    "data_crawlerag": {"provider": "openrouter", "model": "nvidia/nemotron-nano-9b-v2:free"},
    "smart_crawlerag": {"provider": "openrouter", "model": "nvidia/nemotron-nano-9b-v2:free"}
}

r = requests.post("http://127.0.0.1:3002/api/llm/agents", json=config)
print(r.status_code, r.text)
