# test_adaptive_decomposition.py — Tests task decomposition and routing
import sys, os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.infrastructure.router.router as router
import gnom_hub.agents.actions.adaptive_decomposition as adaptive_decomposition
from gnom_hub.agents.actions.adaptive_decomposition import decompose_job

async def test_adaptive_decomposition():
    print("--- TESTING ADAPTIVE DECOMPOSITION ---")

    # Mock ask_router to return a specific complexity (e.g., "8")
    class MockResponse:
        def __init__(self, content):
            self.content = content

    original_ask_router = router.ask_router
    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        if "Komplexität" in p:
            return MockResponse("8")
        return MockResponse("Mock response")

    router.ask_router = mock_ask_router
    adaptive_decomposition.ask_router = mock_ask_router

    try:
        # Test code task (should resolve to Parallel Route A)
        res_code = await decompose_job("Schreibe ein Python-Skript und erstelle eine Landingpage.")
        print(f"Code Task Route:\n{res_code}")
        assert "CoderAG" in res_code["assigned_agents"]
        assert "WriterAG" in res_code["assigned_agents"]
        assert len(res_code["subtasks"]) == 2

        # Test text task (should resolve to Serial Route B)
        res_text = await decompose_job("Schreibe einen Blog-Eintrag.")
        print(f"\nText Task Route:\n{res_text}")
        assert "WriterAG" in res_text["assigned_agents"]
        assert "EditorAG" in res_text["assigned_agents"]
        assert len(res_text["subtasks"]) == 2

        print("\nAdaptive decomposition and routing successfully verified!")

    finally:
        router.ask_router = original_ask_router
        adaptive_decomposition.ask_router = original_ask_router

if __name__ == "__main__":
    asyncio.run(test_adaptive_decomposition())
