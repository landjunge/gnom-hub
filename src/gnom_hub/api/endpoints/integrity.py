"""API-Endpunkte für @system save / @system unsave / Integritätsstatus."""
import logging
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()
log = logging.getLogger(__name__)

def _get_root() -> Path:
    from gnom_hub.core.config import WORKSPACE_DIR
    # Projekt-Root = zwei Ebenen über src/gnom_hub
    return Path(__file__).parent.parent.parent.parent.parent.resolve()


@router.post("/api/system/save")
def system_save():
    """@system save — Systemdateien mit ZWC-Signaturen schützen."""
    try:
        from gnom_hub.core.security.integrity import sign_system_files
        hashes = sign_system_files(_get_root())
        return {
            "status": "saved",
            "message": f"✅ {len(hashes)} Systemdateien signiert und geschützt.",
            "files": list(hashes.keys()),
        }
    except Exception as e:
        log.error("system/save Fehler: %s", e)
        return {"status": "error", "message": str(e)}


@router.post("/api/system/unsave")
def system_unsave():
    """@system unsave — Schutz deaktivieren (Systemdateien editierbar)."""
    try:
        from gnom_hub.core.security.integrity import disable_integrity
        disable_integrity()
        return {
            "status": "unsaved",
            "message": "⚠️ Integritätsschutz deaktiviert. Systemdateien können jetzt verändert werden.",
        }
    except Exception as e:
        log.error("system/unsave Fehler: %s", e)
        return {"status": "error", "message": str(e)}


@router.get("/api/system/integrity")
def system_integrity_status():
    """Gibt den aktuellen Integritätsstatus zurück."""
    try:
        from gnom_hub.core.security.integrity import (
            verify_system_files, is_integrity_enabled
        )
        enabled = is_integrity_enabled()
        if not enabled:
            return {"enabled": False, "status": "disabled", "tampered": []}
        tampered = verify_system_files(_get_root())
        return {
            "enabled": True,
            "status": "ok" if not tampered else "tampered",
            "tampered": tampered,
        }
    except Exception as e:
        return {"enabled": False, "status": "error", "message": str(e)}
