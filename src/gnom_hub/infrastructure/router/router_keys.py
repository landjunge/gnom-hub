import os
from .router_config import DS_KEY, OR_KEY

def get_keys(pvd, kdb):
    lst = list(kdb.values()) if isinstance(kdb, dict) else (kdb or [])
    # Sortiere Keys, sodass verifizierte (valid=True) zuerst probiert werden
    lst = sorted(lst, key=lambda x: 1 if x.get("valid") else 0, reverse=True)
    ks = [k.get("key") for k in lst if k.get("provider") == pvd]
    if pvd == "deepseek" and DS_KEY: ks.append(DS_KEY)
    elif pvd == "openrouter":
        ks.extend([os.environ.get(f"OPENROUTER_KEY_FREE_{i}") for i in range(1, 6) if os.environ.get(f"OPENROUTER_KEY_FREE_{i}")])
        if OR_KEY: ks.append(OR_KEY)
    return list(dict.fromkeys(ks))
