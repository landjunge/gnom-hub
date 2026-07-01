import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from gnom_hub.core.config import Config
from gnom_hub.db import set_state_value
from gnom_hub.db.state_repo import SQLiteStateRepository

router = APIRouter()


def get_workspace_dir():
    """Workspace-Pfad des aktiven Projekts.

    Liest den Root via Config.workspace_dir() (Hot-reload-fähig) und joint
    mit dem aktiven Projektnamen aus dem State-Store.
    """
    proj = SQLiteStateRepository().get_active_project()
    d = os.path.join(str(Config.workspace_dir()), proj)
    os.makedirs(d, exist_ok=True)
    return d


def _safe_path(filename: str):
    """Validate that filename doesn't escape the workspace directory."""
    workspace = Path(get_workspace_dir()).resolve()
    target = (workspace / filename).resolve()
    if not str(target).startswith(str(workspace)):
        raise HTTPException(status_code=403, detail="Zugriff verweigert: Pfad außerhalb des Workspace")
    return str(target)


@router.get("/api/workspace")
def list_workspace():
    w = get_workspace_dir()
    return [{"name": f, "size": os.path.getsize(os.path.join(w, f)), "mtime": os.path.getmtime(os.path.join(w, f))} for f in os.listdir(w) if os.path.isfile(os.path.join(w, f))]


# ── Workspace-Pfad Konfiguration (Hot-reload-fähig) ──────────────────────

@router.get("/api/workspace/config")
def get_workspace_config():
    """Aktuellen Workspace-Pfad + Default-Hinweis zurückgeben."""
    return {
        "path": str(Config.workspace_dir()),
        "default": str(Path.home() / "gnom-Workspace"),
        "is_default": str(Config.workspace_dir()) == str(Path.home() / "gnom-Workspace"),
    }


@router.put("/api/workspace/config")
def set_workspace_config(payload: dict):
    """Workspace-Pfad setzen.

    Speichert den Pfad in `state["workspace_dir_override"]`. Alle Aufrufer,
    die `Config.workspace_dir()` benutzen, sehen den neuen Pfad sofort.
    Validierung:
      - absoluter Pfad
      - liegt nicht in einem System-Verzeichnis (/etc, /usr, /var, /proc,
        /sys, /boot, /lib, /sbin, /bin, /private/etc)
      - existiert (oder wird angelegt)
      - ist beschreibbar
    """
    new_path = (payload.get("path") or "").strip()
    if not new_path:
        raise HTTPException(status_code=400, detail="Pfad darf nicht leer sein")

    p = Path(new_path).expanduser()
    if not p.is_absolute():
        raise HTTPException(status_code=400, detail="Pfad muss absolut sein")

    resolved = p.resolve()
    # Schutz gegen System-Pfade. ~/... ist immer erlaubt.
    blocked_prefixes = (
        "/etc", "/usr", "/var", "/proc", "/sys", "/boot",
        "/lib", "/sbin", "/bin", "/private/etc", "/private/var",
    )
    for prefix in blocked_prefixes:
        if resolved == Path(prefix) or str(resolved).startswith(prefix + "/"):
            raise HTTPException(
                status_code=400,
                detail=f"Pfad innerhalb von {prefix} ist nicht erlaubt (System-Pfad).",
            )

    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"Verzeichnis nicht anlegbar: {e}") from e

    if not os.access(str(p), os.W_OK):
        raise HTTPException(status_code=400, detail=f"Verzeichnis nicht beschreibbar: {p}")

    set_state_value("workspace_dir_override", str(p))
    return {
        "path": str(Config.workspace_dir()),
        "default": str(Path.home() / "gnom-Workspace"),
        "is_default": str(Config.workspace_dir()) == str(Path.home() / "gnom-Workspace"),
        "ok": True,
    }


@router.post("/api/workspace/config/reset")
def reset_workspace_config():
    """Override zurücksetzen — Default-Workspace wird wieder verwendet."""
    set_state_value("workspace_dir_override", "")
    return {
        "path": str(Config.workspace_dir()),
        "default": str(Path.home() / "gnom-Workspace"),
        "is_default": True,
        "ok": True,
    }


# ── File-Operationen ──────────────────────────────────────────────────────

@router.get("/api/workspace/{filename}")
def read_workspace_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return {"content": f.read()}
    return {"error": "File not found"}


@router.get("/api/workspace/{filename}/serve", response_class=HTMLResponse)
def serve_workspace_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Datei nicht gefunden</h1>", status_code=404)


@router.get("/api/workspace/{filename}/raw")
def serve_raw_file(filename: str):
    p = _safe_path(filename)
    if os.path.exists(p):
        return FileResponse(p)
    raise HTTPException(status_code=404, detail="Datei nicht gefunden")


@router.post("/api/workspace/{filename}/run")
def run_workspace_file(filename: str):
    p = _safe_path(filename)
    w = get_workspace_dir()
    if not os.path.exists(p): return {"error": "File not found"}
    if not filename.endswith(".py"): return {"error": "Nur .py Dateien können ausgeführt werden."}
    try:
        r = subprocess.run(["python3", p], capture_output=True, text=True, timeout=15, cwd=w)
        return {"stdout": r.stdout[-2000:], "stderr": r.stderr[-1000:], "code": r.returncode}
    except subprocess.TimeoutExpired: return {"error": "Timeout nach 15 Sekunden"}


@router.get("/api/project")
def get_project(): return {"project": SQLiteStateRepository().get_active_project()}
