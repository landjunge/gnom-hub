# test_additional_systems.py — Tests project planner, explainability, fallbacks, token budget, and velocity systems
import sys, os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
import gnom_hub.router
import gnom_hub.graceful_fallback
import gnom_hub.token_economy

# Imports of new classes
from gnom_hub.project_planner import ProjectPlan, Step
from gnom_hub.explainability import ExplainableOutput
from gnom_hub.specialization_monitor import monitor_drift
from gnom_hub.graceful_fallback import execute_with_fallback, FallbackAgent, AgentUnavailableError, AllAgentsFailedError
from gnom_hub.token_economy import TokenBudget
from gnom_hub.team_velocity import VelocityMetric

async def test_project_planner():
    print("\n--- TESTING PROJECT PLANNER ---")
    # Step 1: CoderAG implements landing page (duration 10)
    # Step 2: WriterAG writes content (duration 15), depends on Step 1
    # Step 3: EditorAG reviews text (duration 5), depends on Step 2
    # Step 4: ResearcherAG studies market (duration 8), independent
    s1 = Step("s1", "Implement landing page", "CoderAG", [], 10, "blocker")
    s2 = Step("s2", "Write landing page content", "WriterAG", ["s1"], 15, "important")
    s3 = Step("s3", "Review landing page text", "EditorAG", ["s2"], 5, "nice_to_have")
    s4 = Step("s4", "Market research", "ResearcherAG", [], 8, "nice_to_have")
    
    plan = ProjectPlan("p1", "Marketing Launch", [s1, s2, s3, s4])
    
    # Calculate critical path: s1 -> s2 -> s3 (Total duration 30)
    cp = plan.calculate_critical_path()
    print(f"Critical Path: {[s.id for s in cp]}")
    assert len(cp) == 3
    assert cp[0].id == "s1"
    assert cp[1].id == "s2"
    assert cp[2].id == "s3"

    # Execute plan. Verify N+2 lookahead works:
    # While executing s1, s3 should be prepped in parallel!
    await plan.execute_with_lookahead()
    assert "s3" in plan.lookahead_prepped
    assert "s1" in plan.executed_steps
    assert "s2" in plan.executed_steps
    assert "s3" in plan.executed_steps
    assert "s4" in plan.executed_steps
    print("Project planner verified successfully!")

def test_explainability():
    print("\n--- TESTING EXPLAINABILITY ---")
    exp = ExplainableOutput(
        primary_answer="Die Antwort lautet 42.",
        confidence=0.92,
        reasoning_chain=["Analysiere Frage", "Lese Handbuch", "Berechne Antwort"],
        alternatives=[
            {"answer": "Die Antwort lautet 43.", "score": 0.45, "why_not": "Ein Rechenfehler lag vor."},
            {"answer": "Die Antwort lautet unbekannt.", "score": 0.10, "why_not": "Zu pessimistisch."}
        ],
        sources=["fact_soul_1", "fact_soul_2"],
        agent_uncertainty="Unsicher über den genauen Textbezug."
    )
    
    rendered = exp.render_for_user()
    print(f"Rendered Output:\n{rendered}")
    assert "Die Antwort lautet 42." in rendered
    assert "Zuversicht:** 92%" in rendered
    assert "Analysiere Frage → Lese Handbuch → Berechne Antwort" in rendered
    assert "fact_soul_1, fact_soul_2" in rendered
    assert "Die Antwort lautet 43. (45%) — Ein Rechenfehler lag vor." in rendered
    print("Explainable output verified successfully!")

async def test_specialization_drift():
    print("\n--- TESTING SPECIALIZATION DRIFT MONITOR ---")
    gnom_hub.db.init_db()
    # WriterAG has copywriting = 0.92, documentation = 0.45, editing = 0.88
    # Drift is 0.92 - 0.45 = 0.47 > 0.3. This should trigger an escalation chat message!
    
    # Let's count messages before and after
    with gnom_hub.db.get_db_conn() as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = 'system'").fetchone()[0]

    await monitor_drift()

    with gnom_hub.db.get_db_conn() as conn:
        count_after = conn.execute("SELECT COUNT(*) FROM chat WHERE agent_id = 'system'").fetchone()[0]

    assert count_after > count_before
    print("Specialization drift monitor escalation verified successfully!")

async def test_graceful_fallback():
    print("\n--- TESTING GRACEFUL FALLBACK ---")
    # Mock estimate_quality to return high confidence
    original_ask_router = gnom_hub.router.ask_router
    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        if "Qualität" in p:
            return "0.85"
        return "Mock execution result"
    gnom_hub.router.ask_router = mock_ask_router
    gnom_hub.graceful_fallback.ask_router = mock_ask_router

    try:
        # Create an offline agent CoderAG
        offline_coder = FallbackAgent("CoderAG")
        
        # Verify it raises AgentUnavailableError if we call execute directly
        # since it resolves to offline in mock metrics or status is offline
        # Let's simulate offline status in get_agent_metrics
        original_metrics = gnom_hub.graceful_fallback.get_agent_metrics
        gnom_hub.graceful_fallback.get_agent_metrics = lambda: {"coderag": {"status": "offline"}}
        
        try:
            await offline_coder.execute("Build web app")
            assert False, "Should have raised AgentUnavailableError"
        except AgentUnavailableError:
            pass

        # Now test fallback. GeneralAG is online.
        gnom_hub.graceful_fallback.get_agent_metrics = lambda: {
            "coderag": {"status": "offline"},
            "generalag": {"status": "online"},
            "writerag": {"status": "online"}
        }

        # Run execute_with_fallback. CoderAG falls back to GeneralAG (pseudocode)
        res = await execute_with_fallback("CoderAG", "Build web app")
        print(f"Fallback Result:\n{res}")
        assert "degradation_note" in dir(res)
        assert "Note: CoderAG was unavailable, GeneralAG (pseudocode) handled this instead." in res.degradation_note
        assert res.completion == "Mock execution result"

        print("Graceful fallback verified successfully!")
    finally:
        gnom_hub.router.ask_router = original_ask_router
        gnom_hub.graceful_fallback.ask_router = original_ask_router

async def test_token_economy():
    print("\n--- TESTING TOKEN ECONOMY ---")
    # Mock ask_router to return simple prompt execution
    original_ask_router = gnom_hub.router.ask_router
    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        return "Skript abgeschlossen."
    gnom_hub.router.ask_router = mock_ask_router
    gnom_hub.token_economy.ask_router = mock_ask_router

    try:
        # 1. Initialize budget with a low daily limit (in cost)
        # e.g., daily_limit = 0.000002 USD cost
        budget = TokenBudget(daily_limit=0.000002)
        
        # Execute prompt that spends some budget
        prompt = "Write long documentation detailing code implementation rules."
        res = await budget.execute_with_budget("CoderAG", prompt)
        
        print(f"Token economy spent: {budget.spent_today:.6f} USD")
        assert budget.spent_today > 0.0
        # Verify alert was generated because spent_today exceeded daily_limit * 0.8
        assert len(budget.alerts) > 0
        assert "80% tägliches Budget verbraucht" in budget.alerts[0].message
        
        print("Token economy budget tracking verified successfully!")
    finally:
        gnom_hub.router.ask_router = original_ask_router
        gnom_hub.token_economy.ask_router = original_ask_router

def test_team_velocity():
    print("\n--- TESTING TEAM VELOCITY METRIC ---")
    # Bottleneck 1: Critical path overhead > 0.3
    v1 = VelocityMetric(
        jobs_completed_per_day=5,
        avg_duration_per_job=25.0,
        agent_utilization={"CoderAG": 0.8, "WriterAG": 0.5},
        critical_path_overhead=0.4
    )
    b1 = v1.identify_bottleneck()
    print(f"Bottleneck 1: {b1}")
    assert b1 == "Parallelization issue — jobs wait for predecessors"

    # Bottleneck 2: WriterAG underutilization < 0.2
    v2 = VelocityMetric(
        jobs_completed_per_day=10,
        avg_duration_per_job=12.5,
        agent_utilization={"CoderAG": 0.9, "WriterAG": 0.15},
        critical_path_overhead=0.1
    )
    b2 = v2.identify_bottleneck()
    print(f"Bottleneck 2: {b2}")
    assert b2 == "WriterAG underutilized — consider reassigning tasks"
    
    print("Team velocity metrics verified successfully!")

async def main():
    await test_project_planner()
    test_explainability()
    await test_specialization_drift()
    await test_graceful_fallback()
    await test_token_economy()
    test_team_velocity()
    print("\nAll additional systems successfully verified!")

if __name__ == "__main__":
    asyncio.run(main())
