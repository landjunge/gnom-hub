# tbm_record.py
import logging
import uuid
from datetime import datetime, timezone

from gnom_hub.db import add_chat_message, get_db_conn
from gnom_hub.infrastructure.tokens.tbm_pricing import MODEL_PRICING


async def record_operation(tbm, op_id: str, agent: str, op_type: str, input_tok: int, output_tok: int, model: str) -> float:
    pricing = MODEL_PRICING.get(model.lower(), {"input": 0.002, "output": 0.002})
    cost = ((input_tok / 1000.0) * pricing["input"]) + ((output_tok / 1000.0) * pricing["output"])
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("INSERT OR REPLACE INTO token_budget_logs (operation_id, agent, operation_type, input_tokens, output_tokens, model, cost, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (op_id, agent, op_type, input_tok, output_tok, model, cost, ts))
    except Exception as e: logging.getLogger(__name__).error('Fehler in Token-Verbrauch-Speicherung: %s', e)
    status = tbm.get_budget_status()
    if status["spent_today"] > tbm.daily_limit_usd * 0.8:
        today_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        alert_exists = False
        try:
            with get_db_conn() as conn:
                row = conn.execute("SELECT COUNT(*) FROM token_budget_alerts WHERE message LIKE ? AND timestamp LIKE ?", ("%80% tägliches Budget%", f"{today_start}%")).fetchone()
                alert_exists = (row[0] > 0)
        except Exception as e: logging.getLogger(__name__).error('Fehler in Budget-Alert-Prüfung: %s', e)
        if not alert_exists:
            alert_msg = f"80% tägliches Budget verbraucht: ${status['spent_today']:.02f}"
            alert_id = str(uuid.uuid4())
            try:
                with get_db_conn() as conn:
                    with conn:
                        conn.execute("INSERT INTO token_budget_alerts (id, message, timestamp) VALUES (?, ?, ?)", (alert_id, alert_msg, ts))
                add_chat_message("default", "System", "system", "chat", f"⚠️ Budget-Warnung: {alert_msg} (Limit: ${tbm.daily_limit_usd:.2f})")
            except Exception as e: logging.getLogger(__name__).error('Fehler in Budget-Alert-Erstellung: %s', e)
    return cost
