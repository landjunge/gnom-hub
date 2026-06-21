# metrics.py — FastAPI Router for agent metrics and audit logs
from fastapi import APIRouter; from pydantic import BaseModel
from gnom_hub.infrastructure.monitoring import get_agent_metrics
from gnom_hub.db.connection import get_db_conn
from gnom_hub.db import get_state_value; import sqlite3
router = APIRouter()
class FeedbackMsg(BaseModel): vote: str; comment: str
@router.get("/api/metrics")
def get_metrics():
    m = get_agent_metrics()
    m["_swarm_comms"] = get_state_value("active_swarm_comms", []) or []
    m["_active_workflow"] = get_state_value("active_workflow")
    try:
        with get_db_conn() as conn:
            m["_evolution_log"] = [dict(r) for r in conn.execute("SELECT key, value, timestamp FROM soul_memory WHERE key LIKE 'evolution_%' ORDER BY timestamp DESC").fetchall()]
    except Exception: m["_evolution_log"] = []
    return m
@router.post("/api/feedback")
def submit_feedback(msg: FeedbackMsg):
    from gnom_hub.soul import handle_user_feedback; handle_user_feedback(msg.vote, msg.comment)
    return {"status": "ok"}
@router.get("/api/audit-log")
def get_audit_log(agent: str = None, event: str = None, limit: int = 50):
    try:
        with get_db_conn() as conn:
            q = "SELECT * FROM audit_log"
            conds, args = [], []
            if agent: conds.append("agent = ?"); args.append(agent)
            if event: conds.append("event_type = ?"); args.append(event)
            if conds: q += " WHERE " + " AND ".join(conds)
            q += " ORDER BY timestamp DESC LIMIT ?"
            args.append(limit)
            return [dict(r) for r in conn.execute(q, args).fetchall()]
    except sqlite3.Error: return []


@router.get("/api/security-audit-log")
def get_security_audit_log(
    agent: str = None,
    action_type: str = None,
    result: str = None,
    severity: str = None,
    since: str = None,
    limit: int = 100,
):
    """SecurityAG-spezifischer Audit-Endpoint (Refactor-Schritt 4, Owner-Decision B).

    Filter: agent (z.B. "SecurityAG"), action_type (z.B. "security_write"), result
    ("allowed"|"denied"|"error"), severity ("low"|"medium"|"high"), since (ISO-8601).
    Default limit=100 (höher als /api/audit-log, weil SecurityAG-Audit dediziert ist
    und selten geladen werden muss).
    """
    try:
        with get_db_conn() as conn:
            q = "SELECT * FROM security_audit_log"
            conds, args = [], []
            if agent: conds.append("agent = ?"); args.append(agent)
            if action_type: conds.append("action_type = ?"); args.append(action_type)
            if result: conds.append("result = ?"); args.append(result)
            if severity: conds.append("severity = ?"); args.append(severity)
            if since: conds.append("timestamp >= ?"); args.append(since)
            if conds: q += " WHERE " + " AND ".join(conds)
            q += " ORDER BY timestamp DESC LIMIT ?"
            args.append(min(max(int(limit), 1), 1000))
            return [dict(r) for r in conn.execute(q, args).fetchall()]
    except sqlite3.Error as e:
        return {"error": str(e)}


@router.get("/metrics")
def prometheus_metrics():
    from fastapi.responses import PlainTextResponse
    import time
    from datetime import datetime
    
    lines = []
    with get_db_conn() as conn:
        # 1. Queue depth per agent & status
        rows = conn.execute("""
            SELECT recipient, status, COUNT(*) as cnt
            FROM agent_messages
            GROUP BY recipient, status
        """).fetchall()

        lines.append("# HELP gnomhub_queue_depth Nachrichten in der Queue")
        lines.append("# TYPE gnomhub_queue_depth gauge")
        for r in rows:
            lines.append(
                f'gnomhub_queue_depth{{agent="{r["recipient"]}",status="{r["status"]}"}} {r["cnt"]}'
            )

        # 2. Dead-letter count
        dlq = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE status='dead_letter'"
        ).fetchone()[0]
        lines.append("# HELP gnomhub_dead_letter_total Nachrichten in der DLQ")
        lines.append("# TYPE gnomhub_dead_letter_total counter")
        lines.append(f"gnomhub_dead_letter_total {dlq}")

        # 3. Agent Heartbeat Drift
        agents = conn.execute(
            "SELECT name, last_seen FROM agents"
        ).fetchall()
        lines.append("# HELP gnomhub_heartbeat_drift_seconds Sekunden seit letztem Heartbeat")
        lines.append("# TYPE gnomhub_heartbeat_drift_seconds gauge")
        now = time.time()
        for a in agents:
            last_seen_str = a["last_seen"]
            drift = 999999.0
            if last_seen_str:
                try:
                    # Parse standard SQLite last_seen (isoformat)
                    dt = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                    drift = now - dt.timestamp()
                except (ValueError, TypeError):
                    pass
            lines.append(
                f'gnomhub_heartbeat_drift_seconds{{agent="{a["name"]}"}} {drift:.1f}'
            )

        # 4. Throughput: processed messages last 60s
        throughput = conn.execute("""
            SELECT recipient, COUNT(*) as cnt
            FROM agent_messages
            WHERE status = 'done'
              AND created_at > ?
            GROUP BY recipient
        """, (now - 60.0,)).fetchall()

        lines.append("# HELP gnomhub_throughput_60s Verarbeitete Msgs letzte 60s")
        lines.append("# TYPE gnomhub_throughput_60s gauge")
        for t in throughput:
            lines.append(
                f'gnomhub_throughput_60s{{agent="{t["recipient"]}"}} {t["cnt"]}'
            )

    return PlainTextResponse("\n".join(lines))
