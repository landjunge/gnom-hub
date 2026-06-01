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
