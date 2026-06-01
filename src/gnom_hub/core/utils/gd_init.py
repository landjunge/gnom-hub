# gd_init.py
import logging
from gnom_hub.db.connection import get_db_conn

def init_tables():
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS graceful_degradation_failures (
                        id TEXT PRIMARY KEY, agent TEXT NOT NULL,
                        failure_type TEXT NOT NULL, fallback_agent TEXT,
                        task TEXT NOT NULL, timestamp TEXT NOT NULL
                    )
                """)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in Tabellen-Initialisierung: %s', e)
