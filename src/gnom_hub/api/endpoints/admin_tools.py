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

# Async Bake — Background Jobs
import threading, uuid, time as _time
_bake_jobs = {}

def _do_bake(job_id: str, req: 'BakeRequest'):
    import os, json
    from gnom_hub.core.config import PROJECT_ROOT, CONFIG_DIR
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
        path = bake_supergnom(req.name, req.template)
        dist_path = Path(path)
        if req.embed_api_key:
            key = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENROUTER_KEY_FREE_1","")
            if key:
                env_file = dist_path / "config" / ".env"
                with open(env_file, "a", encoding="utf-8") as f:
                    f.write(f"\nDEEPSEEK_API_KEY={key}\n")
                keys_file = dist_path / "keys.txt"
                with open(keys_file, "w", encoding="utf-8") as f:
                    f.write(f"DEEPSEEK_API_KEY={key}\n")
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
    # Alle nicht-essentiellen Tabellen leeren
    for tbl in ['chat','audit_log','prompt_versions','capabilities','showbox_presentations',
                'explainable_outputs','agent_messages','swarm_callbacks','agent_capabilities',
                'workflows','workflow_tasks','soul_memory','token_budget_logs','token_budget_alerts']:
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

    # Workspace leeren
    wd = os.path.join(str(WORKSPACE_DIR), 'default')
    if os.path.exists(wd):
        for item in os.listdir(wd):
            item_path = os.path.join(wd, item)
            try:
                if os.path.isdir(item_path): shutil.rmtree(item_path)
                else: os.remove(item_path)
            except OSError as e:
                _log.warning("Workspace: %s nicht löschbar: %s", item, e)

    # Neustart in 3s (nachdem die Antwort zurück ist)
    import threading
    def delayed_restart():
        import time; time.sleep(3)
        from gnom_hub.infrastructure.process.process_manager import restart_hub
        restart_hub()
    threading.Thread(target=delayed_restart, daemon=True).start()

    return {
        "status": "cleaned",
        "msg": "Alles geleert. Hub startet neu in 3s.",
        "backup": backup_result,
    }

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
