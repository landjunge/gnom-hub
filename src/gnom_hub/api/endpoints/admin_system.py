import os, threading
from fastapi import APIRouter, Request
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository
from gnom_hub.db.state_repo import SQLiteStateRepository
from gnom_hub.core.security.hmac_signer import _get_or_create_secret
from gnom_hub.infrastructure.process.process_manager import _kill_proc, restart_hub

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

@router.post("/nuke")
def nuke_restart(request: Request):
    if request.client and request.client.host not in ("127.0.0.1", "::1", "localhost") and request.headers.get("X-Hub-Secret") != _get_or_create_secret().hex():
        return {"error": "Unauthorized"}
    import subprocess
    killed = 0
    # Aggressive kill: ALLE Gnom-Prozesse (auch Zombies ohne PID-File)
    for pattern in ["gnom_hub", "hub_app", "agents\\."]:
        try:
            r = subprocess.run(["pkill", "-9", "-f", pattern], capture_output=True, text=True, timeout=5)
            killed += 1
        except Exception:
            pass
    # Auch nach PID-Dateien
    for t in ["generalAG","soulAG","watchdogAG","securityAG","writerAG","editorAG","researcherAG","coderAG"]:
        try:
            _kill_proc(t)
        except Exception:
            pass
    threading.Timer(1.5, restart_hub).start()
    return {"status": "nuked", "msg": "Alle Prozesse gekillt, Hub startet neu in 1.5s"}
