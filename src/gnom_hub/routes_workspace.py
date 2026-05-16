from fastapi import APIRouter
import os

router = APIRouter()
WORKSPACE_DIR = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)

@router.get("/api/workspace")
def list_workspace():
    files = []
    for f in os.listdir(WORKSPACE_DIR):
        p = os.path.join(WORKSPACE_DIR, f)
        if os.path.isfile(p):
            files.append({"name": f, "size": os.path.getsize(p)})
    return files

@router.get("/api/workspace/{filename}")
def read_workspace_file(filename: str):
    p = os.path.join(WORKSPACE_DIR, filename)
    if os.path.exists(p):
        with open(p, "r") as f:
            return {"content": f.read()}
    return {"error": "File not found"}
