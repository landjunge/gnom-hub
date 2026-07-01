# monitoring.py — Agent Health Monitoring & Heartbeat Tracker
import datetime
import logging
import threading
import time

METRICS = {}
_METRICS_LOCK = threading.Lock()

def record_agent_request(agent: str, duration_ms: float, success: bool):
    name = agent.lower()
    with _METRICS_LOCK:
        if name not in METRICS:
            METRICS[name] = {"total": 0, "failed": 0, "avg_time_ms": 0.0, "last_seen": 0.0}
        m = METRICS[name]
        m["total"] += 1
        if not success: m["failed"] += 1
        m["last_seen"] = time.time()
        m["avg_time_ms"] = ((m["avg_time_ms"] * (m["total"] - 1)) + duration_ms) / m["total"]

def get_agent_metrics() -> dict:
    from gnom_hub.db import get_all_agents
    with _METRICS_LOCK:
        metrics_snapshot = {k: dict(v) for k, v in METRICS.items()}
    now = time.time(); res = {}
    for a in (get_all_agents() or []):
        name = a["name"].lower()
        m = metrics_snapshot.get(name, {"total": 0, "failed": 0, "avg_time_ms": 0.0, "last_seen": 0.0})
        db_ts = 0.0
        try:
            db_ts = datetime.datetime.fromisoformat(a["last_seen"].replace("Z", "+00:00")).timestamp()
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in get_agent_metrics (ISO-Parse): %s', e)
        last_seen = max(m["last_seen"], db_ts)
        is_online = (now - last_seen < 120) and a["status"] == "online"
        res[name] = {
            "total": m["total"], "failed": m["failed"], "avg_time_ms": m["avg_time_ms"],
            "last_seen": last_seen,
            "success_rate": (m["total"] - m["failed"]) / m["total"] if m["total"] > 0 else 1.0,
            "status": "online" if is_online else "offline"
        }
    return res
