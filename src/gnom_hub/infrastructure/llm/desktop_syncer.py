import asyncio
import logging
import os
import re
import time
from pathlib import Path

import gnom_hub.db.state_repo as sr
from gnom_hub.infrastructure.llm.key_verifier import auto_detect_and_verify, clean_key

DESKTOP_TXT = Path.home() / "Desktop" / "api_keys.txt"

# Re-Verify Throttle: damit der Periodische Background-Task nicht zu oft
# gegen Provider-Endpoint hämmert. Per-Key Tracking via mtime auf der TXT.
_LAST_REVERIFY_MONOTONIC: float = 0.0
_REVERIFY_INTERVAL_SECONDS = 30 * 60  # 30 Minuten


async def reverify_invalid_keys(desktop_path: Path = None, force: bool = False) -> dict:
    """Re-verifiziert alle `# UNGÜLTIG:`-Keys in api_keys.txt.

    Hintergrund: `sync_desktop_keys()` liest nur aktive Zeilen. Sobald ein Key
    dort gelandet ist, wird er nie wieder angefasst — auch wenn der Provider
    ihn inzwischen wieder akzeptiert (z.B. nach abgelaufenem Billing-Limit,
    revoke→re-grant, etc.). Diese Funktion holt solche Keys zurück.

    Args:
        desktop_path: Override für DESKTOP_TXT (für Tests).
        force: True um den Throttle zu umgehen (vom manuellen Endpoint genutzt).

    Returns:
        {
          "checked": int,        # Anzahl UNGÜLTIG-Keys die wir geprüft haben
          "recovered": [str],    # Labels der Keys, die jetzt wieder valid sind
          "still_invalid": [str], # Labels der Keys die weiterhin failen
          "skipped": bool,       # True wenn Throttle aktiv war
        }
    """
    global _LAST_REVERIFY_MONOTONIC
    path = Path(desktop_path) if desktop_path else DESKTOP_TXT
    now = time.monotonic()
    skipped_throttle = False
    if not force and (now - _LAST_REVERIFY_MONOTONIC < _REVERIFY_INTERVAL_SECONDS):
        skipped_throttle = True

    if not path.exists():
        return {"checked": 0, "recovered": [], "still_invalid": [], "skipped": False}

    try:
        with open(path) as f:
            raw_lines = f.read().splitlines()
    except Exception as e:
        logging.getLogger(__name__).error('reverify_invalid_keys: read failed: %s', e)
        return {"checked": 0, "recovered": [], "still_invalid": [], "skipped": False}

    # Parse: sammle UNGÜLTIG-Zeilen mit (Label, Key, line_idx)
    invalid_entries: list[tuple[str, str, int]] = []
    for idx, line in enumerate(raw_lines):
        s = line.strip()
        if not s.startswith("# UNGÜLTIG:"):
            continue
        # match "# UNGÜLTIG: Foo=sk-…"
        m = re.match(r'^#\s*UNGÜLTIG:\s*(.+?)=(.+)$', s)
        if m:
            invalid_entries.append((m.group(1).strip(), clean_key(m.group(2)), idx))

    if not invalid_entries:
        _LAST_REVERIFY_MONOTONIC = now
        return {"checked": 0, "recovered": [], "still_invalid": [], "skipped": skipped_throttle}

    # Verifiziere parallel (wie auto_detect_and_verify selbst)
    to_check = [(lbl, k) for lbl, k, _ in invalid_entries]
    results = await asyncio.gather(
        *(auto_detect_and_verify(k, lbl) for lbl, k in to_check),
        return_exceptions=True,
    )

    recovered_labels: list[str] = []
    still_invalid_labels: list[str] = []
    for (lbl, k, idx), res in zip(invalid_entries, results, strict=False):
        if isinstance(res, dict) and res.get("valid"):
            # Reaktivieren: aus der UNGÜLTIG-Zeile eine aktive Zeile machen
            raw_lines[idx] = f"{lbl}={k}"
            recovered_labels.append(lbl)
        else:
            still_invalid_labels.append(lbl)

    if recovered_labels:
        try:
            with open(path, "w") as f:
                f.write("\n".join(raw_lines) + "\n")
            os.chmod(path, 0o600)
            logging.getLogger(__name__).info(
                'reverify_invalid_keys: recovered %d key(s): %s',
                len(recovered_labels), ", ".join(recovered_labels),
            )
            # Sync triggern damit DB die reaktivierten Keys gleich aufnimmt
            try:
                current_db = sr.SQLiteStateRepository().get_value("llm_keys", {}) or {}
                await sync_desktop_keys(current_db if isinstance(current_db, dict) else {})
            except Exception as e:
                logging.getLogger(__name__).error('reverify: post-sync failed: %s', e)
        except Exception as e:
            logging.getLogger(__name__).error('reverify: write failed: %s', e)

    _LAST_REVERIFY_MONOTONIC = now
    return {
        "checked": len(invalid_entries),
        "recovered": recovered_labels,
        "still_invalid": still_invalid_labels,
        "skipped": skipped_throttle,
    }


async def sync_desktop_keys(db_keys: dict) -> dict:
    if not DESKTOP_TXT.exists():
        # Keep only valid keys if file doesn't exist
        db_keys = {kid: v for kid, v in db_keys.items() if isinstance(v, dict) and v.get("valid")}
        return db_keys
    try:
        with open(DESKTOP_TXT) as f:
            lines = [letter.strip() for letter in f if letter.strip()]
        if not lines:
            # Clear keys if file is empty
            sr.SQLiteStateRepository().set_value("llm_keys", {})
            return {}
            
        parsed_active = []
        parsed_invalid = []
        for letter in lines:
            is_comment = letter.startswith("#") or "UNGÜLTIG" in letter.upper()
            parts = letter.split("=", 1)
            lbl = re.sub(r'^[\s#]*(UNGÜLTIG:\s*)?', '', parts[0], flags=re.IGNORECASE).strip() if len(parts) > 1 else "API_KEY"
            key = clean_key(letter)
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
            for idx, ((lbl, clean_k), res) in enumerate(zip(to_verify, res_list, strict=False)):
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
        for _kid, v in db_keys.items():
            new_lines.append(f"{v.get('label', 'API_KEY')}={v['key']}\n")
        for lbl, k in parsed_invalid:
            new_lines.append(f"# UNGÜLTIG: {lbl}={k}\n")
            
        target = "".join(new_lines)
        with open(DESKTOP_TXT) as f:
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
            with open(DESKTOP_TXT) as f:
                for letter in f:
                    if letter.strip().startswith("#") or "UNGÜLTIG" in letter.upper():
                        parts = letter.strip().split("=", 1)
                        lbl = re.sub(r'^[\s#]*(UNGÜLTIG:\s*)?', '', parts[0], flags=re.IGNORECASE).strip() if len(parts) > 1 else "API_KEY"
                        k = clean_key(letter)
                        if k:
                            existing_invalid.append((lbl, k))
                            
        with open(DESKTOP_TXT, "w") as f:
            for _kid, v in keys.items():
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
