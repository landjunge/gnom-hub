# tests/test_gnom_hub.py — Relational & Security Integration Tests for Gnom-Hub
import sys
import os
import pytest

# Ensure the src directory and project root are in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db.legacy_db as db
from gnom_hub.core.security.gatekeeper import is_command_safe_and_whitelisted
from gnom_hub.memory.soul_retrieval import retrieve_relevant_facts

@pytest.fixture(autouse=True)
def setup_db():
    """Idempotently initialize and clean up the database state before each test."""
    # Reset FAISS embeddings singleton and cache files to avoid cross-test contamination
    import glob
    import gnom_hub.memory.embeddings as emb
    emb._instance = None
    for f in glob.glob("data/soul_embeddings_*.index") + glob.glob("data/soul_fact_ids_*.pkl"):
        try:
            os.remove(f)
        except OSError:
            pass

    db.init_db()
    with db.get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM agents WHERE name = 'TestCoder'")
            conn.execute("DELETE FROM chat WHERE project = 'test_project'")
            conn.execute("DELETE FROM soul_memory WHERE key = 'test_key'")

def test_database_initialization():
    """Verify that database connections and tables are properly configured."""
    with db.get_db_conn() as conn:
        # Check WAL mode and foreign keys are on
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert journal_mode.lower() == "wal"
        assert fk == 1

def test_agent_registration_and_status():
    """Test registering a mock agent and updating its status/role in the DB."""
    # Register TestCoder agent
    agent = db.register_agent_in_db("TestCoder", 9999, "A mock coder for tests")
    assert agent is not None
    assert agent["name"] == "TestCoder"
    assert agent["status"] == "online"
    
    # Update status to paused
    updated = db.set_agent_status("TestCoder", "paused")
    assert updated["status"] == "paused"
    
    # Update role to general
    role_updated = db.set_agent_role("TestCoder", "general")
    assert role_updated["role"] == "general"
    
    # Cleanup agent
    db.delete_agent_by_id(agent["id"])

def test_chat_message_persistence():
    """Verify that chat messages are correctly saved and queried relational."""
    msg_id = db.add_chat_message("test_project", "TestUser", "coderag", "chat", "Hello world from integration test")
    assert msg_id is not None
    
    history = db.get_chat_history("test_project", limit=5)
    assert len(history) == 1
    assert history[0]["content"] == "Hello world from integration test"
    assert history[0]["sender"] == "TestUser"
    
    db.delete_memory_by_id(msg_id)

def test_soul_memory_retrieval():
    """Test saving a fact to soul memory and retrieving it via retrieve_relevant_facts."""
    # Seed fact
    db.save_soul_fact("test_key", "Gnom-Hub uses local FAISS indices for embeddings.", agent="System", priority="high")
    
    # Retrieve facts (query > 10 chars to bypass short checks)
    facts = retrieve_relevant_facts("Where does Gnom-Hub save embeddings?")
    assert any("FAISS" in f for f in facts)

def test_command_whitelisting_security():
    """Verify that safe commands are allowed and dangerous commands are rejected by the gatekeeper."""
    # Pre-approved command
    safe, reason = is_command_safe_and_whitelisted("python3 scratch/run_all_tests.py")
    assert safe is True
    
    # Non-whitelisted base executable
    unsafe1, reason1 = is_command_safe_and_whitelisted("sudo apt-get update")
    assert unsafe1 is False
    assert "nicht auf der Whitelist" in reason1
    
    # Dangerous rm targeting root
    unsafe2, reason2 = is_command_safe_and_whitelisted("rm -rf /")
    assert unsafe2 is False
    assert "nicht auf der Whitelist" in reason2 or "nicht erlaubt" in reason2

def test_merken_and_spass_commands():
    """Verify that @merken and @spass chat commands work as intended."""
    from fastapi.testclient import TestClient
    from gnom_hub.api.app import app
    from gnom_hub.db.legacy_db import get_state_value, get_db_conn, register_agent_in_db, delete_agent_by_id
    
    # Register mock CoderAG so that get_all_agents inside the command handler finds it
    mock_coder = register_agent_in_db("CoderAG", 9992, "mock coder")
    
    client = TestClient(app)
    try:
        # 1. Test @merken
        res = client.post("/api/chat", json={"content": "Wichtige Information: DNS ist 8.8.8.8 @merken", "sender": "user"})
        assert res.status_code == 200
        assert res.json()["status"] == "saved"
        
        # Check that it is saved in soul_memory
        with get_db_conn() as conn:
            row = conn.execute("SELECT value FROM soul_memory WHERE value LIKE '%DNS ist 8.8.8.8%'").fetchone()
            assert row is not None
            assert "DNS ist 8.8.8.8" in row["value"]
            
        # 2. Test @spass
        res_spass = client.post("/api/chat", json={"content": "@spass", "sender": "user"})
        assert res_spass.status_code == 200
        assert res_spass.json()["status"] == "ok"
        
        # Verify settings are adjusted
        settings = get_state_value("agent_settings", {})
        assert settings is not None
        coder_set = settings.get("coderag", {})
        assert coder_set.get("personality") == 5
        assert coder_set.get("creativity") == 5
        assert "Humor" in coder_set.get("custom_prompt", "")

        # 3. Test @spass off / @spass ende
        res_spass_off = client.post("/api/chat", json={"content": "@spass ende", "sender": "user"})
        assert res_spass_off.status_code == 200
        assert res_spass_off.json()["status"] == "ok"
        
        # Verify settings are reset to standard
        settings_off = get_state_value("agent_settings", {})
        assert settings_off is not None
        coder_set_off = settings_off.get("coderag", {})
        assert coder_set_off.get("personality") == 3
        assert coder_set_off.get("creativity") == 3
        assert "Humor" not in coder_set_off.get("custom_prompt", "")
    finally:
        delete_agent_by_id(mock_coder["id"])

def test_worker_command():
    """Verify that @worker chat command works as intended."""
    from fastapi.testclient import TestClient
    from gnom_hub.api.app import app
    from gnom_hub.db.legacy_db import register_agent_in_db, delete_agent_by_id
    
    # Register mock worker agent to be online
    mock_coder = register_agent_in_db("CoderAG", 9991, "mock coder")
    
    client = TestClient(app)
    try:
        res = client.post("/api/chat", json={"content": "@worker -> baue eine webseite", "sender": "user"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "dispatched"
        assert "CoderAG" in data["asked"]
        assert data["mode"] == "worker"
    finally:
        delete_agent_by_id(mock_coder["id"])

