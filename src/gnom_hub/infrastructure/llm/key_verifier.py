import httpx, asyncio, re
def clean_key(k: str) -> str:
    k = k.strip()[7:].strip() if k.strip().startswith("export ") else k.strip()
    k = k.split("=", 1)[1] if "=" in k else (k.split(":", 1)[1] if ":" in k else k)
    for p in [r'^[-\*\+\u2022]\s*', r'\s*(#|//).*$', r'\s*\(.*?\)\s*$']: k = re.sub(p, '', k.strip("'\" "))
    return k.strip()
async def verify_key(pvd: str, key: str) -> dict:
    key = clean_key(key)
    urls = {
        "deepseek": ("https://api.deepseek.com/user/balance", {"Authorization": f"Bearer {key}"}, ["text", "tools"]),
        "openrouter": ("https://openrouter.ai/api/v1/key", {"Authorization": f"Bearer {key}"}, ["text", "vision", "tools"]),
        "openai": ("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"}, ["text", "vision", "image", "audio", "tools"]),
        "anthropic": ("https://api.anthropic.com/v1/models", {"x-api-key": key, "anthropic-version": "2023-06-01"}, ["text", "vision", "tools"]),
        "gemini": (f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {}, ["text", "vision", "image", "audio", "tools"]),
        "mistral": ("https://api.mistral.ai/v1/models", {"Authorization": f"Bearer {key}"}, ["text", "vision", "tools"]),
        "elevenlabs": ("https://api.elevenlabs.io/v1/user", {"xi-api-key": key}, ["audio"]),
        "brave": ("https://api.search.brave.com/res/v1/web/search?q=ping", {"Accept": "application/json", "X-Subscription-Token": key}, ["web"]),
    }
    if pvd not in urls: return {"valid": False, "info": "Unknown provider", "caps": []}
    url, headers, caps = urls[pvd]
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            r = await cl.get(url, headers=headers)
            return {"valid": r.status_code == 200, "info": "OK" if r.status_code == 200 else r.text, "caps": caps}
    except Exception as e: return {"valid": False, "info": str(e), "caps": []}
async def auto_detect_and_verify(key: str, label: str = "") -> dict:
    key, lbl = clean_key(key), (label or "").upper()
    if "ELEVEN" in lbl: return {**await verify_key("elevenlabs", key), "provider": "elevenlabs"}
    if "BRAVE" in lbl: return {**await verify_key("brave", key), "provider": "brave"}
    for pfx, pvd in [("sk-or-", "openrouter"), ("sk-ant-", "anthropic"), ("AIzaSy", "gemini"), ("BS-", "brave")]:
        if key.startswith(pfx): return {**await verify_key(pvd, key), "provider": pvd}
    if key.startswith("sk-"):
        res = await asyncio.gather(*(verify_key(p, key) for p in ["deepseek", "openai", "mistral"]), return_exceptions=True)
        for p, r in zip(["deepseek", "openai", "mistral"], res):
            if isinstance(r, dict) and r.get("valid"): return {**r, "provider": p}
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        return {**await verify_key("elevenlabs", key), "provider": "elevenlabs"}
    return {"valid": False, "info": "Kein bekannter Provider erkannt", "caps": []}
