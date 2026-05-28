# test_prompt_versioning.py — Tests prompt versioning, score tracking, and auto-rollback
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from gnom_hub.db import get_db_conn, init_db
from gnom_hub.core.utils.evolution_v2 import (
    create_version,
    get_active_version,
    update_version_score,
    get_version_by_id,
    use_version
)

def test_prompt_versioning():
    print("--- TESTING PROMPT VERSIONING AND AUTO-ROLLBACK ---")
    init_db()

    # 1. Clear previous versions
    with get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM prompt_versions WHERE agent = 'CoderAG'")

    # 2. Create base prompt version (v1)
    v1 = create_version("CoderAG", "Rule 1: Use absolute path validation.")
    print(f"Created version 1: {v1}")
    assert v1.is_active is True
    assert len(v1.modifications) == 1
    assert v1.modifications[0] == "Rule 1: Use absolute path validation."
    
    active = get_active_version("CoderAG")
    assert active is not None
    assert active.id == v1.id

    # 3. Create evolved prompt version (v2)
    v2 = create_version("CoderAG", "Rule 2: Restrict commands to safe lists.")
    print(f"Created evolved version 2: {v2}")
    assert v2.is_active is True
    assert v2.parent_id == v1.id
    assert len(v2.modifications) == 2
    assert "Rule 2: Restrict" in v2.modifications[1]

    # Verify v1 is now inactive
    v1_check = get_version_by_id(v1.id)
    assert v1_check.is_active is False

    # 4. Update score (successful performance)
    update_version_score("CoderAG", "up")
    v2_updated = get_active_version("CoderAG")
    print(f"Version 2 updated score (upvote): {v2_updated.performance_score:.2f}")
    assert v2_updated.feedback_count == 1
    assert v2_updated.performance_score == 1.0

    # 5. Trigger degradation (downvote) -> Auto-Rollback to v1
    # If we downvote, the new score will be (1.0 + 0.0)/2 = 0.5
    # 0.5 < 1.0 (v1 score) * 0.95 (which is 0.95), so it should auto-rollback!
    rollback_target = update_version_score("CoderAG", "down")
    print(f"Updated score (downvote). Active version now: {rollback_target}")
    
    # Verify rollback occurred and v1 is active again
    assert rollback_target.id == v1.id
    assert rollback_target.is_active is True
    
    active_after_rollback = get_active_version("CoderAG")
    assert active_after_rollback.id == v1.id

    print("\nPrompt Versioning and Auto-Rollback successfully verified!")

if __name__ == "__main__":
    test_prompt_versioning()
