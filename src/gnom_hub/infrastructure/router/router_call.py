# router_call.py — Router API calls executor with token tracking
import logging
import requests, time, json; from .router_tokens import track_tokens; from .router_keys import get_keys
def _track(pvd, mdl, n, r_json, msgs, ans):
    try:
        u = r_json.get("usage") or {}
        p_t = u.get("prompt_tokens") or u.get("input_tokens") or r_json.get("prompt_eval_count")
        c_t = u.get("completion_tokens") or u.get("output_tokens") or r_json.get("eval_count")
        if not p_t:
            p_t = int(len(" ".join(m.get("content", "") for m in msgs).split()) * 1.3) or 1
            c_t = int(len((ans or "").split()) * 1.3) or 1
        track_tokens(n or "?", mdl, {"prompt_tokens": p_t, "completion_tokens": c_t})
    except Exception as e: logging.getLogger(__name__).error('Fehler in Token-Tracking: %s', e)

def resolve_local_model(requested_model: str) -> str:
    try:
        import requests
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        if r.status_code == 200:
            models_data = r.json().get("models", [])
            installed_models = [m["name"] for m in models_data]
            if not installed_models:
                return requested_model
            # 1. Exact match
            if requested_model in installed_models:
                return requested_model
            # 2. Match without tag (e.g. "llama3" matches "llama3:latest")
            for m in installed_models:
                if m.split(":")[0] == requested_model:
                    return m
            # 3. Match substring (e.g. "llama3" matches "llama3.1")
            for m in installed_models:
                if requested_model.lower() in m.lower():
                    return m
            # 4. Fallback to first installed model
            return installed_models[0]
    except Exception:
        pass
    return requested_model

def _call(pvd, mdl, key, msgs, n):
    if pvd == "lokal":
        mdl = resolve_local_model(mdl)
    elif pvd == "deepseek":
        if mdl == "deepseek-v4-pro":
            mdl = "deepseek-reasoner"
        elif mdl.startswith("deepseek-v4"):
            mdl = "deepseek-chat"
    h, urls = {"Content-Type": "application/json"}, {"openai": "https://api.openai.com/v1/chat/completions", "mistral": "https://api.mistral.ai/v1/chat/completions", "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "deepseek": "https://api.deepseek.com/chat/completions", "openrouter": "https://openrouter.ai/api/v1/chat/completions", "lokal": "http://127.0.0.1:11434/api/chat", "anthropic": "https://api.anthropic.com/v1/messages"}
    url = urls.get(pvd, urls["openrouter"])
    limit = 1500 if n and n.lower() == "generalag" else (1000 if n and n.lower() == "soulag" else None)
    temp = None
    if n:
        try:
            from gnom_hub.db import get_state_value
            creativity = get_state_value("agent_settings", {}).get(n.lower(), {}).get("creativity", 3)
            temp = {1: 0.1, 2: 0.4, 3: 0.7, 4: 0.9, 5: 1.2}.get(creativity, 0.7)
        except Exception as e: logging.getLogger(__name__).error('Fehler in Kreativitäts-Einstellung-Laden: %s', e)
    if pvd == "anthropic":
        h.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        sys = next((m["content"] for m in msgs if m["role"] == "system"), "")
        pyld = {"model": mdl, "max_tokens": limit or 1024, "messages": [m for m in msgs if m["role"] != "system"]}
        if sys: pyld["system"] = sys
        if temp is not None: pyld["temperature"] = temp
    else:
        if pvd != "lokal": h["Authorization"] = f"Bearer {key}"
        pyld = {"model": mdl, "messages": msgs, "stream": False} if pvd == "lokal" else {"model": mdl, "messages": msgs}
        if limit:
            if pvd == "lokal": pyld.setdefault("options", {})["num_predict"] = limit
            else: pyld["max_tokens"] = limit
        if temp is not None:
            if pvd == "lokal": pyld.setdefault("options", {})["temperature"] = temp
            else: pyld["temperature"] = temp

    for attempt in range(3):
        try:
            r = requests.post(url, headers=h, json=pyld, timeout=120)
            if r.status_code == 200:
                try: res_json = r.json()
                except Exception: res_json = {}
                if pvd == "anthropic": ans = res_json.get("content", [{}])[0].get("text")
                elif pvd == "lokal" and not res_json: ans = "".join(json.loads(l).get("message", {}).get("content", "") for l in r.text.strip().split("\n") if l).strip()
                elif pvd == "lokal": ans = res_json.get("message", {}).get("content", "")
                else:
                    msg_obj = res_json.get("choices", [{}])[0].get("message", {})
                    ans = msg_obj.get("content", "")
                    reasoning = msg_obj.get("reasoning_content") or msg_obj.get("reasoning")
                    if reasoning:
                        ans = f"<think>\n{reasoning}\n</think>\n\n{ans}"
                if ans: _track(pvd, mdl, n, res_json, msgs, ans); return ans
            
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
            else:
                break
        except Exception as e:
            if attempt == 2: raise e
            time.sleep(1.5 * (attempt + 1))
def _try_keys(pvd, mdl, kdb, msgs, an):
    for k in get_keys(pvd, kdb):
        try:
            if ans := _call(pvd, mdl, k, msgs, an): return ans
        except Exception as e: logging.getLogger(__name__).error('Fehler in API-Schlüssel-Aufruf: %s', e)
