import requests
from .router_config import DS_KEY, OR_KEY, AGENT_MODELS, DEFAULT_MODELS, get_key_for
from .router_tokens import track_tokens

def _extract(data, agent_name, model):
    """Prüft ob LLM-Antwort gültig ist und trackt Tokens."""
    choices = data.get("choices", [])
    if choices and choices[0].get("message", {}).get("content"):
        usage = data.get("usage", {})
        if usage: track_tokens(agent_name or "?", model, usage)
        print(f"[ROUTER] Erfolg: {agent_name} auf {model}")
        return choices[0]["message"]["content"]
    return None

def ask_router(prompt, sys_prompt="Du bist ein hilfreicher Assistent.", agent_name=None):
    """DeepSeek zuerst, OpenRouter-Free als Fallback."""
    n = (agent_name or "").lower()
    msgs = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}]

    # 1. DeepSeek (primär)
    if DS_KEY:
        try:
            print(f"\n[ROUTER] {agent_name or '?'} → DeepSeek...")
            res = requests.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DS_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": msgs}, timeout=120)
            if res.status_code == 200:
                r = _extract(res.json(), agent_name, "deepseek-chat")
                if r: return r
            print(f"[ROUTER] DeepSeek: {res.status_code}. Fallback...")
        except Exception as e:
            print(f"[ROUTER] DeepSeek Fehler: {e}. Fallback...")

    # 2. OpenRouter Free (Fallback)
    for model in AGENT_MODELS.get(n, DEFAULT_MODELS):
        if not OR_KEY: continue
        try:
            print(f"[ROUTER] {agent_name or '?'} → {model}...")
            res = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": msgs}, timeout=120)
            if res.status_code == 200:
                r = _extract(res.json(), agent_name, model)
                if r: return r
                print(f"[ROUTER] {model}: leere Antwort. Nächstes...")
            elif res.status_code == 429:
                import time; print(f"[ROUTER] {model}: Rate-Limit. Warte 2s..."); time.sleep(2)
            else:
                print(f"[ROUTER] {model} gescheitert ({res.status_code}).")
        except Exception as e:
            print(f"[ROUTER] Absturz auf {model}: {e}")

    return "[ROUTER-FEHLER] Alle Gleise offline."
