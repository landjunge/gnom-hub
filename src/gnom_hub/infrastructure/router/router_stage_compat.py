def is_valid(provider, kdb):
    return any(k.get("provider") == provider and k.get("valid") for k in kdb.values())

def resolve_stage(stage, kdb, agent_name):
    role = "coder" if "coder" in agent_name.lower() else "normal"
    for pvd, mdl in get_stage_options(stage, role):
        if pvd == "lokal" or is_valid(pvd, kdb): return pvd, mdl
    return "lokal", "llama3"

def get_stage_options(stage, role):
    s4 = [("anthropic", "claude-3-5-sonnet-20241022"), ("openai", "gpt-4o"), ("gemini", "gemini-1.5-pro"), ("deepseek", "deepseek-chat")]
    s3 = [("deepseek", "deepseek-chat"), ("gemini", "gemini-1.5-flash"), ("openrouter", "qwen/qwen3-coder:free" if role == "coder" else "meta-llama/llama-3.3-70b-instruct:free"), ("openai", "gpt-4o-mini"), ("mistral", "mistral-large-latest")]
    s2 = [("openrouter", "qwen/qwen3-coder:free" if role == "coder" else "meta-llama/llama-3.3-70b-instruct:free")]
    s1 = [("lokal", "llama3"), ("lokal", "llama3.2"), ("lokal", "mistral")]
    return (s4 + s3 + s2 + s1) if stage == "stage_4" else ((s3 + s2 + s1) if stage == "stage_3" else ((s2 + s1) if stage == "stage_2" else s1))
