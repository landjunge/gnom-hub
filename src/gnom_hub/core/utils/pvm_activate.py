# pvm_activate.py
from gnom_hub.database.legacy_db import get_db_conn, log_audit_event

def activate_version(agent: str, version_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE agent = ?", (agent,))
                conn.execute("UPDATE prompt_versions SET is_active = 1 WHERE id = ?", (version_id,))
        log_audit_event(agent=agent, event_type="prompt_activated", details={"version_id": version_id})
    except Exception: pass
