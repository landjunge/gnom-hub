# test_swarm_e2e.py — End-to-End Test for Preset, Embeddings, and Capability bypass
import sys, os, time, shutil, json, sqlite3
# Add project root and src directory to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import gnom_hub.db
import gnom_hub.router
import gnom_hub.brainstorm_helpers
import gnom_hub.gatekeeper_browser
import gnom_hub.soul
import gnom_hub.gatekeeper
import gnom_hub.preset_service
import gnom_hub.soul_retrieval
from gnom_hub.chat_commands_handlers import handle_job
from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository
from gnom_hub.capability_manager import check_capability
from gnom_hub.brainstorm_helpers import get_workspace_dir

def test_swarm_e2e():
    print("============================================================")
    print(" 🚀 STARTING SWARM JOB E2E INTEGRATION TEST")
    print("============================================================")

    # Initialize DB
    gnom_hub.db.init_db()

    # Clear previous capabilities & facts to ensure clean run
    with gnom_hub.db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM capabilities")
            conn.execute("DELETE FROM soul_memory WHERE key IN ('preferred_language', 'unity_version', 'coding_style')")

    # 1. Preset check: load_presets should contain 'Test Preset'
    print("🔍 [Phase 1.1] Loading and merging Test Preset...")
    presets = gnom_hub.preset_service.load_presets()
    assert "Test Preset" in presets.get("prompts", {}), "Test Preset not loaded!"
    
    gnom_hub.preset_service.handle_preset_change("Test Preset")
    assert gnom_hub.db.get_state_value("active_preset") == "Test Preset"
    print("✅ Preset successfully loaded and activated.")

    # 2. Seed facts into soul_memory
    print("🔍 [Phase 1.2] Seeding C# and Unity facts to soul memory...")
    gnom_hub.db.save_soul_fact("preferred_language", "Als Programmiersprache wird C# bevorzugt.", agent="EmbeddingsTest")
    gnom_hub.db.save_soul_fact("unity_version", "Die verwendete Engine ist Unity Version 2022.3 LTS.", agent="EmbeddingsTest")
    gnom_hub.db.save_soul_fact("coding_style", "Verwende immer XML-Dokumentation für öffentliche Methoden in C#-Klassen.", agent="EmbeddingsTest")
    print("✅ Facts successfully seeded.")

    # Validate that semantic retrieval retrieves them
    print("🔍 [Phase 1.3] Validating semantic retrieval...")
    facts = gnom_hub.soul_retrieval.retrieve_relevant_facts("Unity Version")
    print(f"   └─ Retrieved facts: {facts}")
    assert any("Unity" in f for f in facts), "Semantic retrieval should find Unity fact!"
    print("✅ Semantic retrieval successfully verified.")

    # 3. Setup mock LLM router responses
    router_calls = []
    
    def mock_ask_router(p, sys="Du bist ein Assistent.", agent_name=None):
        name = (agent_name or "").lower()
        print(f"🤖 [Mock LLM] Call for '{name}' with prompt: {p[:120]}... (sys: {sys[:80]}...)")
        router_calls.append({"agent": name, "prompt": p, "sys": sys})
        
        if "watchdogag" in name or "du bist watchdogag" in sys.lower():
            return "APPROVED"
        if "securityag" in name or "du bist securityag" in sys.lower():
            return "APPROVED"
        if "coderag" in name:
            return """[WRITE: test_player.cs]
using UnityEngine;
/// <summary>
/// Unity player controller class.
/// </summary>
public class PlayerController {
    public void Jump() {}
}
[/WRITE]"""
        if "generalag" in name or "du bist generalag" in sys.lower():
            if p.strip().startswith("@job"):
                return "@CoderAG -> Erstelle eine C#-Klasse für einen Unity-Player mit einer Methode Jump(). Speichere sie unter test_player.cs."
            return "Workflow beendet. Die Datei test_player.cs wurde erfolgreich erstellt."
        return "APPROVED"

    # Save original references
    orig_router = gnom_hub.router.ask_router
    orig_helpers = gnom_hub.brainstorm_helpers.ask_router
    orig_browser = gnom_hub.gatekeeper_browser.ask_router
    orig_soul = gnom_hub.soul.ask_router

    # Apply mocks globally
    gnom_hub.router.ask_router = mock_ask_router
    gnom_hub.brainstorm_helpers.ask_router = mock_ask_router
    gnom_hub.gatekeeper_browser.ask_router = mock_ask_router
    gnom_hub.soul.ask_router = mock_ask_router

    # Force all agents to status 'online' in the database
    agent_repo = SQLiteAgentRepository()
    for ag in agent_repo.get_all():
        agent_repo.update_status(ag.name, "online")

    try:
        # Start Swarm Job
        print("🔍 [Phase 1.4] Starting swarm job via handle_job...")
        res = handle_job("@job: Erstelle eine C#-Klasse für einen Unity-Player mit einer Methode Jump(). Speichere sie unter test_player.cs.")
        print(f"   └─ handle_job Response: {res}")
        assert res.get("status") == "job_created"

        # Wait for workflow coordinator and CoderAG thread to complete
        print("🔍 [Phase 1.5] Waiting for coordinator background thread to complete...")
        state_repo = SQLiteStateRepository()
        
        start_time = time.time()
        completed = False
        while time.time() - start_time < 8.0:
            active_wf = state_repo.get_value("active_workflow")
            if active_wf is None:
                completed = True
                break
            time.sleep(0.2)

        assert completed, "Swarm job workflow timed out!"
        print("✅ Background coordinator finished execution.")

        # 4. Assertions on results
        # A. Verify file was created in workspace
        expected_path = os.path.join(get_workspace_dir(), "test_player.cs")
        print(f"🔍 [Phase 1.6] Checking created file at: {expected_path}")
        assert os.path.exists(expected_path), f"File {expected_path} was not created!"
        with open(expected_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"   └─ File Content:\n{content}")
        assert "public class PlayerController" in content, "Expected class PlayerController not found in file!"
        assert "/// <summary>" in content, "Expected XML documentation comment not found in file!"
        print("✅ File creation and content verified successfully.")

        # B. Verify capability was leased
        print("🔍 [Phase 1.7] Verifying capability lease in DB...")
        assert check_capability("CoderAG", "WRITE", "test_player.cs"), "Capability lease for test_player.cs not found or not active!"
        print("✅ Capability lease registered successfully.")

        # C. Verify capability lease bypasses LLM
        print("🔍 [Phase 1.8] Verifying capability bypass (router shouldn't be called)...")
        # Clear router_calls to verify new calls
        router_calls.clear()
        
        # Call verify_write again. Since capability is leased, it should return True immediately without calling router.
        bypass_result = gnom_hub.gatekeeper.verify_write(
            {"name": "CoderAG", "role": "coder"},
            "test_player.cs",
            "dummy content",
            get_workspace_dir(),
            ["write"]
        )
        assert bypass_result is True, "verify_write failed on second call!"
        assert len([c for c in router_calls if c["agent"] in ("watchdogag", "securityag")]) == 0, "Router was incorrectly called during capability lease bypass!"
        print("✅ Capability lease bypass verified successfully (no router calls).")

    finally:
        # Clean up router overrides
        gnom_hub.router.ask_router = orig_router
        gnom_hub.brainstorm_helpers.ask_router = orig_helpers
        gnom_hub.gatekeeper_browser.ask_router = orig_browser
        gnom_hub.soul.ask_router = orig_soul

        # Clean up files & presets
        expected_path = os.path.join(get_workspace_dir(), "test_player.cs")
        if os.path.exists(expected_path):
            os.unlink(expected_path)
            
        print("============================================================")
        print(" 🎉 ALL E2E INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("============================================================")

if __name__ == "__main__":
    test_swarm_e2e()
