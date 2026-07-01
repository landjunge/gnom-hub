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

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam
from pydantic import BaseModel, ValidationError

from gnom_hub.core.preset_loader import (
    delete_preset as _delete_preset,
)
from gnom_hub.core.preset_loader import (
    get_presets_root,
    validate_preset_bundle,
)
from gnom_hub.core.preset_loader import (
    list_presets as _list_presets,
)
from gnom_hub.core.preset_loader import (
    load_preset as _load_preset,
)
from gnom_hub.core.preset_loader import (
    save_preset as _save_preset,
)
from gnom_hub.core.preset_schema import PresetBundle

logger = logging.getLogger("gnom_hub.api.presets")

router = APIRouter(prefix="/api/presets", tags=["presets"])

# --------------------------------------------------------------------- #
# Hilfsfunktionen: aktives Preset                                      #
# --------------------------------------------------------------------- #

ACTIVE_PRESET_KEY = "active_preset"


def _get_active_preset_id() -> str | None:
    """Liest die ID des aktuell aktiven Presets aus dem State-Store."""
    try:
        from gnom_hub.db.system_repo import get_state_value

        v = get_state_value(ACTIVE_PRESET_KEY, default=None)
        if isinstance(v, str) and v.strip():
            return v.strip()
    except Exception as e:
        logger.debug("get_active_preset_id: %s", e)
    return None


def _set_active_preset_id(preset_id: str | None) -> None:
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
    id: str | None
    name: str | None = None


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
        raise HTTPException(status_code=500, detail=f"list_presets failed: {e}") from e


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
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' nicht gefunden.") from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Preset '{preset_id}' ist ungültig: {e}") from e
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
        raise HTTPException(status_code=500, detail=f"save_preset failed: {e}") from e
    return CreatePresetResponse(id=pid, status="ok").model_dump()


@router.get("/{preset_id}")
def get_preset_endpoint(preset_id: str = PathParam(..., min_length=1, max_length=120)):
    """Liefert das volle Preset-Bundle (alle 14 Sub-Modelle)."""
    try:
        bundle = _load_preset(preset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Preset ungültig: {e}") from e
    except Exception as e:
        logger.exception("get_preset failed")
        raise HTTPException(status_code=500, detail=f"load_preset failed: {e}") from e
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
        raise HTTPException(status_code=500, detail=f"save_preset failed: {e}") from e
    return {"status": "ok", "preset_id": preset_id}


@router.delete("/{preset_id}")
def delete_preset_endpoint(preset_id: str = PathParam(..., min_length=1, max_length=120)):
    """Löscht ein Preset (nicht ``default``)."""
    try:
        ok = _delete_preset(preset_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    if not ok:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' nicht gefunden.")
    # Falls das aktive Preset gelöscht wurde → zurücksetzen.
    if _get_active_preset_id() == preset_id:
        _set_active_preset_id(None)
    return {"status": "ok", "deleted": preset_id}


# ───────────────────────────────────────────────────────────────────── #
# Per-Agent CRUD (Layer A: presets.json mit agent_groups + presets.<slug>
# .agents.<name>) — verwendet gnom_hub.core.utils.preset_service
# ───────────────────────────────────────────────────────────────────── #

@router.get("/groups")
def get_agent_groups_endpoint():
    """Liefert die System + Worker Agent-Gruppen aus presets.json."""
    try:
        from gnom_hub.core.utils.preset_service import get_agent_groups
        return get_agent_groups()
    except Exception as e:
        logger.warning("get_agent_groups_endpoint failed: %s", e)
        return {"system": ["soulag", "watchdogag", "generalag", "securityag"],
                "worker": ["coderag", "researcherag", "writerag", "editorag"]}


@router.get("/layer-a/list")
def list_layer_a_presets_endpoint():
    """Listet Presets aus Layer A (presets.json) — Summary."""
    try:
        from gnom_hub.core.utils.preset_service import list_presets
        return list_presets()
    except Exception as e:
        logger.warning("list_layer_a_presets_endpoint failed: %s", e)
        return []


@router.get("/layer-a/{slug}")
def get_layer_a_preset_endpoint(slug: str = PathParam(..., min_length=1, max_length=120)):
    """Volles Preset aus Layer A."""
    try:
        from gnom_hub.core.utils.preset_service import get_preset
        p = get_preset(slug)
        if not p:
            raise HTTPException(status_code=404, detail=f"Preset '{slug}' nicht gefunden.")
        return p
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("get_layer_a_preset_endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/layer-a/{slug}/agents/{agent_name}")
def update_layer_a_preset_agent_endpoint(
    slug: str = PathParam(..., min_length=1, max_length=120),
    agent_name: str = PathParam(..., min_length=1, max_length=64),
    body: dict = None,
):
    """Updated ein einzelnes Agent-Feld in einem Layer-A-Preset."""
    try:
        from gnom_hub.core.utils.preset_service import update_preset_agent
        if not body or not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Body muss ein Dict mit Agent-Feldern sein")
        ok = update_preset_agent(slug, agent_name, body)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Preset '{slug}' oder Agent '{agent_name}' nicht gefunden.")
        return {"status": "ok", "slug": slug, "agent": agent_name, "updated": list(body.keys())}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("update_layer_a_preset_agent_endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/layer-a")
def create_layer_a_preset_endpoint(body: dict = None):
    """Legt ein neues Preset in Layer A an."""
    try:
        from gnom_hub.core.utils.preset_service import create_preset
        if not body or "name" not in body:
            raise HTTPException(status_code=400, detail="Body braucht 'name'")
        slug = create_preset(name=body["name"], description=body.get("description", ""))
        return {"status": "ok", "slug": slug}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("create_layer_a_preset_endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/layer-a/{slug}/clone")
def clone_layer_a_preset_endpoint(
    slug: str = PathParam(..., min_length=1, max_length=120),
    body: dict = None,
):
    """Klont ein Layer-A-Preset."""
    try:
        from gnom_hub.core.utils.preset_service import clone_preset
        if not body or "name" not in body:
            raise HTTPException(status_code=400, detail="Body braucht 'name'")
        new_slug = clone_preset(slug, body["name"])
        if not new_slug:
            raise HTTPException(status_code=404, detail=f"Preset '{slug}' nicht gefunden.")
        return {"status": "ok", "slug": new_slug}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("clone_layer_a_preset_endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/layer-a/{slug}")
def delete_layer_a_preset_endpoint(slug: str = PathParam(..., min_length=1, max_length=120)):
    """Löscht ein Layer-A-Preset (nicht 'default')."""
    try:
        from gnom_hub.core.utils.preset_service import delete_preset
        ok = delete_preset(slug)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Preset '{slug}' nicht löschbar (existiert nicht oder ist 'default').")
        return {"status": "ok", "deleted": slug}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("delete_layer_a_preset_endpoint failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = ["router"]
