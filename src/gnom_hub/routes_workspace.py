from fastapi import APIRouter
import os
from .db import get_active_project

router = APIRouter()
BASE_WORKSPACE = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"

def get_workspace_dir():
    d = os.path.join(BASE_WORKSPACE, get_active_project())
    os.makedirs(d, exist_ok=True)
    return d

@router.get("/api/workspace")
def list_workspace():
    wd = get_workspace_dir()
    files = []
    for f in os.listdir(wd):
        p = os.path.join(wd, f)
        if os.path.isfile(p):
            files.append({"name": f, "size": os.path.getsize(p)})
    return files

@router.get("/api/workspace/{filename}")
def read_workspace_file(filename: str):
    wd = get_workspace_dir()
    p = os.path.join(wd, filename)
    if os.path.exists(p):
        with open(p, "r") as f:
            return {"content": f.read()}
    return {"error": "File not found"}
