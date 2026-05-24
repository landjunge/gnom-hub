from fastapi import APIRouter
from pydantic import BaseModel
from .config import FRONTEND_DIR

router = APIRouter()
THEMES_PATH = FRONTEND_DIR / "themes.js"

class ThemesData(BaseModel):
    content: str

@router.get("/api/showbox/themes")
def get_themes():
    if THEMES_PATH.exists():
        return {"content": THEMES_PATH.read_text(encoding="utf-8")}
    return {"content": ""}

@router.post("/api/showbox/themes")
def save_themes(data: ThemesData):
    THEMES_PATH.write_text(data.content, encoding="utf-8")
    return {"status": "ok"}

