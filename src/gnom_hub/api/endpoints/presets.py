"""FastAPI-Endpoints für das Gnom-Hub Preset-System.

Stellt CRUD + Activate-Operationen für Preset-Bundles unter
``/api/presets`` bereit.

Routen
------
- ``GET    /api/presets``                — Liste aller Presets (Summary)
- ``GET    /api/presets/{preset_id}``    — Volles Bundle
- ``PUT    /api/presets/{preset_id}``    — Speichern (mit Cross-File-Validierung)
- ``POST   /api/presets``                — Neues Preset anlegen
- ``DELETE /api/presets/{preset_id}``    — Preset löschen (nicht "default")
- ``GET    /api/presets/active``         — aktuell aktives Preset
- ``POST   /api/presets/activate/{id}``  — setzt ``state["active_preset"]``

Das aktive Preset wird in der ``state``-Tabelle unter dem Schlüssel
``active_preset`` persistiert (siehe ``gnom_hub.db.system_repo``).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path as PathParam
from pydantic import BaseModel, ValidationError

from gnom_hub.core.preset_loader import (
    delete_preset as _delete_preset,
    get_presets_root,
    list_presets as _list_presets,
    load_preset as _load_preset,
    save_preset as _save_preset,
    validate_preset_bundle,
)
from gnom_hub.core.preset_schema import PresetBundle

logger = logging.getLogger("gnom_hub.api.presets")

router = APIRouter(prefix="/api/presets", tags=["presets"])

# --------------------------------------------------------------------- #
# Hilfsfunktionen: aktives Preset                                      #
# --------------------------------------------------------------------- #

ACTIVE_PRESET_KEY = "active_preset"


def _get_active_preset_id() -> Optional[str]:
    """Liest die ID des aktuell aktiven Presets aus dem State-Store."""
    try:
        from gnom_hub.db.system_repo import get_state_value

        v = get_state_value(ACTIVE_PRESET_KEY, default=None)
        if isinstance(v, str) and v.strip():
            return v.strip()
    except Exception as e:
        logger.debug("get_active_preset_id: %s", e)
    return None


def _set_active_preset_id(preset_id: Optional[str]) -> None:
    """Setzt die ID des aktuell aktiven Presets im State-Store."""
    try:
        from gnom_hub.db.system_repo import set_state_value

        set_state_value(ACTIVE_PRESET_KEY, preset_id)
    except Exception as e:
        logger.warning("set_active_preset_id(%r): %s", preset_id, e)


# --------------------------------------------------------------------- #
# Pydantic-Modelle für API-I/O                                          #
# --------------------------------------------------------------------- #

class ActivePresetResponse(BaseModel):
    id: Optional[str]
    name: Optional[str] = None


class CreatePresetRequest(BaseModel):
    """Body für ``POST /api/presets``.

    Erlaubt das Anlegen eines neuen Presets mit ID + Bundle-Inhalt.
    """

    id: str
    bundle: PresetBundle


class SavePresetRequest(BaseModel):
    """Body für ``PUT /api/presets/{id}`` — nur das Bundle, kein ID-Feld."""

    bundle: PresetBundle


class CreatePresetResponse(BaseModel):
    id: str
    status: str = "ok"


# --------------------------------------------------------------------- #
# Endpoints                                                             #
# --------------------------------------------------------------------- #

@router.get("", response_model=list)
def list_presets_endpoint():
    """Liste aller Presets (id, name, description, version, updated_at)."""
    try:
        return [p.model_dump(mode="json") for p in _list_presets()]
    except Exception as e:
        logger.exception("list_presets failed")
        raise HTTPException(status_code=500, detail=f"list_presets failed: {e}")


@router.get("/active")
def get_active_preset_endpoint():
    """Liefert die ID und den Namen des aktuell aktiven Presets."""
    pid = _get_active_preset_id()
    if not pid:
        return ActivePresetResponse(id=None, name=None).model_dump()
    try:
        bundle = _load_preset(pid)
        return ActivePresetResponse(id=pid, name=bundle.config.name).model_dump()
    except FileNotFoundError:
        # aktives Preset wurde gelöscht → zurücksetzen
        _set_active_preset_id(None)
        return ActivePresetResponse(id=None, name=None).model_dump()
    except Exception as e:
        logger.warning("get_active_preset failed: %s", e)
        return ActivePresetResponse(id=pid, name=None).model_dump()


@router.post("/activate/{preset_id}")
def activate_preset_endpoint(preset_id: str = PathParam(..., min_length=1, max_length=120)):
    """Setzt ``state['active_preset']`` auf ``preset_id``."""
    try:
        # Validierung: Preset muss tatsächlich existieren + ladbar sein.
        _load_preset(preset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' nicht gefunden.")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Preset '{preset_id}' ist ungültig: {e}")
    _set_active_preset_id(preset_id)
    return {"status": "ok", "active_preset": preset_id}


@router.post("")
def create_preset_endpoint(req: CreatePresetRequest):
    """Legt ein neues Preset an."""
    pid = req.id.strip()
    if not pid:
        raise HTTPException(status_code=400, detail="id darf nicht leer sein.")
    pdir = get_presets_root() / pid
    if pdir.is_dir():
        raise HTTPException(
            status_code=409,
            detail=f"Preset '{pid}' existiert bereits.",
        )
    # Cross-File-Validierung
    errors = validate_preset_bundle(req.bundle)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"validation_errors": errors},
        )
    try:
        _save_preset(pid, req.bundle)
    except Exception as e:
        logger.exception("create_preset failed")
        raise HTTPException(status_code=500, detail=f"save_preset failed: {e}")
    return CreatePresetResponse(id=pid, status="ok").model_dump()


@router.get("/{preset_id}")
def get_preset_endpoint(preset_id: str = PathParam(..., min_length=1, max_length=120)):
    """Liefert das volle Preset-Bundle (alle 14 Sub-Modelle)."""
    try:
        bundle = _load_preset(preset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Preset ungültig: {e}")
    except Exception as e:
        logger.exception("get_preset failed")
        raise HTTPException(status_code=500, detail=f"load_preset failed: {e}")
    return bundle.model_dump(mode="json")


@router.put("/{preset_id}")
def put_preset_endpoint(
    req: SavePresetRequest,
    preset_id: str = PathParam(..., min_length=1, max_length=120),
):
    """Speichert das übergebene Bundle (mit Cross-File-Validierung)."""
    if preset_id == "default":
        # default darf nicht überschrieben werden, ohne dass der User das
        # explizit möchte — wir lehnen PUTs darauf grundsätzlich ab.
        raise HTTPException(
            status_code=403,
            detail=(
                "Das 'default'-Preset ist geschützt. "
                "Bitte klone es zuerst (POST /api/presets) und ändere die Kopie."
            ),
        )
    pdir = get_presets_root() / preset_id
    if not pdir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Preset '{preset_id}' existiert nicht. Verwende POST zum Anlegen.",
        )
    # Cross-File-Validierung
    errors = validate_preset_bundle(req.bundle)
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"validation_errors": errors},
        )
    try:
        _save_preset(preset_id, req.bundle)
    except Exception as e:
        logger.exception("put_preset failed")
        raise HTTPException(status_code=500, detail=f"save_preset failed: {e}")
    return {"status": "ok", "preset_id": preset_id}


@router.delete("/{preset_id}")
def delete_preset_endpoint(preset_id: str = PathParam(..., min_length=1, max_length=120)):
    """Löscht ein Preset (nicht ``default``)."""
    try:
        ok = _delete_preset(preset_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' nicht gefunden.")
    # Falls das aktive Preset gelöscht wurde → zurücksetzen.
    if _get_active_preset_id() == preset_id:
        _set_active_preset_id(None)
    return {"status": "ok", "deleted": preset_id}


__all__ = ["router"]
