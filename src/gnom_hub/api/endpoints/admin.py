import hmac
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from gnom_hub.core.security.hmac_signer import _get_or_create_secret
from gnom_hub.api.dependencies import get_admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin(request: Request):
    """Admin-Authentifizierung: Bearer-Token (bevorzugt) oder IP + X-Hub-Secret.

    Alle Secret-Vergleiche gehen über `hmac.compare_digest`, um Timing-Attacks
    auf den String-Vergleich auszuschließen.
    """
    # 1. Bearer-Token aus Env-Variable (bevorzugt)
    admin_token = os.environ.get("GNOM_ADMIN_TOKEN")
    auth_header = request.headers.get("Authorization", "")
    if admin_token and auth_header.startswith("Bearer "):
        presented = auth_header[7:]
        if hmac.compare_digest(presented.encode("utf-8"), admin_token.encode("utf-8")):
            return True

    # 2. Localhost-Zugriff erlauben
    if request.client and request.client.host in ("127.0.0.1", "::1", "localhost"):
        return True

    # 3. X-Hub-Secret als Fallback
    expected = _get_or_create_secret().hex()
    presented = request.headers.get("X-Hub-Secret", "")
    if hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8")):
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


@router.get("/dead-letter")
def list_dead_letters(request: Request, _=Depends(verify_admin)):
    """Zeigt alle fehlgeschlagenen Nachrichten (max. 100)."""
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as db:
        rows = db.execute("""
            SELECT id, sender, recipient, payload, retry_count, created_at
            FROM agent_messages
            WHERE status = 'dead_letter'
            ORDER BY created_at DESC
            LIMIT 100
        """).fetchall()
        return [dict(r) for r in rows]


@router.post("/dead-letter/{msg_id}/retry")
def retry_dead_letter(msg_id: int, request: Request, _=Depends(verify_admin)):
    """Setzt eine DLQ-Nachricht zurück auf 'pending' für manuellen Retry."""
    from gnom_hub.db.connection import get_db_conn
    from gnom_hub.agents.swarm.swarm_comms import notify_agent

    with get_db_conn() as db:
        affected = db.execute("""
            UPDATE agent_messages
            SET status='pending', retry_count=0, deliver_after=0
            WHERE id=? AND status='dead_letter'
        """, (msg_id,)).rowcount
        db.commit()

        if affected == 0:
            raise HTTPException(status_code=404, detail="Nachricht nicht gefunden oder nicht in DLQ")

        row = db.execute(
            "SELECT recipient FROM agent_messages WHERE id=?", (msg_id,)
        ).fetchone()
        if row:
            notify_agent(row["recipient"])

    return {"status": "requeued", "msg_id": msg_id}


@router.delete("/dead-letter/{msg_id}")
def discard_dead_letter(msg_id: int, request: Request, _=Depends(verify_admin)):
    """Löscht eine DLQ-Nachricht endgültig."""
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as db:
        affected = db.execute(
            "DELETE FROM agent_messages WHERE id=? AND status='dead_letter'",
            (msg_id,)
        ).rowcount
        db.commit()

        if affected == 0:
            raise HTTPException(status_code=404, detail="Nachricht nicht gefunden oder nicht in DLQ")

    return {"status": "deleted", "msg_id": msg_id}


@router.delete("/dead-letter")
def purge_dead_letters(request: Request, _=Depends(verify_admin)):
    """Löscht ALLE DLQ-Nachrichten. Vorsicht: irreversibel."""
    from gnom_hub.db.connection import get_db_conn
    with get_db_conn() as db:
        count = db.execute(
            "DELETE FROM agent_messages WHERE status='dead_letter'"
        ).rowcount
        db.commit()
    return {"status": "purged", "deleted_count": count}
