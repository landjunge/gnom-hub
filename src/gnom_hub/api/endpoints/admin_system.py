import hmac, os, threading, subprocess, logging
from typing import List
from fastapi import APIRouter, Request
import psutil
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.core.security.hmac_signer import _get_or_create_secret
from gnom_hub.infrastructure.process.process_manager import _kill_proc, AGENTS
from gnom_hub.core.constants import ADMIN_SYSTEM_PKILL_TIMEOUT

router = APIRouter(prefix="/api/admin")
log = logging.getLogger(__name__)

@router.post("/cleanup")
def cleanup_offline():
    SQLiteAgentRepository().delete_offline()
    from gnom_hub.db import cleanup_old_data
    cleanup_old_data()
    return {"status": "ok"}

@router.get("/health")
def health():
    import os, time, sqlite3
    from gnom_hub.core.config import DB_PATH
    # DB-Integrität prüfen
    db_ok = False
    db_size = 0
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute("PRAGMA integrity_check")
        db_ok = cur.fetchone()[0] == "ok"
        db_size = os.path.getsize(DB_PATH)
        conn.close()
    except Exception:
        pass
    # Letztes Backup suchen
    last_backup_ts = None
    backup_root = os.path.expanduser("~/Desktop/gnom_dev/backups_datenbanken")
    if os.path.exists(backup_root):
        dirs = [os.path.join(backup_root, d) for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))]
        if dirs:
            last_backup_ts = max(os.path.getmtime(d) for d in dirs)
    agents = SQLiteAgentRepository().get_all()
    online_count = sum(1 for a in agents if (getattr(a, "status", None) == "online" or (hasattr(a, '__dict__') and a.__dict__.get('status') == "online")))
    # Chat-Count: Await-Objekt → sync aus DB lesen
    chat_count = 0
    try:
        import sqlite3
        from gnom_hub.core.config import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        chat_count = conn.execute("SELECT COUNT(*) FROM chat").fetchone()[0]
        conn.close()
    except Exception:
        pass
    return {
        "status": "ok",
        "db_ok": db_ok,
        "db_size_bytes": db_size,
        "db_size_mb": round(db_size / 1024 / 1024, 2),
        "agents_total": len(agents),
        "agents_online": online_count,
        "memory": chat_count,
        "tools": len(SQLiteStateRepository().get_value("tools", [])),
        "last_backup_unix": last_backup_ts,
        "last_backup_ago_min": round((time.time() - last_backup_ts) / 60, 1) if last_backup_ts else None,
        "uptime_check": "OK"
    }

@router.get("/blockade-level")
def get_blockade_level():
    from gnom_hub.db import get_state_value
    return {"level": int(get_state_value("blockade_level", 0))}

@router.put("/blockade-level")
def set_blockade_level(level: int):
    from gnom_hub.db import get_state_value, set_state_value
    old_level = int(get_state_value("security_blockade_level", 0) or 0)
    level = max(0, min(4, level))
    # Schreibt BEIDE Keys — vorher nur blockade_level, was path_validator
    # NICHT liest → Silent-No-Op (gefixt 2026-06-27).
    set_state_value("security_blockade_level", level)
    set_state_value("blockade_level", level)
    try:
        from gnom_hub.core.audit_helpers import record_blockade_change
        record_blockade_change("admin", old_level=old_level, new_level=level,
                               source="PUT /api/admin/blockade-level")
    except Exception:
        pass
    return {"level": level}

@router.post("/nuke")
def nuke_restart(request: Request):
    expected = _get_or_create_secret().hex()
    presented = request.headers.get("X-Hub-Secret", "")
    is_local = bool(request.client and request.client.host in ("127.0.0.1", "::1", "localhost"))
    secret_ok = hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))
    if not is_local and not secret_ok:
        return {"error": "Unauthorized"}
    my_pid = os.getpid()
    killed = _kill_processes_by_name(["gnom_hub", "hub_app"], exclude_pids=[my_pid])
    for t in AGENTS:
        try:
            _kill_proc(t)
        except Exception:
            pass
    # Hub-Selbstmord gefahrlos: detached subprocess ruft start_gnom_hub.sh auf
    # nach kurzer Verzögerung, damit der alte Hub wirklich weg ist
    threading.Timer(1.5, _delayed_restart, args=[my_pid]).start()
    return {"status": "nuked", "msg": f"{killed} Prozesse gekillt, Hub startet neu in 1.5s"}


def _kill_processes_by_name(names: List[str], exclude_pids: list = None) -> int:
    killed = 0
    exclude_pids = exclude_pids or []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] in exclude_pids:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(n in cmdline for n in names):
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def _is_old_hub_still_alive(pid: int) -> bool:
    """True wenn PID existiert UND der Prozess wie ein Hub aussieht.

    PID-Recycling-Schutz: wenn der Hub schnell stirbt und ein anderer
    Prozess die PID kriegt, dürfen wir nicht fälschlich auf einen toten
    Hub warten und den Restart blockieren.
    """
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline() or []).lower()
        name = (proc.name() or "").lower()
        return any(n.lower() in cmdline or n.lower() in name for n in ("gnom_hub", "hub_app"))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _delayed_restart(old_hub_pid: int, max_wait_s: float = 30.0) -> None:
    """Startet Hub neu in einem separaten Prozess, nachdem der alte Hub tot ist."""
    import time
    # Warte bis der alte Hub wirklich weg ist (PID-Recycling-sicher)
    waited = 0.0
    poll_interval = 0.2
    while waited < max_wait_s:
        if not _is_old_hub_still_alive(old_hub_pid):
            break
        time.sleep(poll_interval)
        waited += poll_interval
    else:
        log.warning("Alter Hub (PID %s) nach %.1fs noch nicht beendet — starte trotzdem neu", old_hub_pid, max_wait_s)

    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    script = os.path.join(repo, "start_gnom_hub.sh")
    if not os.path.exists(script):
        log.error("start_gnom_hub.sh nicht gefunden unter %s — Hub bleibt offline!", script)
        return
    try:
        proc = subprocess.Popen(
            ["bash", script],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        log.info("Hub neu gestartet (PID %s) nach %.1fs Wartezeit", proc.pid, waited)
    except OSError as e:
        log.error("Hub-Restart fehlgeschlagen beim Popen: %s", e)
