# gnom_hub/api/endpoints/showbox_presets.py
# HTTP-Endpoint für Showbox-Button-Presets.
# Frontend (showbox-buttons.js) ruft dies beim Showbox-Open ab.
from fastapi import APIRouter
from gnom_hub.showbox.button_presets import (
    categories,
    get_preset,
    all_buttons,
    get_buttons_for_context,
    to_frontend_buttons,
)

router = APIRouter(prefix="/api/showbox", tags=["showbox"])


@router.get("/button-presets")
def list_presets():
    """Alle verfügbaren Preset-Kategorien."""
    return {"categories": categories()}


@router.get("/button-presets/all")
def get_all():
    """Alle Presets als Dict (alle Buttons aller Kategorien)."""
    return all_buttons()


@router.get("/button-presets/{name}")
def get_one(name: str):
    """Ein einzelnes Preset (z.B. 'nav', 'actions')."""
    return get_preset(name)


@router.get("/button-presets/{name}/frontend")
def get_frontend(name: str):
    """Preset im Frontend-Format (für direkten use in showbox-buttons.js)."""
    preset = get_preset(name)
    return {
        "category": name,
        "buttons": to_frontend_buttons(preset.get("buttons", [])),
    }


@router.get("/context-buttons")
def context_buttons(context: str = "default"):
    """Kontextuell ausgewählte Buttons für die aktuelle Showbox.

    context:
      - default:  2x nav + 2x actions + 2x agents + 2x workflow
      - minimal:  nur nav
      - tribunal: mehr actions
      - show:     mehr workflow
    """
    return {
        "context": context,
        "buttons": to_frontend_buttons(get_buttons_for_context(context)),
    }
