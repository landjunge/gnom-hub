# tbm_stats.py
from datetime import datetime, timezone, timedelta
from gnom_hub.database.legacy_db import get_db_conn

def get_budget_status(limit: float) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spent = 0.0
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT SUM(cost) FROM token_budget_logs WHERE timestamp LIKE ?", (f"{today}%",)).fetchone()
            if row and row[0]: spent = float(row[0])
    except Exception: pass
    return {"spent_today": spent, "daily_limit": limit, "remaining": max(0.0, limit - spent), "percentage_used": min(100.0, (spent / limit) * 100.0) if limit > 0.0 else 0.0}

def get_agent_usage(agent: str, days: int = 7) -> dict:
    lim = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    cost, tokens = 0.0, 0
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT SUM(cost), SUM(input_tokens + output_tokens) FROM token_budget_logs WHERE agent = ? AND timestamp >= ?", (agent, lim)).fetchone()
            if row: cost, tokens = float(row[0] or 0.0), int(row[1] or 0)
    except Exception: pass
    return {"agent": agent, "days": days, "total_cost": cost, "total_tokens": tokens}

def get_recent_alerts() -> list:
    alerts = []
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM token_budget_alerts WHERE acknowledged = 0 ORDER BY timestamp DESC").fetchall()
            for r in rows: alerts.append(dict(r))
    except Exception: pass
    return alerts

def acknowledge_alert(alert_id: str):
    try:
        with get_db_conn() as conn:
            with conn: conn.execute("UPDATE token_budget_alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    except Exception: pass
