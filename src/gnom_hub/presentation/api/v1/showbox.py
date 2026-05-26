import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gnom_hub.core.config import FRONTEND_DIR
from gnom_hub.db import (
    get_showbox_presentations,
    save_showbox_presentation,
    delete_showbox_presentation,
    get_active_showbox,
    set_active_showbox
)

router = APIRouter()
THEMES_PATH = FRONTEND_DIR / "themes.js"

class ThemesData(BaseModel):
    content: str

class PresentationData(BaseModel):
    name: str
    slides: list
    sender: str = None

class ActiveData(BaseModel):
    name: str

@router.get("/api/showbox/themes")
def get_themes():
    try:
        presentations = get_showbox_presentations()
        def get_order_key(p):
            name = p["name"]
            if name.startswith("Showbox ") and name[8:].isdigit():
                return (0, int(name[8:]))
            return (1, name)
        presentations.sort(key=get_order_key)
        slides_list = [p["slides"] for p in presentations]
        js_content = f"window.showboxes = {json.dumps(slides_list, indent=2)};"
        return {"content": js_content}
    except Exception as e:
        return {"content": f"// Error: {e}"}

@router.post("/api/showbox/themes")
def save_themes(data: ThemesData):
    try:
        if THEMES_PATH.parent.exists():
            THEMES_PATH.write_text(data.content, encoding="utf-8")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/showbox/presentations")
def get_presentations():
    return get_showbox_presentations()

@router.post("/api/showbox/presentations")
def save_presentation(data: PresentationData):
    res = save_showbox_presentation(data.name, data.slides, data.sender)
    if res:
        set_active_showbox(data.name)
        return {"status": "ok", "presentation": res}
    raise HTTPException(status_code=500, detail="Failed to save presentation")

@router.delete("/api/showbox/presentations/{name}")
def delete_presentation(name: str):
    success = delete_showbox_presentation(name)
    if success:
        # If deleted active, reset active state
        if get_active_showbox() == name:
            set_active_showbox("")
        return {"status": "ok"}
    raise HTTPException(status_code=500, detail="Failed to delete presentation")

@router.get("/api/showbox/active")
def get_active():
    return {"active": get_active_showbox()}

@router.post("/api/showbox/active")
def set_active(data: ActiveData):
    set_active_showbox(data.name)
    return {"status": "ok"}
