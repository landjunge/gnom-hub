import os, asyncio, time
from pathlib import Path
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, clean_key

DESKTOP_TXT = Path.home() / "Desktop" / "api_keys.txt"

async def sync_desktop_keys(db_keys: dict) -> dict:
    if not DESKTOP_TXT.exists(): return db_keys
    try:
        with open(DESKTOP_TXT, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines: return db_keys
        raw_k = [clean_key(l) for l in lines]
        to_verify = [k for k in raw_k if k not in [v.get("key") for v in db_keys.values() if isinstance(v, dict)]]
        
        if to_verify:
            res_list = await asyncio.gather(*(auto_detect_and_verify(k) for k in to_verify), return_exceptions=True)
            for idx, (clean_k, res) in enumerate(zip(to_verify, res_list)):
                d = res if isinstance(res, dict) else {}
                kid = f"k_{int(time.time() * 1000) + idx}"
                db_keys[kid] = {"id": kid, "key": clean_k, "provider": d.get("provider", "unknown"), "valid": d.get("valid", False), "info": d.get("info", str(res)), "caps": d.get("caps", [])}
            
        db_by_val = {v.get("key"): v for v in db_keys.values() if isinstance(v, dict)}
        target = "\n".join(f"{'# UNGÜLTIG: ' if not db_by_val.get(k, {}).get('valid') else ''}{db_by_val.get(k, {}).get('provider', 'unknown').upper()}_API_KEY={k}" for k in raw_k) + "\n"
        
        with open(DESKTOP_TXT, "r") as f: current = f.read()
        if current != target:
            with open(DESKTOP_TXT, "w") as f: f.write(target)
        SQLiteStateRepository().set_value("llm_keys", db_keys)
    except Exception: pass
    return db_keys

def write_keys_to_desktop(keys: dict):
    try:
        with open(DESKTOP_TXT, "w") as f:
            for k in (v for v in keys.values() if isinstance(v, dict) and v.get("key")):
                f.write(f"{'# UNGÜLTIG: ' if not k.get('valid') else ''}{k.get('provider', 'unknown').upper()}_API_KEY={k['key']}\n")
    except Exception: pass
