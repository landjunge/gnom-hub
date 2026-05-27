# pvm_history.py
from gnom_hub.database.legacy_db import get_db_conn
from gnom_hub.evolution.evolution_v2 import _row_to_version

def get_version_by_id(version_id: str):
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,)).fetchone()
            if row: return _row_to_version(row)
    except Exception: pass
    return None

def get_version_history(agent: str, limit: int = 10):
    history = []
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM prompt_versions WHERE agent = ? ORDER BY created_at DESC LIMIT ?", (agent, limit)).fetchall()
            for r in rows: history.append(_row_to_version(r))
    except Exception: pass
    return history
