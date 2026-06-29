import logging
from fastapi import APIRouter
from pydantic import BaseModel
from gnom_hub.db.state_repo import SQLiteStateRepository
_log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")

class BakeRequest(BaseModel):
    name: str
    template: str = "chat"
    embed_api_key: bool = True
    preset_file: str = ""
    selected_models: list = []
    preset_selections: dict = {}  # {agent_name: preset_slug} per-agent selection

# Async Bake — Background Jobs
import threading, uuid, time as _time
_bake_jobs = {}

def _do_bake(job_id: str, req: 'BakeRequest'):
    import os, json, logging, stat, tempfile
    from gnom_hub.core.config import PROJECT_ROOT, CONFIG_DIR
    _log = logging.getLogger(__name__)
    try:
        if req.preset_file:
            preset_path = CONFIG_DIR / "presets" / req.preset_file
            if preset_path.exists():
                data = json.loads(preset_path.read_text(encoding="utf-8"))
                from gnom_hub.db import set_state_value
                if data.get("agent_settings"):
                    set_state_value("agent_settings", data["agent_settings"])
        from gnom_hub.core.utils.compiler import bake_supergnom
        from pathlib import Path
        path = bake_supergnom(req.name, req.template, req.selected_models, req.preset_selections)
        dist_path = Path(path)
        if req.embed_api_key:
            key = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENROUTER_KEY_FREE_1","")
            if key:
                env_file = dist_path / "config" / ".env"
                with open(env_file, "a", encoding="utf-8") as f:
                    f.write(f"\nDEEPSEEK_API_KEY={key}\n")
                # Sicherheits-Hinweis: API-Key landet im Klartext in keys.txt.
                # Das ist Teil des Bake-Workflows (User kopiert die Datei in
                # sein Gnom-Hub-Setup); chmod 600 schützt vor anderen lokalen
                # Usern. Atomares Schreiben über tempfile + rename, damit
                # partielle Files bei Crash nicht zurückbleiben.
                keys_file = dist_path / "keys.txt"
                _dir = keys_file.parent
                _dir.mkdir(parents=True, exist_ok=True)
                fd, tmp_path = tempfile.mkstemp(prefix=".keys_", suffix=".txt", dir=str(_dir))
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(f"DEEPSEEK_API_KEY={key}\n")
                    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
                    os.replace(tmp_path, keys_file)
                except Exception:
                    if os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                    raise
                _log.warning(
                    "Bake: API-Key wurde in %s geschrieben (mode 0600). "
                    "Datei enthält den Key im Klartext — vor Weitergabe des "
                    "gebakten Projekts entfernen oder überschreiben.",
                    keys_file,
                )
        _bake_jobs[job_id] = {"status": "finished", "path": str(dist_path), "error": None}
    except Exception as e:
        _bake_jobs[job_id] = {"status": "error", "path": None, "error": str(e)}

@router.post("/bake/start")
def bake_start(req: BakeRequest):
    """Startet Bake-Job im Hintergrund. Gibt job_id zurück."""
    job_id = str(uuid.uuid4())[:8]
    _bake_jobs[job_id] = {"status": "running", "path": None, "error": None}
    t = threading.Thread(target=_do_bake, args=(job_id, req), daemon=True)
    t.start()
    return {"status": "started", "job_id": job_id}


@router.get("/bake/preview")
def bake_preview():
    """Schnittmenge Ollama-Modelle ∩ routing.txt — User kann im Frontend wählen."""
    try:
        from gnom_hub.core.utils.compiler import (
            intersect_ollama_routing,
            ollama_get_models_with_sizes,
            routing_get_models_used,
        )
        intersection = intersect_ollama_routing()
        return {
            "intersection": intersection,
            "ollama_all": ollama_get_models_with_sizes(),
            "routing_used": routing_get_models_used(),
            "auto_threshold_gb": 2.0,
            "default_recommendation": [m["name"] for m in intersection["matches"]],
        }
    except Exception as e:
        _log.exception("Bake-Preview fehlgeschlagen: %s", e)
        return {"error": str(e)}

@router.get("/bake/status/{job_id}")
def bake_status(job_id: str):
    """Fragt Bake-Job-Status ab."""
    job = _bake_jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job

@router.post("/clean-all")
def clean_all():
    """Alles zurücksetzen: DB, Tokens, Workspace, Logs. Dann Neustart.
    Erstellt ZUERST ein unveränderliches Backup (cleanAll-Trigger)."""
    import os, shutil, subprocess
    from pathlib import Path
    from gnom_hub.db.connection import get_db_connection
    from gnom_hub.db.passive_db import get_passive_conn
    from gnom_hub.core.config import CONFIG_DIR, WORKSPACE_DIR, PROJECT_ROOT

    # ── 1. Backup ZUERST (nie überschreiben, atomar) ─────────
    backup_script = Path(PROJECT_ROOT) / "scripts" / "backup_all_dbs.sh"
    backup_result = {"status": "skipped", "path": None}
    if backup_script.exists():
        try:
            r = subprocess.run(
                [str(backup_script), "cleanAll"],
                cwd=str(PROJECT_ROOT),
                capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0:
                # Letzte Zeile enthält "✅ Backup erfolgreich: <pfad>"
                for line in r.stdout.splitlines()[::-1]:
                    if "Backup erfolgreich:" in line:
                        backup_result["path"] = line.split(":", 1)[-1].strip()
                        backup_result["status"] = "ok"
                        break
                _log.info("CleanAll-Backup erstellt: %s", backup_result["path"])
            else:
                _log.error("Backup fehlgeschlagen (rc=%d): %s", r.returncode, r.stderr)
                return {
                    "status": "aborted",
                    "reason": "backup_failed",
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                }
        except Exception as e:
            _log.exception("Backup-Aufruf fehlgeschlagen: %s", e)
            return {"status": "aborted", "reason": "backup_exception", "error": str(e)}

    conn = get_db_connection()
    # Alle nicht-essentiellen Tabellen leeren.
    # soul_memory wird BEHALTEN — ist das Lern-Gedächtnis von Gnom.
    # Soll explizit via eigenem Endpoint oder manuell gelöscht werden.
    for tbl in ['chat','audit_log','security_audit_log','prompt_versions','capabilities','showbox_presentations',
                'explainable_outputs','agent_messages','swarm_callbacks','agent_capabilities',
                'workflows','workflow_tasks','token_budget_logs','token_budget_alerts']:
        try: conn.execute(f'DELETE FROM {tbl}')
        except Exception as e:
            _log.warning("Cleanup: Tabelle %s nicht leerbar: %s", tbl, e)
    # State reset
    conn.execute("DELETE FROM state WHERE key NOT IN ('active_project','language','active_showbox','enable_confirmations')")
    conn.execute("UPDATE agents SET status='online', circuit_state='CLOSED', consecutive_failures=0")
    conn.commit()
    conn.close()

    # Token-File löschen
    for token_file in list(CONFIG_DIR.glob('.gnom-hub-tokens*.json')):
        try: token_file.unlink()
        except OSError as e:
            _log.warning("Token-File %s nicht löschbar: %s", token_file.name, e)

    # Passive DB
    try:
        pconn = get_passive_conn()
        for t in pconn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            try: pconn.execute(f'DELETE FROM {t["name"]}')
            except Exception as e:
                _log.warning("Passive DB: Tabelle %s nicht leerbar: %s", t["name"], e)
        pconn.commit()
        pconn.close()
    except Exception as e:
        _log.warning("Passive DB nicht verfügbar: %s", e)

    # Workspace leeren — wurde aus cleanAll entfernt weil es außerhalb vom
    # Gnom-Hub-Repo liegt (~/gnom-Workspace/) und der User dort eigene Files hat.
    # Wer Workspace leeren will: explizit via /api/admin/clean-workspace mit
    # eigenem Confirm-Endpoint.
    # wd = os.path.join(str(WORKSPACE_DIR), 'default')  # ← auskommentiert
    # if os.path.exists(wd):
    #     for item in os.listdir(wd):
    #         ...

    # Neustart in 3s (nachdem die Antwort zurück ist)
    import threading
    import os
    from gnom_hub.api.endpoints.admin_system import _delayed_restart
    my_pid = os.getpid()
    threading.Timer(3.0, _delayed_restart, args=[my_pid]).start()

    return {
        "status": "cleaned",
        "msg": "Alles geleert. Hub startet neu in 3s.",
        "backup": backup_result,
    }


@router.post("/backup")
def create_backup():
    """Non-destructive backup. Calls scripts/backup_all_dbs.sh and returns the path.

    Trigger label: 'manual'. Does NOT touch any DB tables or workspace.
    """
    import os, subprocess
    from pathlib import Path
    from gnom_hub.core.config import PROJECT_ROOT

    backup_script = Path(PROJECT_ROOT) / "scripts" / "backup_all_dbs.sh"
    if not backup_script.exists():
        return {"status": "error", "info": f"backup script not found: {backup_script}"}

    try:
        r = subprocess.run(
            [str(backup_script), "manual"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=120,
        )
    except Exception as e:
        _log.exception("Backup-Aufruf fehlgeschlagen: %s", e)
        return {"status": "error", "info": str(e)}

    if r.returncode != 0:
        _log.error("Backup fehlgeschlagen (rc=%d): %s", r.returncode, r.stderr)
        return {
            "status": "error",
            "info": "backup_failed",
            "stdout": r.stdout,
            "stderr": r.stderr,
        }

    backup_path = None
    # Script log line looks like: "[HH:MM:SS] ✅ Backup erfolgreich: <path>"
    # The timestamp contains ':' so a naive split on ':' mangles the path.
    for line in r.stdout.splitlines()[::-1]:
        idx = line.find("Backup erfolgreich:")
        if idx >= 0:
            backup_path = line[idx + len("Backup erfolgreich:"):].strip()
            break
    return {"status": "ok", "path": backup_path, "stdout": r.stdout}


class ToolDef(BaseModel):
    name: str
    description: str = ""
    method: str = "GET"
    path: str = ""

@router.get("/tools")
def list_tools():
    return SQLiteStateRepository().get_value("tools", [])

@router.post("/tools")
def register_tool(t: ToolDef):
    repo = SQLiteStateRepository()
    tools = [x for x in repo.get_value("tools", []) if x["name"] != t.name] + [t.dict()]
    repo.set_value("tools", tools)
    return {"registered": t.name}

@router.delete("/tools/{name}")
def remove_tool(name: str):
    repo = SQLiteStateRepository()
    tools = [t for t in repo.get_value("tools", []) if t["name"] != name]
    repo.set_value("tools", tools)
    return {"removed": name}


@router.post("/clean-workspace")
def clean_workspace(payload: dict = None):
    """Workspace-Inhalt leeren — EXPLIZIT, mit Type-Confirm "DELETE" im Body.

    Im Gegensatz zu /clean-all (das nur DBs löscht) löscht dieser Endpoint
    NUR den User-Workspace unter ~/gnom-Workspace/default. Erfordert
    explizit confirm="DELETE" im Body damit niemand versehentlich klickt.

    Body: {"confirm": "DELETE"}
    """
    import os, shutil
    from gnom_hub.core.config import WORKSPACE_DIR

    payload = payload or {}
    if payload.get("confirm") != "DELETE":
        return {
            "status": "error",
            "info": "Bestätigung erforderlich: sende {\"confirm\": \"DELETE\"} im Body"
        }

    wd = os.path.join(str(WORKSPACE_DIR), 'default')
    if not os.path.exists(wd):
        return {"status": "ok", "info": "Workspace war bereits leer", "deleted": 0}

    deleted = 0
    for item in os.listdir(wd):
        item_path = os.path.join(wd, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            deleted += 1
        except OSError as e:
            logging.getLogger(__name__).warning("Workspace: %s nicht löschbar: %s", item, e)

    return {
        "status": "ok",
        "info": f"Workspace geleert: {deleted} Items entfernt",
        "deleted": deleted,
        "workspace": wd,
    }
