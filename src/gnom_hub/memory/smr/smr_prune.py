import logging

# smr_prune.py
from datetime import datetime, timedelta, timezone

from gnom_hub.db.connection import get_db_conn
from gnom_hub.memory.smr.smr_math import cosine_similarity


def prune_low_relevance(threshold: float = 0.15, min_age_days: int = 30):
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT content FROM chat WHERE sender = 'user' ORDER BY timestamp DESC LIMIT 30").fetchall()
            q_list = [r["content"] for r in rows]
        if not q_list: return
        lim = (datetime.now(timezone.utc) - timedelta(days=min_age_days)).isoformat().replace("+00:00", "Z")
        p = ["active_preset", "approved_system_paths", "approved_security_writes", "approved_security_commands"]
        # placeholders sind ?, Werte parametrisiert.
        placeholders = ",".join("?" for _ in p)
        with get_db_conn() as conn:
            facts = [dict(r) for r in conn.execute(f"SELECT id, value FROM soul_memory WHERE timestamp < ? AND key NOT IN ({placeholders})", (lim, *p)).fetchall()]  # noqa: S608
            with conn:
                for f in facts:
                    if max(cosine_similarity(q, f["value"]) for q in q_list) < threshold:
                        conn.execute("DELETE FROM soul_memory WHERE id = ?", (f["id"],))
    except Exception as e: logging.getLogger(__name__).error('Fehler: %s', e)
