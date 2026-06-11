import os, threading, subprocess
from typing import List
from fastapi import APIRouter, Request
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.core.security.hmac_signer import _get_or_create_secret
from gnom_hub.infrastructure.process.process_manager import _kill_proc, restart_hub, AGENTS
from gnom_hub.core.constants import ADMIN_SYSTEM_PKILL_TIMEOUT

router = APIRouter(prefix="/api/admin")

@router.post("/cleanup")
def cleanup_offline():
    SQLiteAgentRepository().delete_offline()
    from gnom_hub.db import cleanup_old_data
    cleanup_old_data()
    return {"status": "ok"}

@router.get("/health")
def health():
    return {
        "status": "ok",
        "agents": len(SQLiteAgentRepository().get_all()),
        "memory": SQLiteChatRepository().count_messages(),
        "tools": len(SQLiteStateRepository().get_value("tools", []))
    }

def _kill_processes_by_name(names: List[str]) -> int:
    import psutil
    killed = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(n in cmdline for n in names):
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed

@router.get("/blockade-level")
def get_blockade_level():
    from gnom_hub.db import get_state_value
    return {"level": int(get_state_value("blockade_level", 0))}

@router.put("/blockade-level")
def set_blockade_level(level: int):
    from gnom_hub.db import set_state_value
    level = max(0, min(4, level))
    set_state_value("blockade_level", level)
    return {"level": level}

@router.post("/nuke")
def nuke_restart(request: Request):
    if request.client and request.client.host not in ("127.0.0.1", "::1", "localhost") and request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex():
        return {"error": "Unauthorized"}
    killed = _kill_processes_by_name(["gnom_hub", "hub_app"])
    for t in AGENTS:
        try:
            _kill_proc(t)
        except Exception:
            pass
    threading.Timer(1.5, restart_hub).start()
    return {"status": "nuked", "msg": f"{killed} Prozesse gekillt, Hub startet neu in 1.5s"}
