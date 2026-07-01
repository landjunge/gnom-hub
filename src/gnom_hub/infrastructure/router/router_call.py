# router_call.py — Router API calls executor with token tracking
import json
import logging
import time

import requests

from .router_keys import get_keys
from .router_tokens import track_tokens

# HTTP status codes that should trigger key rotation in _try_keys once the
# in-call retry loop is exhausted. We raise _RetryableCallError so _try_keys
# can advance to the next key in the rotation list.
RETRYABLE_STATUS = (429, 500, 502, 503, 504)


class _RetryableCallError(Exception):
    """Internal signal: status code indicates the caller should try the next key."""

    def __init__(self, status_code: int, provider: str):
        self.status_code = status_code
        self.provider = provider
        super().__init__(f"{provider} returned retryable status {status_code}")


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
    except Exception as e:
        logging.getLogger(__name__).debug("Lokales Model-Resolving fehlgeschlagen: %s", e)
    return requested_model

def _call(pvd, mdl, key, msgs, n):
    if pvd == "lokal":
        mdl = resolve_local_model(mdl)
    elif pvd == "deepseek":
        # Map stage-3/stage-4 alias names to the actual DeepSeek API ids.
        if mdl in ("deepseek-v4-pro", "deepseek-reasoner"):
            mdl = "deepseek-reasoner"
        elif mdl.startswith("deepseek-v4") or mdl == "deepseek-v4-flash":
            mdl = "deepseek-chat"
    h, urls = {"Content-Type": "application/json"}, {"openai": "https://api.openai.com/v1/chat/completions", "mistral": "https://api.mistral.ai/v1/chat/completions", "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "deepseek": "https://api.deepseek.com/chat/completions", "openrouter": "https://openrouter.ai/api/v1/chat/completions", "lokal": "http://127.0.0.1:11434/api/chat", "anthropic": "https://api.anthropic.com/v1/messages", "minimax": "https://api.minimax.io/v1/chat/completions"}
    url = urls.get(pvd, urls["openrouter"])
    limit = {"generalag": 6000, "soulag": 6000, "securityag": 6000, "watchdogag": 6000, "coderag": 6000, "writerag": 6000, "researcherag": 6000, "editorag": 6000}.get(n.lower() if n else "", 6000)
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
        # M3 (MiniMax) generiert endlos wenn nicht gestoppt → stop nach 深思
        if pvd == "minimax":
            existing = pyld.get("stop")
            stop_token = "深思"  # noqa: S105 — Sentinel-String für LLM stop-Sequence, kein Passwort
            if isinstance(existing, list):
                if stop_token not in existing:
                    pyld["stop"] = existing + [stop_token]
            else:
                pyld["stop"] = [stop_token]

    # CoderAG braucht mehr Zeit — komplexe Tasks brauchen 60-120s
    # Lokal: 20s, OpenRouter/DeepSeek: 90s
    req_timeout = 20 if pvd == "lokal" else 90
    max_retries = 1 if pvd == "lokal" else 2
    last_status = None
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=h, json=pyld, timeout=req_timeout)
            last_status = r.status_code
            if r.status_code == 200:
                try: res_json = r.json()
                except (json.JSONDecodeError, ValueError): res_json = {}
                if pvd == "anthropic": ans = res_json.get("content", [{}])[0].get("text")
                elif pvd == "lokal" and not res_json: ans = "".join(json.loads(letter).get("message", {}).get("content", "") for letter in r.text.strip().split("\n") if letter).strip()
                elif pvd == "lokal": ans = res_json.get("message", {}).get("content", "")
                else:
                    msg_obj = res_json.get("choices", [{}])[0].get("message", {})
                    ans = msg_obj.get("content", "")
                    reasoning = msg_obj.get("reasoning_content") or msg_obj.get("reasoning")
                    if reasoning:
                        ans = f"<\u2588think>\n{reasoning}\n<\u2588/think>\n\n{ans}"
                if ans: _track(pvd, mdl, n, res_json, msgs, ans); return ans

            if r.status_code in RETRYABLE_STATUS:
                # Retry on the same key once. If we exhaust retries, raise so
                # _try_keys moves on to the next key in the rotation.
                time.sleep(1.5 * (attempt + 1))
                if attempt == max_retries - 1:
                    raise _RetryableCallError(r.status_code, pvd)
            else:
                # Non-retryable status (400, 401, 403, 404, ...). Surface it
                # immediately so _try_keys can rotate keys instead of stalling.
                raise _RetryableCallError(r.status_code, pvd)
        except _RetryableCallError:
            raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1.5 * (attempt + 1))
    if last_status is not None:
        logging.getLogger(__name__).debug(
            "_call for %s/%s ended without a 2xx (last status=%s)", pvd, mdl, last_status
        )
    return None


def _try_keys(pvd, mdl, kdb, msgs, an):
    """Try every available key for ``pvd`` until one returns a non-empty answer.

    Rotation is triggered by both transient errors *and* retryable HTTP status
    codes (429 rate-limit, 5xx server errors, 401/403 auth failures). Previously
    a single 429 silently killed the whole call even if other valid keys were
    available — that bug is now fixed by raising :class:`_RetryableCallError`
    out of :func:`_call`.
    """
    last_err = None
    for k in get_keys(pvd, kdb):
        try:
            ans = _call(pvd, mdl, k, msgs, an)
            if ans:
                return ans
        except _RetryableCallError as e:
            last_err = e
            logging.getLogger(__name__).warning(
                'Provider %s key rotiert wegen Status %s', pvd, e.status_code
            )
            continue
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in API-Schlüssel-Aufruf: %s', e)
            last_err = e
            continue
    if last_err is not None:
        logging.getLogger(__name__).debug(
            '_try_keys für %s/%s erschöpft ohne Antwort (letzter Fehler: %s)',
            pvd, mdl, last_err,
        )
    return None
