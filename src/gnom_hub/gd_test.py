# gd_test.py
import asyncio

async def simulate_agent_failure(mgr, agent: str):
    mgr.simulated_failures.add(agent.lower())
    print(f"[Degradation] Simulated failure active for {agent}")
    await asyncio.sleep(0.01)

async def test_all_fallbacks(mgr) -> dict:
    results = {}
    for agent in ["CoderAG", "WriterAG"]:
        mgr.simulated_failures.add(agent.lower())
        res, success, fb = await mgr.execute_with_fallback(agent=agent, task="Test fallback routing", executor=lambda: "Normal Execution succeeded")
        results[agent] = {"success": success, "fallback_used": fb, "response_received": len(res) > 0}
        mgr.simulated_failures.remove(agent.lower())
    return results
