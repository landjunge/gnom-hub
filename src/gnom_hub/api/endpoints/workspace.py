from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
import os, subprocess
from gnom_hub.core.config import WORKSPACE_DIR
from gnom_hub.db.state_repo import SQLiteStateRepository

router = APIRouter()
def get_workspace_dir():
    proj = SQLiteStateRepository().get_active_project()
    d = os.path.join(str(WORKSPACE_DIR), proj)
    os.makedirs(d, exist_ok=True); return d

def _safe_path(filename: str):
    """Validate that filename doesn't escape the workspace directory."""
    from pathlib import Path
    workspace = Path(get_workspace_dir()).resolve()
    target = (workspace / filename).resolve()
    if not str(target).startswith(str(workspace)):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Zugriff verweigert: Pfad außerhalb des Workspace")
    return str(target)

@router.get("/api/workspace")
def list_workspace():
    w = get_workspace_dir()
    return [{"name": f, "size": os.path.getsize(os.path.join(w, f)), "mtime": os.path.getmtime(os.path.join(w, f))} for f in os.listdir(w) if os.path.isfile(os.path.join(w, f))]

@router.get("/api/workspace/{filename}")
def read_workspace_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"error": "File not found"}

@router.get("/api/workspace/{filename}/serve", response_class=HTMLResponse)
def serve_workspace_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Datei nicht gefunden</h1>", status_code=404)

@router.get("/api/workspace/{filename}/raw")
def serve_raw_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        return FileResponse(p)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Datei nicht gefunden")

@router.post("/api/workspace/{filename}/run")
def run_workspace_file(filename: str):
    p = _safe_path(filename)
    w = get_workspace_dir()
    if not os.path.exists(p): return {"error": "File not found"}
    if not filename.endswith(".py"): return {"error": "Nur .py Dateien können ausgeführt werden."}
    try:
        from gnom_hub.infrastructure.process.sandbox_exec import run_sandboxed
        r = run_sandboxed(["python3", p], cwd=w, timeout=15)
        return {"stdout": r.stdout[-2000:], "stderr": r.stderr[-1000:], "code": r.returncode}
    except subprocess.TimeoutExpired: return {"error": "Timeout nach 15 Sekunden"}

@router.get("/api/project")
def get_project(): return {"project": SQLiteStateRepository().get_active_project()}
