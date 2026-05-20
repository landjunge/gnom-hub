from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()
THEMES_PATH = "/Users/landjunge/Documents/AG-Flega/frontend/themes.js"

class ThemesData(BaseModel):
    content: str

@router.get("/api/showbox/themes")
def get_themes():
    if os.path.exists(THEMES_PATH):
        return {"content": open(THEMES_PATH, "r").read()}
    return {"content": ""}

@router.post("/api/showbox/themes")
def save_themes(data: ThemesData):
    with open(THEMES_PATH, "w") as f:
        f.write(data.content)
    return {"status": "ok"}
