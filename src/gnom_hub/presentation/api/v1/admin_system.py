import os, threading
from fastapi import APIRouter, Request
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.database.chat_repo import SQLiteChatRepository
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.security.hmac_signer import _get_or_create_secret
from gnom_hub.infrastructure.process.psutil_mgr import _kill_proc, restart_hub

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
    killed = []
    for t in ["generalAG", "soulAG", "watchdogAG", "securityAG", "writerAG", "editorAG", "researcherAG", "coderAG", os.environ.get("GNOM_HUB_PORT", "3002")]:
        _kill_proc(t)
        killed.append(t)
    threading.Timer(1.5, restart_hub).start()
    return {"status": "nuked", "killed": killed}
