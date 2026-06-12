import logging
import time, threading, os
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.infrastructure.process.process_manager import AGENTS, _get_proc

BUSY_TIMEOUT = 15 if os.environ.get("TESTING") == "true" else 120  # (war 60)

def pulse_janitor():
    repo = SQLiteAgentRepository()
    from datetime import datetime, timezone
    import json
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now()
    for agent in repo.list_all():
        if agent.status == "busy" and agent.last_seen:
            last_seen = agent.last_seen
            if last_seen.tzinfo is not None:
                diff = (now_utc - last_seen).total_seconds()
            else:
                diff = (now_local - last_seen).total_seconds()
            if diff > BUSY_TIMEOUT:
                agent.status = "online"
                agent.active_job = None
                repo.save(agent)
                try:
                    from gnom_hub.db import add_chat_message, get_active_project
                    add_chat_message(get_active_project(), "System", "war-room", "chat",
                                     f"⚠️ [System] Agent **{agent.name}** wurde nach 2 Minuten Inaktivität automatisch freigegeben (@free).",
                                     {"type": "chat"})
                except Exception as e:
                    logging.getLogger(__name__).error('Fehler in Agenten-Freigabe-Benachrichtigung: %s', e)
    for name in AGENTS:
        proc = _get_proc(name)
        agent = repo.get_by_name(name)
        if agent and agent.pid != (proc.pid if proc else None):
            agent.pid = proc.pid if proc else None
            repo.save(agent)

# Stuck-Message Recovery alle 5 Min (nicht bei jedem Pulse)
_last_recovery = 0
RECOVERY_INTERVAL = 300  # 5 Minuten

_last_security_check = 0
SECURITY_CHECK_INTERVAL = 60  # 1 Minute

def _maybe_security_dispatch():
    """Prüft auf blockierte Messages und dispatched an SecurityAG/WatchdogAG."""
    global _last_security_check
    now = time.time()
    if now - _last_security_check < SECURITY_CHECK_INTERVAL:
        return
    _last_security_check = now
    try:
        from gnom_hub.core.config import DB_PATH
        from gnom_hub.agents.swarm.swarm_comms import dispatch_mention, get_db_connection
        conn = get_db_connection()
        try:
            # Finde Messages die an Gatekeeper gescheitert sind (retry_count > 0, aber nicht done)
            rows = conn.execute("""
                SELECT id, recipient, sender, context_id, depth, parent_msg_id
                FROM agent_messages
                WHERE status IN ('pending', 'processing')
                  AND retry_count > 0
                  AND recipient NOT IN ('SecurityAG', 'WatchdogAG')
                  AND (sender = 'Gatekeeper' OR payload LIKE '%Gatekeeper%')
                ORDER BY created_at DESC
                LIMIT 5
            """).fetchall()
            
            for row in rows:
                # Dispatch an SecurityAG + WatchdogAG
                context_id = row["context_id"]
                depth = row["depth"]
                parent_id = row["parent_msg_id"]
                
                # SecurityAG
                dispatch_mention(
                    sender="System",
                    text="@SecurityAG Prüfe Gatekeeper-Blockade und erteile Freigabe falls User es verlangt. MSG-ID: " + str(row["id"]),
                    context_id=context_id,
                    db_path=str(DB_PATH),
                    current_depth=depth + 1,
                    parent_msg_id=parent_id,
                    priority="high"
                )
                
                # WatchdogAG
                dispatch_mention(
                    sender="System",
                    text="@WatchdogAG Prüfe Gatekeeper-Blockade auf geschützte Pfade. Erteile Alternativpfad falls nötig. MSG-ID: " + str(row["id"]),
                    context_id=context_id,
                    db_path=str(DB_PATH),
                    current_depth=depth + 1,
                    parent_msg_id=parent_id,
                    priority="high"
                )
        finally:
            conn.close()
    except Exception as e:
        logging.getLogger(__name__).warning("Security dispatch fehlgeschlagen: %s", e)

_last_recovery = 0
RECOVERY_INTERVAL = 300  # 5 Minuten

_last_ctx_cleanup = 0
CLEANUP_INTERVAL = 86400  # 24 Stunden

def _maybe_cleanup_contexts():
    global _last_ctx_cleanup
    now = time.time()
    if now - _last_ctx_cleanup < CLEANUP_INTERVAL:
        return
    _last_ctx_cleanup = now
    try:
        from gnom_hub.soul.memory_layers import get_context_db
        get_context_db().cleanup_old(days=7)
    except Exception as e:
        logging.getLogger(__name__).warning("ContextDB cleanup fehlgeschlagen: %s", e)

def _maybe_recover_stuck():
    global _last_recovery
    now = time.time()
    if now - _last_recovery < RECOVERY_INTERVAL:
        return
    _last_recovery = now
    try:
        from gnom_hub.core.config import DB_PATH
        from gnom_hub.agents.swarm.swarm_comms import recover_stuck_messages
        recover_stuck_messages(str(DB_PATH), timeout=300.0)
    except Exception as e:
        logging.getLogger(__name__).error("recover_stuck_messages fehlgeschlagen: %s", e)

def start_pulse(interval=30):
    def loop():
        while True:
            try: pulse_janitor()
            except Exception as e: logging.getLogger(__name__).error("Pulse janitor failed: %s", e)
            try: _maybe_recover_stuck()
            except Exception as e: logging.getLogger(__name__).error("Recovery check fehlgeschlagen: %s", e)
            try: _maybe_cleanup_contexts()
            except Exception as e: logging.getLogger(__name__).error("Context cleanup fehlgeschlagen: %s", e)
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
