import os
from fastapi import APIRouter, Depends, HTTPException, Request
from gnom_hub.core.security.hmac_signer import _get_or_create_secret
from gnom_hub.api.dependencies import get_admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin(request: Request):
    """Admin-Authentifizierung: Bearer-Token (bevorzugt) oder IP + X-Hub-Secret."""
    # 1. Bearer-Token aus Env-Variable (bevorzugt)
    admin_token = os.environ.get("GNOM_ADMIN_TOKEN")
    auth_header = request.headers.get("Authorization", "")
    if admin_token and auth_header.startswith("Bearer "):
        if auth_header[7:] == admin_token:
            return True

    # 2. Localhost-Zugriff erlauben
    if request.client and request.client.host in ("127.0.0.1", "::1", "localhost"):
        return True

    # 3. X-Hub-Secret als Fallback
    if request.headers.get("X-Hub-Secret") == _get_or_create_secret().hex():
        return True

    raise HTTPException(status_code=403, detail="Unauthorized: Admin-Zugriff verweigert.")


@router.post("/nuke")
async def nuke_database(request: Request, _=Depends(verify_admin), service=Depends(get_admin_service)):
    """Komplettes Zurücksetzen der Datenbank (gefährlich!)."""
    try:
        service.nuke()
        return {"status": "ok", "message": "Datenbank wurde komplett zurückgesetzt"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nuke fehlgeschlagen: {e}")


@router.post("/clean")
async def clean_workspace(request: Request, _=Depends(verify_admin), service=Depends(get_admin_service)):
    """Löscht temporäre Dateien und Logs (ohne Datenbank)."""
    try:
        service.clean()
        return {"status": "ok", "message": "Workspace temporäre Dateien wurden bereinigt"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clean fehlgeschlagen: {e}")
