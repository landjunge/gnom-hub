# test_conflict_resolution.py — Tests conflict resolution flow
import sys, os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.router
from gnom_hub.conflict_resolver import ConflictResolution

async def test_conflict_resolution():
    print("--- TESTING CONFLICT RESOLUTION ---")

    # Mock ask_router calls to guide the debate and final voting
    import gnom_hub.conflict_resolver
    original_ask_router = gnom_hub.router.ask_router
    call_sequence = []

    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        call_sequence.append((agent_name, p))
        if "Analysiere diese zwei Outputs" in p:
            return "Difference: Agent 1 uses camelCase, Agent 2 uses snake_case."
        elif "Warum divergieren diese Outputs" in p:
            return "Drift: CoderAG got a python-centric prompt, WriterAG got a JS-centric prompt."
        elif "repräsentierst Agent 1" in p:
            return "Agent 1 Argument: camelCase is standard in JS/TS frontend code."
        elif "repräsentierst Agent 2" in p:
            return "Agent 2 Argument: snake_case is standard in Python backend code."
        elif "neutraler Richter" in p:
            # Return valid JSON representation matching requested winner
            return """
            {
                "winner": "CoderAG",
                "confidence": 0.95,
                "reasoning": "Tasks is JS landing page, so CoderAG JS standard wins.",
                "consensus_output": "const userName = 'Gnom';"
            }
            """
        return "Mock default response"

    gnom_hub.router.ask_router = mock_ask_router
    gnom_hub.conflict_resolver.ask_router = mock_ask_router

    try:
        resolver = ConflictResolution()
        res = await resolver.resolve_divergence(
            agent1_output="const userName = 'Gnom';",
            agent2_output="user_name = 'Gnom'",
            task="Erstelle Variable für Landingpage"
        )
        
        print(f"Conflict Resolution Result:\n{res}")
        
        assert res["winner"] == "CoderAG"
        assert res["confidence"] == 0.95
        assert "JS standard wins" in res["reasoning"]
        assert "const userName" in res["consensus_output"]
        
        # Verify the sequence of calls
        assert len(call_sequence) == 5
        print("\nAll 5 steps in divergence resolution flow executed successfully!")
        
    finally:
        gnom_hub.router.ask_router = original_ask_router
        gnom_hub.conflict_resolver.ask_router = original_ask_router

if __name__ == "__main__":
    asyncio.run(test_conflict_resolution())
