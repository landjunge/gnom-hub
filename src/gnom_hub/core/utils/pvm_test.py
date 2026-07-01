# pvm_test.py
import logging

from gnom_hub.core.utils.evolution_v2 import _row_to_version
from gnom_hub.db.connection import get_db_conn


def record_test_result(version_id: str, success: bool):
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,)).fetchone()
            if row:
                v = _row_to_version(row)
                new_cnt = v.feedback_count + 1
                new_score = (v.performance_score * v.feedback_count + (1.0 if success else 0.0)) / new_cnt
                with conn:
                    conn.execute("UPDATE prompt_versions SET performance_score = ?, feedback_count = ? WHERE id = ?", (new_score, new_cnt, version_id))
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Testergebnis-Speicherung: %s', e)
