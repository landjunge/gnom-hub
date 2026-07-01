# pvm_activate.py
import logging

from gnom_hub.db import log_audit_event
from gnom_hub.db.connection import get_db_conn


def activate_version(agent: str, version_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE agent = ?", (agent,))
                conn.execute("UPDATE prompt_versions SET is_active = 1 WHERE id = ?", (version_id,))
        log_audit_event(agent=agent, event_type="prompt_activated", details={"version_id": version_id})
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Version-Aktivierung: %s', e)
