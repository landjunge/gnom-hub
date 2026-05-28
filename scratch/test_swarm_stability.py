# test_swarm_stability.py — Test swarm stability, mention depth cascades, and pulse timeout watcher
import sys, os, json, time
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
from gnom_hub.agents.entities import Agent
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.agents.swarm.swarm_comms import process_swarm_mentions
from gnom_hub.infrastructure.pulse import pulse_janitor
from gnom_hub.core.utils.preset_service import handle_preset_change

def check_mention_depth(repo):
    agent_id = "22345678-1234-5678-1234-567812345678"
    a = Agent(
        id=agent_id, name="TestCoderAG", port=0, description="Test",
        status="online", capabilities=["CODER"], role="normal"
    )
    repo.save(a)
    print("Checking mention depth limit...")
    from gnom_hub.db.legacy_db import get_chat_history, get_active_project
    process_swarm_mentions("GeneralAG", "@TestCoderAG build it", depth=10)
    history = get_chat_history(get_active_project(), limit=5)
    warning_found = any("Limit überschritten" in m.get("content", "") for m in history)
    assert warning_found, "Mention depth loop prevention did not abort at depth > 10!"
    print("Mention depth limit verified successfully!")
    return agent_id

def check_pulse_janitor(repo, agent_id):
    print("Checking pulse timeout watcher...")
    coder = repo.get_by_name("TestCoderAG")
    assert coder is not None
    coder.status = "busy"
    coder.last_seen = datetime.now(timezone.utc) - timedelta(minutes=6)
    repo.save(coder)
    pulse_janitor()
    coder_after = repo.get_by_name("TestCoderAG")
    assert coder_after.status == "online", f"Agent status was not reset! Still: {coder_after.status}"
    assert coder_after.active_job is None, "Agent active job was not cleared!"
    from gnom_hub.db.legacy_db import get_chat_history, get_active_project
    history_after = get_chat_history(get_active_project(), limit=5)
    timeout_msg_found = any("automatisch freigegeben" in m.get("content", "") for m in history_after)
    assert timeout_msg_found, "System timeout release chat message was not posted!"
    print("Pulse timeout watcher verified successfully!")

def test_swarm_stability():
    print("--- STARTING SWARM STABILITY TESTS ---")
    gnom_hub.db.init_db()
    repo = SQLiteAgentRepository()
    agent_id = check_mention_depth(repo)
    check_pulse_janitor(repo, agent_id)
    print("Checking preset change transactional safety...")
    handle_preset_change("Web Development")
    assert gnom_hub.db.get_state_value("active_preset") == "Web Development"
    print("Preset transactional change verified successfully!")
    repo.delete(agent_id)
    print("All stability tests passed successfully!")

if __name__ == "__main__":
    test_swarm_stability()
