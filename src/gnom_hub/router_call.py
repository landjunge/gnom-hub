# router_call.py — Low-level LLM call helpers
import requests, time, json; from .router_tokens import track_tokens
def _ext(d, a, m):
    c = d.get("choices", [])
    if c and c[0].get("message", {}).get("content"):
        if d.get("usage"): track_tokens(a or "?", m, d["usage"])
        return c[0]["message"]["content"]
    return None
def _call(pvd, mdl, key, msgs, n):
    url = "http://127.0.0.1:11434/api/chat" if pvd == "lokal" else ("https://api.deepseek.com/chat/completions" if pvd == "deepseek" else "https://openrouter.ai/api/v1/chat/completions")
    h = {"Content-Type": "application/json"}
    if pvd != "lokal": h["Authorization"] = f"Bearer {key}"
    pyld = {"model": mdl, "messages": msgs}
    if pvd == "lokal": pyld["stream"] = False
    r = requests.post(url, headers=h, json=pyld, timeout=120)
    if r.status_code == 200:
        if pvd != "lokal": return _ext(r.json(), n, mdl)
        return "".join(json.loads(l).get("message", {}).get("content", "") for l in r.text.strip().split("\n") if l).strip() or None
    if r.status_code == 429: time.sleep(2)
    return None
def _try(pvd, mdl, key, msgs, n):
    try: return _call(pvd, mdl, key, msgs, n) or None
    except Exception: return None
def get_keys(pvd, kdb):
    import os; from .router_config import DS_KEY, OR_KEY
    ks = [k.get("key") for k in (kdb.values() if isinstance(kdb, dict) else kdb) if k.get("provider") == pvd and k.get("valid")]
    if pvd == "deepseek" and DS_KEY: ks.append(DS_KEY)
    elif pvd == "openrouter":
        ks.extend([os.environ.get(f"OPENROUTER_KEY_FREE_{i}") for i in range(1, 6) if os.environ.get(f"OPENROUTER_KEY_FREE_{i}")])
        if OR_KEY: ks.append(OR_KEY)
    return list(dict.fromkeys(ks))
def _try_keys(pvd, mdl, kdb, msgs, an):
    for k in get_keys(pvd, kdb):
        ans = _try(pvd, mdl, k, msgs, an)
        if ans: return ans
