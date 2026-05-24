from fastapi import APIRouter; from fastapi.responses import HTMLResponse; import os, subprocess; from .db import get_active_project; from .config import WORKSPACE_DIR
router = APIRouter()
def get_workspace_dir(): d = os.path.join(str(WORKSPACE_DIR), get_active_project()); os.makedirs(d, exist_ok=True); return d
@router.get("/api/workspace")
def list_workspace():
    w = get_workspace_dir()
    return [{"name": f, "size": os.path.getsize(os.path.join(w, f)), "mtime": os.path.getmtime(os.path.join(w, f))} for f in os.listdir(w) if os.path.isfile(os.path.join(w, f))]
@router.get("/api/workspace/{filename}")
def read_workspace_file(filename: str):
    p = os.path.join(get_workspace_dir(), filename)
    return {"content": open(p, "r").read()} if os.path.exists(p) else {"error": "File not found"}
@router.get("/api/workspace/{filename}/serve", response_class=HTMLResponse)
def serve_workspace_file(filename: str):
    p = os.path.join(get_workspace_dir(), filename)
    return HTMLResponse(open(p, "r").read()) if os.path.exists(p) else HTMLResponse("<h1>Datei nicht gefunden</h1>", status_code=404)
@router.post("/api/workspace/{filename}/run")
def run_workspace_file(filename: str):
    w, p = get_workspace_dir(), os.path.join(get_workspace_dir(), filename)
    if not os.path.exists(p): return {"error": "File not found"}
    if not filename.endswith(".py"): return {"error": "Nur .py Dateien können ausgeführt werden."}
    try:
        from .sandbox_exec import run_sandboxed
        r = run_sandboxed(["python3", p], cwd=w, timeout=15)
        return {"stdout": r.stdout[-2000:], "stderr": r.stderr[-1000:], "code": r.returncode}
    except subprocess.TimeoutExpired: return {"error": "Timeout nach 15 Sekunden"}
@router.get("/api/project")
def get_project(): return {"project": get_active_project()}
