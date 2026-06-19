# tbm_middleware.py
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

async def require_confirmation(estimated_cost: float, reason: str) -> bool:
    print(f"[BudgetManager] Confirmation required: {reason} (Estimated cost: ${estimated_cost:.5f})")
    await asyncio.sleep(0.01)
    return True

class TokenBudgetMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, budget_manager):
        super().__init__(app)
        self.budget_manager = budget_manager
    async def dispatch(self, request: Request, call_next):
        return await call_next(request)
