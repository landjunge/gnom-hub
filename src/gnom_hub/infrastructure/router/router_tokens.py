import logging
import os, json, threading, tempfile
from gnom_hub.core.config import TOKENS_FILE
from gnom_hub.core.logger import get_logger

logger = get_logger("router_tokens")
LLM_TOKENS_FILE = str(TOKENS_FILE)
_tokens_lock = threading.Lock()

def track_tokens(key_name, model, usage):
    with _tokens_lock:
        try:
            data = json.load(open(LLM_TOKENS_FILE)) if os.path.exists(LLM_TOKENS_FILE) else {"total": 0, "calls": 0, "history": []}
            prompt_t = usage.get("prompt_tokens", 0)
            comp_t = usage.get("completion_tokens", 0)
            total_t = usage.get("total_tokens", prompt_t + comp_t)
            data["total"] = data.get("total", 0) + total_t
            if ":free" in model: data["total_free"] = data.get("total_free", 0) + total_t
            else: data["total_pay"] = data.get("total_pay", 0) + total_t
            data["calls"] = data.get("calls", 0) + 1
            data.setdefault("history", []).append({"key": key_name, "model": model, "prompt": prompt_t, "completion": comp_t, "total": total_t})
            if len(data["history"]) > 200: data["history"] = data["history"][-200:]
            
            # Atomic write to prevent file corruption
            dir_name = os.path.dirname(LLM_TOKENS_FILE)
            fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_path, LLM_TOKENS_FILE)
            except Exception:
                if os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except OSError as e: logging.getLogger(__name__).error('Fehler in Temp-Datei-Bereinigung: %s', e)
                raise
                
            logger.info(f"[TOKENS] +{total_t} (Gesamt: {data['total']}, Calls: {data['calls']})")
        except Exception as e:
            logger.error(f"[TOKENS] Tracking-Fehler: {e}")
