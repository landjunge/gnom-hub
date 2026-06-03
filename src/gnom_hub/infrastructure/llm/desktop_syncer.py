import asyncio, time, re, os, logging, gnom_hub.db.state_repo as sr
from pathlib import Path
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, clean_key
DESKTOP_TXT = Path.home() / "Desktop" / "api_keys.txt"

async def sync_desktop_keys(db_keys: dict) -> dict:
    if not DESKTOP_TXT.exists():
        # Keep only valid keys if file doesn't exist
        db_keys = {kid: v for kid, v in db_keys.items() if isinstance(v, dict) and v.get("valid")}
        return db_keys
    try:
        with open(DESKTOP_TXT, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            # Clear keys if file is empty
            sr.SQLiteStateRepository().set_value("llm_keys", {})
            return {}
            
        parsed_active = []
        parsed_invalid = []
        for l in lines:
            is_comment = l.startswith("#") or "UNGÜLTIG" in l.upper()
            parts = l.split("=", 1)
            lbl = re.sub(r'^[\s#]*(UNGÜLTIG:\s*)?', '', parts[0], flags=re.IGNORECASE).strip() if len(parts) > 1 else "API_KEY"
            key = clean_key(l)
            if key:
                if is_comment:
                    parsed_invalid.append((lbl, key))
                else:
                    parsed_active.append((lbl, key))
                    
        # Verify new active keys
        to_verify = []
        for lbl, k in parsed_active:
            already_valid = False
            for v in db_keys.values():
                if isinstance(v, dict) and v.get("key") == k and v.get("valid"):
                    already_valid = True
                    v["label"] = lbl
                    break
            if not already_valid:
                to_verify.append((lbl, k))
                
        if to_verify:
            res_list = await asyncio.gather(*(auto_detect_and_verify(k, lbl) for lbl, k in to_verify), return_exceptions=True)
            for idx, ((lbl, clean_k), res) in enumerate(zip(to_verify, res_list)):
                d = res if isinstance(res, dict) else {}
                if d.get("valid"):
                    kid = f"k_{int(time.time() * 1000) + idx}"
                    db_keys[kid] = {
                        "id": kid, "key": clean_k, "provider": d.get("provider", "unknown"),
                        "valid": True, "info": "OK", "caps": d.get("caps", []), "label": lbl
                    }
                else:
                    parsed_invalid.append((lbl, clean_k))
                    
        # Keep only valid active keys
        active_keys = [k for _, k in parsed_active]
        db_keys = {
            kid: v for kid, v in db_keys.items()
            if isinstance(v, dict) and v.get("valid") and v.get("key") in active_keys
        }
        
        # Rewrite to Desktop txt
        new_lines = []
        for kid, v in db_keys.items():
            new_lines.append(f"{v.get('label', 'API_KEY')}={v['key']}\n")
        for lbl, k in parsed_invalid:
            new_lines.append(f"# UNGÜLTIG: {lbl}={k}\n")
            
        target = "".join(new_lines)
        with open(DESKTOP_TXT, "r") as f:
            current = f.read()
        if current != target:
            with open(DESKTOP_TXT, "w") as f:
                f.write(target)
            os.chmod(DESKTOP_TXT, 0o600)
                
        sr.SQLiteStateRepository().set_value("llm_keys", db_keys)
        
        # Trigger model check in background immediately on desktop sync
        if any(v.get("provider") == "openrouter" and v.get("valid") for v in db_keys.values()):
            from gnom_hub.api.endpoints.llm_models import check_and_update_models
            asyncio.create_task(check_and_update_models())
    except Exception as e:
        print(f"Error in sync_desktop_keys: {e}")
    return db_keys

def write_keys_to_desktop(keys: dict):
    try:
        existing_invalid = []
        if DESKTOP_TXT.exists():
            with open(DESKTOP_TXT, "r") as f:
                for l in f:
                    if l.strip().startswith("#") or "UNGÜLTIG" in l.upper():
                        parts = l.strip().split("=", 1)
                        lbl = re.sub(r'^[\s#]*(UNGÜLTIG:\s*)?', '', parts[0], flags=re.IGNORECASE).strip() if len(parts) > 1 else "API_KEY"
                        k = clean_key(l)
                        if k:
                            existing_invalid.append((lbl, k))
                            
        with open(DESKTOP_TXT, "w") as f:
            for kid, v in keys.items():
                if isinstance(v, dict) and v.get("key"):
                    if v.get("valid"):
                        f.write(f"{v.get('label', 'API_KEY')}={v['key']}\n")
                    else:
                        f.write(f"# UNGÜLTIG: {v.get('label', 'API_KEY')}={v['key']}\n")
            for lbl, k in existing_invalid:
                # Avoid duplicates
                if k not in [v.get("key") for v in keys.values() if isinstance(v, dict)]:
                    f.write(f"# UNGÜLTIG: {lbl}={k}\n")
        os.chmod(DESKTOP_TXT, 0o600)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in write_keys_to_desktop: %s', e)
