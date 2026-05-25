import httpx, asyncio, re

def clean_key(key: str) -> str:
    k = key.strip()
    if k.startswith("export "): k = k[7:].strip()
    if "=" in k: k = k.split("=", 1)[1]
    elif ":" in k: k = k.split(":", 1)[1]
    k = k.strip("'\" ")
    for p in [r'^[-\*\+\u2022]\s*', r'\s*(#|//).*$', r'\s*\(.*?\)\s*$']:
        k = re.sub(p, '', k)
    return k.strip()

async def verify_key(provider: str, key: str) -> dict:
    key = clean_key(key)
    urls = {
        "deepseek": ("https://api.deepseek.com/user/balance", {"Authorization": f"Bearer {key}"}, ["text", "tools"]),
        "openrouter": ("https://openrouter.ai/api/v1/auth/key", {"Authorization": f"Bearer {key}"}, ["text", "vision", "tools"]),
        "openai": ("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"}, ["text", "vision", "image", "audio", "tools"]),
        "anthropic": ("https://api.anthropic.com/v1/models", {"x-api-key": key, "anthropic-version": "2023-06-01"}, ["text", "vision", "tools"]),
        "gemini": (f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", {}, ["text", "vision", "image", "audio", "tools"]),
        "mistral": ("https://api.mistral.ai/v1/models", {"Authorization": f"Bearer {key}"}, ["text", "vision", "tools"]),
    }
    if provider not in urls: return {"valid": False, "info": "Unknown provider", "caps": []}
    url, headers, caps = urls[provider]
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            r = await cl.get(url, headers=headers)
            return {"valid": r.status_code == 200, "info": "OK" if r.status_code == 200 else r.text, "caps": caps}
    except Exception as e: return {"valid": False, "info": str(e), "caps": []}

async def auto_detect_and_verify(key: str) -> dict:
    key = clean_key(key)
    for pfx, pvd in [("sk-or-", "openrouter"), ("sk-ant-", "anthropic"), ("AIzaSy", "gemini")]:
        if key.startswith(pfx): return {**await verify_key(pvd, key), "provider": pvd}
    if key.startswith("sk-"):
        res = await asyncio.gather(*(verify_key(p, key) for p in ["deepseek", "openai", "mistral"]), return_exceptions=True)
        for p, r in zip(["deepseek", "openai", "mistral"], res):
            if isinstance(r, dict) and r.get("valid"): return {**r, "provider": p}
    return {"valid": False, "info": "Kein bekannter Provider erkannt", "caps": []}
