# graceful_degradation.py — Graceful degradation fallback executor and health monitor
import asyncio
from typing import Callable, Tuple, Optional
from gnom_hub.resilience.gd_init import init_tables
import gnom_hub.resilience.gd_online as go
import gnom_hub.resilience.gd_fallback as gf
import gnom_hub.resilience.gd_reports as gr
import gnom_hub.resilience.gd_test as gt

class GracefulDegradationManager:
    def __init__(self, db=None, agent_health_checker=None):
        self.db = db
        self.agent_health_checker = agent_health_checker
        self.simulated_failures = set()
        init_tables()

    def is_online(self, agent: str) -> bool:
        return go.is_online(self, agent)

    async def execute_with_fallback(self, agent: str, task: str, executor: Callable) -> Tuple[str, bool, Optional[str]]:
        return await gf.execute_with_fallback(self, agent, task, executor)

    def get_failure_report(self, agent: Optional[str] = None, days: int = 7) -> list:
        return gr.get_failure_report(agent, days)

    def get_degradation_report(self) -> dict:
        return gr.get_degradation_report()

    async def simulate_agent_failure(self, agent: str):
        await gt.simulate_agent_failure(self, agent)

    async def test_all_fallbacks(self) -> dict:
        return await gt.test_all_fallbacks(self)
