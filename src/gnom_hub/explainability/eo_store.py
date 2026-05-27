# eo_store.py
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from gnom_hub.database.legacy_db import get_db_conn
from gnom_hub.explainability.eo_class import ExplainableOutput
from gnom_hub.explainability.eo_formatter import ExplainableOutputFormatter

class ExplainableOutputStore:
    def __init__(self, db=None):
        self.db = db
        try:
            with get_db_conn() as conn:
                with conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS explainable_outputs (id TEXT PRIMARY KEY, agent TEXT NOT NULL, task TEXT NOT NULL, data TEXT NOT NULL, timestamp TEXT NOT NULL)")
        except Exception: pass

    def store(self, o: ExplainableOutput) -> str:
        oid = str(uuid.uuid4())
        data_str = ExplainableOutputFormatter.to_json(o)
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            with get_db_conn() as conn:
                with conn:
                    conn.execute("INSERT INTO explainable_outputs (id, agent, task, data, timestamp) VALUES (?, ?, ?, ?, ?)", (oid, o.agent, o.task, data_str, ts))
        except Exception: pass
        return oid

    def get(self, oid: str) -> Optional[ExplainableOutput]:
        try:
            with get_db_conn() as conn:
                r = conn.execute("SELECT * FROM explainable_outputs WHERE id = ?", (oid,)).fetchone()
                if r:
                    d = json.loads(r["data"])
                    return ExplainableOutput(d.get("agent"), d.get("task"), d.get("answer"), d.get("confidence", 0.0), d.get("reasoning_chain"), d.get("sources"), d.get("alternatives"), d.get("execution_time_ms", 0), d.get("degradation_note"))
        except Exception: pass
        return None
