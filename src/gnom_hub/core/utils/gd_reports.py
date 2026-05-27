# gd_reports.py
from datetime import datetime, timezone, timedelta
from gnom_hub.database.legacy_db import get_db_conn

def get_failure_report(agent=None, days: int = 7) -> list:
    lim = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    failures = []
    try:
        with get_db_conn() as conn:
            q = "SELECT * FROM graceful_degradation_failures WHERE agent = ? AND timestamp >= ? ORDER BY timestamp DESC" if agent else "SELECT * FROM graceful_degradation_failures WHERE timestamp >= ? ORDER BY timestamp DESC"
            p = (agent, lim) if agent else (lim,)
            rows = conn.execute(q, p).fetchall()
            for r in rows: failures.append(dict(r))
    except Exception: pass
    return failures

def get_degradation_report() -> dict:
    report = {}
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT agent, COUNT(*) as cnt FROM graceful_degradation_failures GROUP BY agent").fetchall()
            for r in rows: report[r["agent"]] = r["cnt"]
    except Exception: pass
    return report
