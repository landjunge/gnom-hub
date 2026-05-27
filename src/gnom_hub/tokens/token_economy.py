# token_economy.py — Token cost budgeting and spending guardrails
import asyncio
from typing import List
from gnom_hub.database.legacy_db import add_chat_message

PRICE_PER_1K_TOKENS = 0.002  # $0.002 per 1k tokens
EXPENSIVE_THRESHOLD = 0.05    # Set threshold low ($0.05) to trigger confirmations easily

def estimate_tokens(text: str) -> int:
    """Estimates token count using a simple word count multiplier."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, int(words * 1.3) if words > 0 else len(text) // 4)

def count_tokens(text: str) -> int:
    return estimate_tokens(text)

class Alert:
    def __init__(self, message: str):
        self.message = message

    def __repr__(self):
        return f"<Alert msg='{self.message}'>"

async def user_confirm(message: str):
    """Simulates user confirmation with logs."""
    print(f"[TokenEconomy] User confirmation prompt: {message}")
    await asyncio.sleep(0.01)

async def alert_user(message: str):
    """Sends warning alerts to the user chat."""
    print(f"[TokenEconomy] ALERT: {message}")
    add_chat_message("default", "System", "system", "chat", f"⚠️ Budget-Warnung: {message}")

class TokenBudgetAgent:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, prompt: str):
        from gnom_hub.router import ask_router
        eo = await asyncio.to_thread(ask_router, prompt, agent_name=self.name)
        
        # Return an object that has a .completion attribute
        class AgentResponse:
            def __init__(self, text: str):
                self.completion = text
        return AgentResponse(eo.content)

class TokenBudget:
    def __init__(self, daily_limit: float = 100_000):
        self.daily_limit = daily_limit  # Budget limit (can represent tokens or cost)
        self.spent_today = 0.0
        self.alerts: List[Alert] = []

    async def execute_with_budget(self, agent, prompt: str):
        # Resolve agent to TokenBudgetAgent if string is passed
        run_agent = TokenBudgetAgent(agent) if isinstance(agent, str) else agent

        estimated_cost = (estimate_tokens(prompt) / 1000.0) * PRICE_PER_1K_TOKENS
        
        if estimated_cost > EXPENSIVE_THRESHOLD:
            await user_confirm(
                f"Operation kostet ~${estimated_cost:.05f}. Fortfahren?"
            )
        
        result = await run_agent.execute(prompt)
        actual_cost = (count_tokens(result.completion) / 1000.0) * PRICE_PER_1K_TOKENS
        self.spent_today += actual_cost
        
        if self.spent_today > self.daily_limit * 0.8:
            msg = f"80% tägliches Budget verbraucht: ${self.spent_today:.05f}"
            self.alerts.append(Alert(msg))
            await alert_user(msg)
        
        return result
