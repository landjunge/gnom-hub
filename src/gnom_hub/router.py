import os, json, requests
from dotenv import load_dotenv

load_dotenv()

# === KEYS (dediziert pro Worker für parallele Brainstorms) ===
OR_KEYS = {
    "writer":     os.getenv("OPENROUTER_KEY_FREE_1"),
    "coder":      os.getenv("OPENROUTER_KEY_FREE_2"),
    "researcher": os.getenv("OPENROUTER_KEY_FREE_1"),
    "editor":     os.getenv("OPENROUTER_KEY_FREE_4"),
    "crawler":    os.getenv("OPENROUTER_KEY_FREE_5"),
    "default":    os.getenv("OPENROUTER_KEY_FREE_1"),
}
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

LLM_TOKENS_FILE = os.path.join(os.path.dirname(__file__), "../../.gnom-hub-tokens.json")

def _track_tokens(key_name, model, usage):
    """Zählt Tokens pro Call und akkumuliert sie."""
    try:
        data = json.load(open(LLM_TOKENS_FILE)) if os.path.exists(LLM_TOKENS_FILE) else {"total": 0, "calls": 0, "history": []}
        prompt_t = usage.get("prompt_tokens", 0)
        comp_t = usage.get("completion_tokens", 0)
        total_t = usage.get("total_tokens", prompt_t + comp_t)
        data["total"] = data.get("total", 0) + total_t
        if ":free" in model:
            data["total_free"] = data.get("total_free", 0) + total_t
        else:
            data["total_pay"] = data.get("total_pay", 0) + total_t
        data["calls"] = data.get("calls", 0) + 1
        data["history"].append({"key": key_name, "model": model, "prompt": prompt_t, "completion": comp_t, "total": total_t})
        if len(data["history"]) > 200: data["history"] = data["history"][-200:]
        json.dump(data, open(LLM_TOKENS_FILE, "w"), indent=2)
        print(f"[TOKENS] +{total_t} (Gesamt: {data['total']}, Calls: {data['calls']})")
    except Exception as e:
        print(f"[TOKENS] Tracking-Fehler: {e}")

def _get_key_for(agent_name):
    """Holt den richtigen Key für den Agenten."""
    n = (agent_name or "").lower()
    if "web_crawler" in n:   return OR_KEYS["crawler"]
    if "data_crawler" in n:  return OR_KEYS["crawler"]
    if "smart_crawler" in n: return OR_KEYS["crawler"]
    n = n.replace("ag", "")
    return OR_KEYS.get(n, OR_KEYS["default"])

def ask_router(prompt, sys_prompt="Du bist ein hilfreicher Assistent.", agent_name=None):
    """Feuert auf das bevorzugte Modell des Agenten. Fallback-Kette wenn nötig."""
    n = (agent_name or "").lower()
    models = AGENT_MODELS.get(n, DEFAULT_MODELS)
    key = _get_key_for(agent_name)

    # Erst bevorzugte Modelle mit eigenem Key
    for model in models:
        if not key: continue
        try:
            print(f"\n[ROUTER] {agent_name or '?'} → {model}...")
            res = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]},
                timeout=120
            )
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    usage = data.get("usage", {})
                    if usage: _track_tokens(agent_name or "?", model, usage)
                    print(f"[ROUTER] Erfolg: {agent_name} auf {model}")
                    return choices[0]["message"]["content"]
                print(f"[ROUTER] {model}: 200 aber leere Antwort. Nächstes...")
            elif res.status_code == 429:
                import time; print(f"[ROUTER] {model}: Rate-Limit. Warte 2s..."); time.sleep(2)
            else:
                print(f"[ROUTER] {model} gescheitert ({res.status_code}). Nächstes...")
        except Exception as e:
            print(f"[ROUTER] Absturz auf {model}: {e}")

    # Letzte Rettung: DeepSeek bezahlt
    if DS_KEY:
        try:
            print(f"\n[ROUTER] Fallback → DeepSeek (bezahlt)...")
            res = requests.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DS_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]}
            )
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    usage = data.get("usage", {})
                    if usage: _track_tokens(agent_name or "?", "deepseek-chat", usage)
                    return choices[0]["message"]["content"]
        except Exception as e:
            print(f"[ROUTER] DeepSeek Absturz: {e}")

    return "[ROUTER-FEHLER] Alle Gleise offline."
