import os, json
from .config import TOKENS_FILE

LLM_TOKENS_FILE = str(TOKENS_FILE)

def track_tokens(key_name, model, usage):
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
        with open(LLM_TOKENS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[TOKENS] +{total_t} (Gesamt: {data['total']}, Calls: {data['calls']})")
    except Exception as e:
        print(f"[TOKENS] Tracking-Fehler: {e}")
