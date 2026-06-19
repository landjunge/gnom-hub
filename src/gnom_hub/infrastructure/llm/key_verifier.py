"""Key-Verifier: testet API-Keys gegen Provider-Endpoints.

Nutzt die zentrale Provider-Registry in `providers.py` — neue Provider
dort hinzufügen, hier wird nichts geändert.
"""
import httpx, asyncio, re
from gnom_hub.infrastructure.llm.providers import (
    PROVIDERS, build_test_request,
    detect_provider_from_key, detect_provider_from_label,
)


def clean_key(k: str) -> str:
    k = k.strip()[7:].strip() if k.strip().startswith("export ") else k.strip()
    k = k.split("=", 1)[1] if "=" in k else (k.split(":", 1)[1] if ":" in k else k)
    for p in [r'^[-\*\+\u2022]\s*', r'\s*(#|//).*$', r'\s*\(.*?\)\s*$']:
        k = re.sub(p, '', k.strip("'\" "))
    return k.strip()


async def verify_key(pvd: str, key: str) -> dict:
    """Test key against provider's API endpoint. Returns {valid, info, caps}."""
    key = clean_key(key)
    if pvd not in PROVIDERS:
        return {"valid": False, "info": f"Unknown provider: {pvd}", "caps": []}
    req = build_test_request(pvd, key)
    if not req:
        return {"valid": False, "info": "Provider has no test endpoint", "caps": []}
    caps = PROVIDERS[pvd]["caps"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            method = req["method"].upper()
            if method == "GET":
                r = await cl.get(req["url"], headers=req["headers"])
            elif method == "POST":
                r = await cl.post(req["url"], headers=req["headers"])
            else:
                return {"valid": False, "info": f"Unsupported method: {method}", "caps": caps}
            return {
                "valid": r.status_code == 200,
                "info": "OK" if r.status_code == 200 else r.text[:200],
                "caps": caps,
            }
    except Exception as e:
        return {"valid": False, "info": str(e), "caps": caps}


async def auto_detect_and_verify(key: str, label: str = "") -> dict:
    """Try to identify provider from label OR key prefix, then verify."""
    key = clean_key(key)
    lbl = (label or "").upper()

    # 1. Try label-based detection (e.g. OPENAI_API_KEY, GEMINI_KEY)
    pvd = detect_provider_from_label(lbl)
    if pvd and pvd in PROVIDERS:
        return {**await verify_key(pvd, key), "provider": pvd}

    # 2. Try key-prefix detection (e.g. sk-or-v1-... = openrouter)
    pvd = detect_provider_from_key(key)
    if pvd and pvd in PROVIDERS:
        return {**await verify_key(pvd, key), "provider": pvd}

    # 3. Fallback for unknown keys starting with "sk-": try common LLM providers
    if key.startswith("sk-"):
        candidates = ["openai", "deepseek", "mistral", "groq", "kimi"]
        res = await asyncio.gather(
            *(verify_key(p, key) for p in candidates), return_exceptions=True
        )
        for p, r in zip(candidates, res):
            if isinstance(r, dict) and r.get("valid"):
                return {**r, "provider": p}

    # 4. Fallback for 32-char hex (likely ElevenLabs)
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        return {**await verify_key("elevenlabs", key), "provider": "elevenlabs"}

    return {"valid": False, "info": "Kein bekannter Provider erkannt", "caps": []}
