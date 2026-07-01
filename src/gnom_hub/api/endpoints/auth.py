# auth.py — Auth-Decorators für sensitive API-Endpoints
# Sichert Endpoints ab die P0-Risiko haben:
# - /api/soul/save und /api/soul/delete (memory_crud)
# - /api/llm/keys POST (llm_keys)
#
# Strategie: gleiche Logik wie verify_admin() in admin.py:
# 1. Bearer-Token (wenn GNOM_HUB_API_TOKEN gesetzt) ODER
# 2. Localhost-Zugriff (127.0.0.1, ::1, localhost) ODER
# 3. X-Hub-Secret Header (HMAC des Hub-Secrets)
#
# Wichtig: KEIN offener Endpunkt ohne Auth. Wenn keiner der 3 Wege
# matcht → 403 Forbidden.

import os

from fastapi import Header, HTTPException, Request


def verify_admin(request: Request, authorization: str = Header(None),
                 x_hub_secret: str = Header(None)):
    """
    Sensitive-API-Authentifizierung. Erlaubt:
    1. Bearer-Token via Authorization-Header (wenn GNOM_HUB_API_TOKEN gesetzt)
    2. Localhost-Zugriff (Client-IP 127.0.0.1, ::1 oder localhost)
    3. X-Hub-Secret Header (HMAC-Wert, kompatibel mit admin.py)

    Sonst: 403 Forbidden.
    """
    # 1. Bearer-Token
    api_token = os.environ.get("GNOM_HUB_API_TOKEN")
    if api_token and authorization and authorization.startswith("Bearer "):
        if authorization[7:] == api_token:
            return True

    # 2. Localhost
    if request.client and request.client.host in ("127.0.0.1", "::1", "localhost"):
        return True

    # 3. X-Hub-Secret (kompatibel mit admin.verify_admin)
    if x_hub_secret:
        try:
            from gnom_hub.core.security.hmac_signer import _get_or_create_secret
            if x_hub_secret == _get_or_create_secret().hex():
                return True
        except Exception:
            pass

    raise HTTPException(
        status_code=403,
        detail="Unauthorized: sensitive Endpoint erfordert Authentifizierung "
               "(Bearer-Token, Localhost oder X-Hub-Secret).",
    )
