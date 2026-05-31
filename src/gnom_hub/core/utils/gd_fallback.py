# gd_fallback.py
import uuid, asyncio, logging
from datetime import datetime, timezone
from gnom_hub.db import get_db_conn, log_audit_event
from gnom_hub.infrastructure.router.router import ask_router

logger = logging.getLogger("degradation")

async def execute_with_fallback(mgr, agent: str, task: str, executor) -> tuple:
    if not mgr.is_online(agent):
        return await run_fallback(mgr, agent, "Offline status check", task)
    try:
        res = await executor() if asyncio.iscoroutinefunction(executor) else executor()
        return (res.completion if hasattr(res, "completion") else str(res)), True, None
    except Exception as e:
        logger.warning(f"Agent {agent} failed: {e}")
        return await run_fallback(mgr, agent, str(e), task)

async def run_fallback(mgr, agent: str, fail_type: str, task: str) -> tuple:
    opts = {"CoderAG": ["GeneralAG", "WriterAG"], "WriterAG": ["GeneralAG", "EditorAG"]}.get(agent, ["GeneralAG"])
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for fb in opts:
        if mgr.is_online(fb):
            try:
                import functools
                loop = asyncio.get_running_loop()
                eo = await loop.run_in_executor(
                    None,
                    functools.partial(ask_router, f"Führe als Backup diese Aufgabe aus: {task}", agent_name=fb)
                )
                if not eo.content.startswith("[ROUTER-FEHLER]"):
                    write_fail_log(agent, fail_type, fb, task, ts)
                    log_audit_event(agent=agent, event_type="degradation_fallback", details={"failure_type": fail_type, "fallback_agent": fb})
                    return eo.content, True, fb
            except Exception as e: logging.getLogger(__name__).error('Fehler in Fallback-Ausführung: %s', e)
    write_fail_log(agent, fail_type, None, task, ts)
    return f"[ROUTER-FEHLER] Alle Backups für {agent} ebenfalls fehlgeschlagen.", False, None

def write_fail_log(agent, fail, fb, task, ts):
    try:
        with get_db_conn() as conn:
            with conn: conn.execute("INSERT INTO graceful_degradation_failures (id, agent, failure_type, fallback_agent, task, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), agent, fail, fb, task, ts))
    except Exception as e: logging.getLogger(__name__).error('Fehler in Schreiben des Fehlerprotokolls: %s', e)
