import asyncio, time, re, gnom_hub.infrastructure.database.state_repo as sr
from pathlib import Path
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, clean_key
DESKTOP_TXT = Path.home() / "Desktop" / "api_keys.txt"

async def sync_desktop_keys(db_keys: dict) -> dict:
    if not DESKTOP_TXT.exists(): return db_keys
    try:
        with open(DESKTOP_TXT, "r") as f: lines = [l.strip() for l in f if l.strip()]
        if not lines: return db_keys
        parsed = [(re.sub(r'^[\s#]*(UNGÜLTIG:\s*)?', '', l.split("=", 1)[0], flags=re.IGNORECASE).strip() if "=" in l else "API_KEY", clean_key(l)) for l in lines]
        to_verify = [pk for pk in parsed if pk[1] not in [v.get("key") for v in db_keys.values() if isinstance(v, dict)]]
        if to_verify:
            res_list = await asyncio.gather(*(auto_detect_and_verify(k, lbl) for lbl, k in to_verify), return_exceptions=True)
            for idx, ((lbl, clean_k), res) in enumerate(zip(to_verify, res_list)):
                d = res if isinstance(res, dict) else {}
                kid = f"k_{int(time.time() * 1000) + idx}"
                db_keys[kid] = {"id": kid, "key": clean_k, "provider": d.get("provider", "unknown"), "valid": d.get("valid", False), "info": d.get("info", str(res)), "caps": d.get("caps", []), "label": lbl}
        for lbl, k in parsed:
            for v in db_keys.values():
                if isinstance(v, dict) and v.get("key") == k: v["label"] = lbl
        db = {v.get("key"): v for v in db_keys.values() if isinstance(v, dict)}
        parsed = sorted(parsed, key=lambda pk: 0 if db.get(pk[1], {}).get('valid') else 1)
        target = "".join(f"{'# UNGÜLTIG: ' if not db.get(k, {}).get('valid') else ''}{db.get(k, {}).get('label', 'API_KEY')}={k}\n" for _, k in parsed)
        with open(DESKTOP_TXT, "r") as f: current = f.read()
        if current != target:
            with open(DESKTOP_TXT, "w") as f: f.write(target)
        db_keys = {kid: v for kid, v in sorted(db_keys.items(), key=lambda x: 0 if (isinstance(x[1], dict) and x[1].get("valid")) else 1)}
        sr.SQLiteStateRepository().set_value("llm_keys", db_keys)
    except Exception: pass
    return db_keys
def write_keys_to_desktop(keys: dict):
    try:
        with open(DESKTOP_TXT, "w") as f:
            sorted_ks = sorted((v for v in keys.values() if isinstance(v, dict) and v.get("key")), key=lambda x: 0 if x.get("valid") else 1)
            for k in sorted_ks:
                f.write(f"{'# UNGÜLTIG: ' if not k.get('valid') else ''}{k.get('label', 'API_KEY')}={k['key']}\n")
    except Exception: pass
