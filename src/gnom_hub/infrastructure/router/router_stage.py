def is_valid(provider, kdb):
    for k in kdb.values():
        if k.get("provider") == provider and k.get("valid"):
            return True
    return False

def resolve_stage(stage, kdb, agent_name):
    role = "coder" if "coder" in agent_name.lower() else "normal"
    if stage == "stage_4":
        if is_valid("anthropic", kdb): return "anthropic", "claude-3-5-sonnet-20241022"
        if is_valid("openai", kdb): return "openai", "gpt-4o"
        if is_valid("gemini", kdb): return "gemini", "gemini-1.5-pro"
        if is_valid("deepseek", kdb): return "deepseek", "deepseek-chat"
        stage = "stage_3"
    if stage == "stage_3":
        if is_valid("deepseek", kdb): return "deepseek", "deepseek-chat"
        if is_valid("gemini", kdb): return "gemini", "gemini-1.5-flash"
        if is_valid("openrouter", kdb):
            return "openrouter", "qwen/qwen3-coder:free" if role == "coder" else "deepseek/deepseek-v4-flash:free"
        if is_valid("openai", kdb): return "openai", "gpt-4o-mini"
        if is_valid("mistral", kdb): return "mistral", "mistral-large-latest"
        stage = "stage_2"
    if stage == "stage_2":
        if is_valid("openrouter", kdb):
            return "openrouter", "qwen/qwen3-coder:free" if role == "coder" else "deepseek/deepseek-v4-flash:free"
    return "lokal", "llama3"
