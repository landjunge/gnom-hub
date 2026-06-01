#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add src/ to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import gnom_hub.db
from gnom_hub.db.legacy_db import (
    get_all_agents,
    create_agent_record,
    register_agent_in_db,
    set_agent_role
)
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.agents.entities import Agent
from gnom_hub.core.exceptions import ValidationError
from uuid import uuid4

def check_initial_agents():
    agents = get_all_agents()
    print(f"    Current agent count: {len(agents)}")
    assert len(agents) == 8, "Expected exactly 8 seeded agents initially."

def check_create_worker_overflow():
    print("    [Test 1] Adding 5th worker via create_agent_record...")
    try:
        create_agent_record("TestWorkerAG", role="coder")
        assert False, "Should have raised ValidationError for 5th worker agent"
    except ValidationError as e:
        print(f"    ✅ Got expected validation error: {e}")

def check_create_sys_overflow():
    print("    [Test 2] Adding 5th system agent via create_agent_record...")
    try:
        create_agent_record("TestSystemAG", role="watchdog")
        assert False, "Should have raised ValidationError for 5th system agent"
    except ValidationError as e:
        print(f"    ✅ Got expected validation error: {e}")

def check_register_overflow():
    print("    [Test 3] Adding 5th worker via register_agent_in_db...")
    try:
        register_agent_in_db("AnotherWorkerAG", 1234, "Test description")
        assert False, "Should have raised ValidationError for 5th worker agent"
    except ValidationError as e:
        print(f"    ✅ Got expected validation error: {e}")

def check_repo_save_overflow():
    print("    [Test 4] Adding 5th worker via SQLiteAgentRepository.save...")
    repo = SQLiteAgentRepository()
    new_agent = Agent(id=uuid4(), name="RepoWorkerAG", role="coder", status="online")
    try:
        repo.save(new_agent)
        assert False, "Should have raised ValidationError for 5th worker agent"
    except ValidationError as e:
        print(f"    ✅ Got expected validation error: {e}")

def check_valid_role_update():
    print("    [Test 5] Updating existing agent role within same category (should pass)...")
    res = set_agent_role("CoderAG", "editor")
    assert res is not None, "Should allow shifting CoderAG to editor (both worker roles)"
    assert res["role"] == "editor"
    res_restore = set_agent_role("CoderAG", "coder")
    assert res_restore is not None
    assert res_restore["role"] == "coder"
    print("    ✅ Passed role update test.")

def test_limits():
    print("🧪 Running Agent Limit Verification Tests...")
    old = os.environ.get("FORCE_LIMIT_CHECK")
    os.environ["FORCE_LIMIT_CHECK"] = "1"
    try:
        gnom_hub.db.init_db()
        check_initial_agents()
        check_create_worker_overflow()
        check_create_sys_overflow()
        check_register_overflow()
        check_repo_save_overflow()
        check_valid_role_update()
    finally:
        if old is None:
            del os.environ["FORCE_LIMIT_CHECK"]
        else:
            os.environ["FORCE_LIMIT_CHECK"] = old
    print("\n🎉 All agent limit tests PASSED!")

if __name__ == "__main__":
    test_limits()
