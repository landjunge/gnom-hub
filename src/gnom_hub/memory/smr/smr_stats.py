# smr_stats.py
from gnom_hub.db.connection import get_db_conn

def get_memory_stats() -> dict:
    try:
        with get_db_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM soul_memory").fetchone()[0]
            rows_agent = conn.execute("SELECT agent, COUNT(*) as cnt FROM soul_memory GROUP BY agent").fetchall()
            by_agent = {r["agent"]: r["cnt"] for r in rows_agent if r["agent"]}
            newest = conn.execute("SELECT MAX(timestamp) FROM soul_memory").fetchone()[0]
            oldest = conn.execute("SELECT MIN(timestamp) FROM soul_memory").fetchone()[0]
            return {"total_facts": total, "by_agent": by_agent, "newest_timestamp": newest, "oldest_timestamp": oldest}
    except Exception:
        return {"total_facts": 0, "by_agent": {}, "newest_timestamp": None, "oldest_timestamp": None}
