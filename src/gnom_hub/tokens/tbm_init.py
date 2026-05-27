# tbm_init.py
from gnom_hub.database.legacy_db import get_db_conn

def init_tables():
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS token_budget_logs (
                        operation_id TEXT PRIMARY KEY, agent TEXT NOT NULL,
                        operation_type TEXT NOT NULL, input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL, model TEXT NOT NULL,
                        cost REAL NOT NULL, timestamp TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS token_budget_alerts (
                        id TEXT PRIMARY KEY, message TEXT NOT NULL,
                        timestamp TEXT NOT NULL, acknowledged INTEGER DEFAULT 0
                    )
                """)
    except Exception: pass
