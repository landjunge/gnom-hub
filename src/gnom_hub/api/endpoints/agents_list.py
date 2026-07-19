import json
import os

from fastapi import APIRouter, Query

from gnom_hub.core.config import TOKENS_FILE
from gnom_hub.db.agent_repo import SQLiteAgentRepository

router = APIRouter(tags=["agents"])

@router.get("/api/agents")
def list_agents(health: bool = Query(False, description="Include honest health fields")):
    repo = SQLiteAgentRepository()
    ags = [dict(a.__dict__) for a in repo.get_all()]
    for a in ags:
        if a.get("active_job"): a["status"] = "busy"
        elif a.get("status") == "running": a["status"] = "online"
        # UUID/datetime not JSON-serializable as-is in some paths
        if hasattr(a.get("id"), "hex"):
            a["id"] = str(a["id"])
        if a.get("last_seen") is not None and hasattr(a["last_seen"], "isoformat"):
            a["last_seen"] = a["last_seen"].isoformat()
    if health:
        try:
            from gnom_hub.infrastructure.agent_health import collect_all_agent_health
            snap = collect_all_agent_health()
            by_name = {h["name"].lower(): h for h in snap.get("agents", [])}
            for a in ags:
                h = by_name.get((a.get("name") or "").lower())
                if h:
                    a["health"] = h
                    a["effective_status"] = h["effective_status"]
                    a["process_alive"] = h["process_alive"]
                    a["queue"] = h["queue"]
                    a["healthy"] = h["healthy"]
        except Exception:
            pass
    return ags


@router.get("/api/agents/health")
def agents_health():
    """Honest health for all agents: process + heartbeat + queue."""
    from gnom_hub.infrastructure.agent_health import collect_all_agent_health
    return collect_all_agent_health()


@router.get("/api/agents/search")
def search_agents(q: str):
    return [a for a in list_agents() if q.lower() in str(a).lower()]

@router.get("/api/agents/{a_id}")
def get_agent(a_id: str):
    return next((a for a in list_agents() if a.get("id") == a_id or a.get("name") == a_id), {})

@router.get("/api/stats")
def get_system_stats():
    from gnom_hub.db.chat_repo import SQLiteChatRepository
    from gnom_hub.db.connection import get_db_conn
    from gnom_hub.db.state_repo import SQLiteStateRepository
    from gnom_hub.memory.smr.smr_stats import get_memory_stats
    from gnom_hub.soul import SOULS
    sys_set = {k for k, v in SOULS.items() if v.get("role") not in ("writer","coder","researcher","editor")}
    d = json.load(open(str(TOKENS_FILE))) if os.path.exists(str(TOKENS_FILE)) else {}
    ags = list_agents()
    sa = sum(1 for a in ags if a.get("name","").lower() in sys_set)
    cc = SQLiteChatRepository().count_messages()
    mem = get_memory_stats().get("total_facts", 0)
    tfb = SQLiteStateRepository().get_value("tokens", [{}])[0].get("total", 0) if SQLiteStateRepository().get_value("tokens") else 0
    # Ops panel: queue depth, leases, last error
    queue = {"pending": 0, "processing": 0, "dead_letter": 0, "failed": 0}
    leases = []
    last_error = None
    try:
        with get_db_conn() as conn:
            for row in conn.execute(
                "SELECT status, COUNT(*) AS c FROM agent_messages "
                "WHERE status IN ('pending','processing','dead_letter','failed') GROUP BY status"
            ):
                st = row["status"] if hasattr(row, "keys") else row[0]
                cnt = row["c"] if hasattr(row, "keys") else row[1]
                if st in queue:
                    queue[st] = int(cnt)
            for row in conn.execute(
                """
                SELECT id, recipient, sender, processing_since, created_at
                FROM agent_messages
                WHERE status = 'processing'
                ORDER BY COALESCE(processing_since, created_at) ASC
                LIMIT 8
                """
            ):
                leases.append({
                    "id": row["id"],
                    "recipient": row["recipient"],
                    "sender": row["sender"],
                    "processing_since": row["processing_since"],
                    "created_at": row["created_at"],
                })
            err = conn.execute(
                """
                SELECT id, recipient, status, completed_at
                FROM agent_messages
                WHERE status IN ('dead_letter', 'failed')
                ORDER BY COALESCE(completed_at, 0) DESC
                LIMIT 1
                """
            ).fetchone()
            if err:
                last_error = {
                    "id": err["id"],
                    "recipient": err["recipient"],
                    "status": err["status"],
                    "completed_at": err["completed_at"],
                }
    except Exception:
        pass
    return {
        "agents": len(ags),
        "sys_agents": sa,
        "work_agents": len(ags) - sa,
        "memory": mem,
        "chat": cc,
        "tokens": d.get("total", tfb),
        "tokens_free": d.get("total_free", 0),
        "tokens_pay": d.get("total_pay", 0),
        "queue": queue,
        "leases": leases,
        "last_error": last_error,
    }
