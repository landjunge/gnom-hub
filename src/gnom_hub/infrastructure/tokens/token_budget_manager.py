# token_budget_manager.py — Track operational cost and enforce token limits
from typing import List
from gnom_hub.infrastructure.tokens.tbm_pricing import MODEL_PRICING
from gnom_hub.infrastructure.tokens.tbm_init import init_tables
import gnom_hub.infrastructure.tokens.tbm_record as tr
import gnom_hub.infrastructure.tokens.tbm_stats as ts
import gnom_hub.infrastructure.tokens.tbm_middleware as tm
from gnom_hub.infrastructure.tokens.tbm_middleware import TokenBudgetMiddleware

class TokenBudgetManager:
    def __init__(self, db=None, daily_limit_usd: float = 5.0):
        self.db = db
        self.daily_limit_usd = daily_limit_usd
        init_tables()

    async def require_confirmation(self, estimated_cost: float, reason: str) -> bool:
        return await tm.require_confirmation(estimated_cost, reason)

    async def record_operation(self, operation_id: str, agent: str, operation_type: str, input_tokens: int, output_tokens: int, model: str) -> float:
        return await tr.record_operation(self, operation_id, agent, operation_type, input_tokens, output_tokens, model)

    def get_budget_status(self) -> dict:
        return ts.get_budget_status(self.daily_limit_usd)

    def get_agent_usage(self, agent: str, days: int = 7) -> dict:
        return ts.get_agent_usage(agent, days)

    def get_recent_alerts(self) -> List[dict]:
        return ts.get_recent_alerts()

    def acknowledge_alert(self, alert_id: str):
        ts.acknowledge_alert(alert_id)
