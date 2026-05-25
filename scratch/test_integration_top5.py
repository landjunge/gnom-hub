# test_integration_top5.py — Verification of all 5 integration managers
import sys, os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
import gnom_hub.router
import gnom_hub.graceful_degradation
import gnom_hub.gd_fallback

# Import top 5 modules
from gnom_hub.prompt_version_manager import PromptVersionManager
from gnom_hub.semantic_memory_retriever import SemanticMemoryRetriever
from gnom_hub.explainable_output import ExplainableOutputBuilder, ExplainableOutputFormatter, ExplainableOutputStore
from gnom_hub.token_budget_manager import TokenBudgetManager
from gnom_hub.graceful_degradation import GracefulDegradationManager

async def test_all_integrations():
    print("--- STARTING TOP 5 INTEGRATION TESTS ---")
    gnom_hub.db.init_db()

    # ========================================================================
    # 1. Test PromptVersionManager
    # ========================================================================
    print("\n[Test 1] Testing PromptVersionManager...")
    pvm = PromptVersionManager()
    
    # Clean previous
    with gnom_hub.db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM prompt_versions WHERE agent = 'WriterAG'")

    # Create prompt v1
    v1 = pvm.create_version("WriterAG", "Direct copy, focus on emotional tags.", ["Copywriting v1"])
    pvm.activate_version("WriterAG", v1.id)
    assert v1.parent_id is None
    
    # Create prompt v2 (evolved)
    v2 = pvm.create_version("WriterAG", "Direct copy, focus on emotional tags. Focus on landing page H2.", ["Copywriting v1", "Add landing H2"])
    assert v2.parent_id == v1.id

    pvm.activate_version("WriterAG", v2.id)
    pvm.record_test_result(v2.id, success=False)  # record fail score goes down to 0.0

    history = pvm.get_version_history("WriterAG", limit=5)
    assert len(history) >= 2
    
    # Auto-rollback should be triggered because v2 score (0.0) < v1 score (1.0) * 0.95
    if pvm.should_rollback("WriterAG", v2.id, v1.id):
        pvm.auto_rollback("WriterAG", v1.id)

    # Compare versions
    diff = pvm.compare_versions(v1.id, v2.id)
    assert "Add landing H2" in diff["added_rules"]
    print("PromptVersionManager verified successfully!")

    # ========================================================================
    # 2. Test SemanticMemoryRetriever
    # ========================================================================
    print("\n[Test 2] Testing SemanticMemoryRetriever...")
    smr = SemanticMemoryRetriever()
    
    # Seed memories
    with gnom_hub.db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM soul_memory WHERE agent = 'SemanticTest'")
    
    gnom_hub.db.add_to_soul_memory("Das Design-System ist blau.", priority="medium", agent="SemanticTest")
    gnom_hub.db.add_to_soul_memory("Die DB verwendet SQLite.", priority="high", agent="SemanticTest")

    # Query matching
    res = await smr.retrieve_similar("SQLite Datenbank Konfiguration", top_k=5)
    print(f"Similarity results: {res}")
    assert any("SQLite" in x for x in res)

    # Fallback checking
    fallback_res = await smr.retrieve_with_fallback("Apfelkuchen Rezept", top_k=2)
    print(f"Fallback results: {fallback_res}")
    assert len(fallback_res) > 0

    # Pruning stats
    stats = smr.get_memory_stats()
    assert stats["total_facts"] > 0
    print("SemanticMemoryRetriever verified successfully!")

    # ========================================================================
    # 3. Test ExplainableOutput
    # ========================================================================
    print("\n[Test 3] Testing ExplainableOutput...")
    store = ExplainableOutputStore()
    
    builder = ExplainableOutputBuilder("CoderAG", "Generate auth middleware")
    builder.set_answer("class AuthMiddleware: pass")
    builder.set_confidence(0.95)
    builder.add_reasoning("Parsed request").add_reasoning("Created basic structure")
    builder.add_source("db_sqlite", "sqlite_conn")
    builder.add_alternative("Functional check", 0.60, "Less reusable")
    builder.set_execution_time(1500)
    
    output = builder.build()
    output_id = store.store(output)
    
    loaded = store.get(output_id)
    assert loaded is not None
    assert loaded.agent == "CoderAG"
    assert loaded.confidence == 0.95
    assert len(loaded.reasoning_chain) == 2

    # Render formats
    md = ExplainableOutputFormatter.to_markdown(loaded)
    json_str = ExplainableOutputFormatter.to_json(loaded)
    html_str = ExplainableOutputFormatter.to_html(loaded)
    assert "AuthMiddleware" in md
    assert "functional check" in json_str.lower()
    assert "explainable-output-card" in html_str
    print("ExplainableOutput verified successfully!")

    # ========================================================================
    # 4. Test TokenBudgetManager
    # ========================================================================
    print("\n[Test 4] Testing TokenBudgetManager...")
    
    # Clean previous budget records
    with gnom_hub.db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM token_budget_logs")
            conn.execute("DELETE FROM token_budget_alerts")

    # Low limit $0.0001
    budget_mgr = TokenBudgetManager(daily_limit_usd=0.0001)
    
    # record expensive operation
    cost = await budget_mgr.record_operation(
        operation_id="op_test_1",
        agent="CoderAG",
        operation_type="test_call",
        input_tokens=5000,
        output_tokens=8000,
        model="gpt-4-turbo"
    )
    print(f"Recorded cost: ${cost:.5f}")
    assert cost > 0.0
    
    status = budget_mgr.get_budget_status()
    print(f"Budget Status: {status}")
    assert status["spent_today"] > 0.0

    # Verify alert was generated
    alerts = budget_mgr.get_recent_alerts()
    assert len(alerts) > 0
    
    # Acknowledge alert
    alert_id = alerts[0]["id"]
    budget_mgr.acknowledge_alert(alert_id)
    assert len(budget_mgr.get_recent_alerts()) == 0
    print("TokenBudgetManager verified successfully!")

    # ========================================================================
    # 5. Test GracefulDegradationManager
    # ========================================================================
    print("\n[Test 5] Testing GracefulDegradationManager...")
    
    # Ensure backups and agents are considered online by resetting last_seen
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with gnom_hub.db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM graceful_degradation_failures")
            conn.execute("UPDATE agents SET last_seen = ?, status = 'online'", (now_str,))

    degradation_mgr = GracefulDegradationManager()
    
    # Mock router to return quality
    original_ask_router = gnom_hub.router.ask_router
    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        if "Qualität" in p:
            return "0.90"
        return "Consensus answer"
    gnom_hub.router.ask_router = mock_ask_router
    gnom_hub.gd_fallback.gnom_hub.router.ask_router = mock_ask_router

    try:
        # Simulate CoderAG failure
        await degradation_mgr.simulate_agent_failure("CoderAG")
        
        # Verify execute_with_fallback routes to GeneralAG backup
        result, success, fb_used = await degradation_mgr.execute_with_fallback(
            agent="CoderAG",
            task="Refactor codebase",
            executor=lambda: "CoderAG successful response (should be offline)"
        )
        
        print(f"Degradation result: {result} | success: {success} | fallback: {fb_used}")
        assert success is True
        assert fb_used == "GeneralAG"
        assert result == "Consensus answer"
        
        # Verify failure report logs
        report = degradation_mgr.get_failure_report("CoderAG")
        assert len(report) > 0
        assert report[0]["fallback_agent"] == "GeneralAG"
        
        # Verify degradation summary report counts
        summary = degradation_mgr.get_degradation_report()
        assert summary.get("CoderAG", 0) > 0
        print("GracefulDegradationManager verified successfully!")
    finally:
        gnom_hub.router.ask_router = original_ask_router
        gnom_hub.gd_fallback.gnom_hub.router.ask_router = original_ask_router

    print("\n--- ALL TOP 5 INTEGRATION TESTS COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    asyncio.run(test_all_integrations())
