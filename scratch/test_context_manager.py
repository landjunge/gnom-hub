# test_context_manager.py — Tests ContextBudget and token-based priority eviction
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from gnom_hub.db import get_db_conn, init_db
from gnom_hub.context_manager import ContextBudget, count_tokens

def test_context_manager():
    print("--- TESTING CONTEXT BUDGET & EVICTION ---")
    init_db()

    # 1. Clear facts for simulated agent
    agent_name = "CoderAG"
    with get_db_conn() as conn:
        with conn:
            conn.execute("DELETE FROM soul_memory WHERE agent = ?", (agent_name,))

    # 2. Initialize ContextBudget
    # Max tokens = 65, Reserved for output = 40, Available for context = 25
    budget = ContextBudget(agent=agent_name, max_tokens=65, reserved_for_output=40)
    assert budget.available_for_context == 25
    assert budget.current_usage == 0

    # 3. Add facts within budget limits
    # "Fact A" is about 7 tokens.
    fact_a = "Fact A: Database uses WAL mode."
    budget.add_fact(fact_a, priority="high")
    tokens_a = count_tokens(fact_a)
    print(f"Added Fact A ({tokens_a} tokens). Current usage: {budget.current_usage} / 25")
    assert budget.current_usage == tokens_a

    # Add Fact B (medium priority)
    fact_b = "Fact B: Server runs on port 3002."
    budget.add_fact(fact_b, priority="medium")
    tokens_b = count_tokens(fact_b)
    print(f"Added Fact B ({tokens_b} tokens). Current usage: {budget.current_usage} / 25")
    assert budget.current_usage == tokens_a + tokens_b

    # Add Fact C (low priority)
    fact_c = "Fact C: Temporary scratchpad files."
    budget.add_fact(fact_c, priority="low")
    tokens_c = count_tokens(fact_c)
    print(f"Added Fact C ({tokens_c} tokens). Current usage: {budget.current_usage} / 25")
    assert budget.current_usage == tokens_a + tokens_b + tokens_c

    # 4. Exceed the budget! Adding a high-priority Fact D (needs e.g. 11 tokens)
    # The total will be (tokens_a + tokens_b + tokens_c + tokens_d) > 25.
    # Eviction should kick in and evict lowest-priority first (Fact C - 'low', then Fact B - 'medium' if needed)
    fact_d = "Fact D: Safety commands require specific sandbox parameters validation."
    tokens_d = count_tokens(fact_d)
    print(f"\nAdding Fact D ({tokens_d} tokens) which exceeds remaining budget.")
    budget.add_fact(fact_d, priority="high")
    print(f"Current usage after eviction: {budget.current_usage} / 25")

    # Verify that we are within budget
    assert budget.current_usage <= budget.available_for_context

    # Verify which facts remain in database
    with get_db_conn() as conn:
        rows = conn.execute("SELECT value, priority FROM soul_memory WHERE agent = ?", (agent_name,)).fetchall()
        remaining_values = [r["value"] for r in rows]
        print(f"Remaining facts in DB: {remaining_values}")
        
        # Fact C (low priority) MUST have been evicted!
        assert fact_c not in remaining_values
        # Fact D (high priority) MUST be in the database
        assert fact_d in remaining_values

    print("\nContext budget management and eviction successfully verified!")

if __name__ == "__main__":
    test_context_manager()
