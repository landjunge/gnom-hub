# context_manager.py — Dynamic context budget management and priority eviction
import sqlite3
from typing import Literal
from gnom_hub.db import get_db_conn, add_to_soul_memory

# Priority values for eviction sorting (lower value gets evicted first)
PRIORITY_VALUES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}

def count_tokens(text: str) -> int:
    """Estimates the token count of a given string using word/char approximation."""
    if not text:
        return 0
    words = len(text.split())
    # Standard approximation: 1 word ~ 1.3 tokens, fallback to characters if very short
    return max(1, int(words * 1.3) if words > 0 else len(text) // 4)

class ContextBudget:
    def __init__(self, agent: str, max_tokens: int = 2000, reserved_for_output: int = 1000):
        self.agent = agent
        self.max_tokens = max_tokens
        self.reserved_for_output = reserved_for_output
        self.available_for_context = max_tokens - reserved_for_output
        self.current_usage = self._calculate_current_usage()

    def _calculate_current_usage(self) -> int:
        """Sums up token count of all active context facts for this agent."""
        total = 0
        try:
            with get_db_conn() as conn:
                rows = conn.execute(
                    "SELECT value FROM soul_memory WHERE agent = ?",
                    (self.agent,)
                ).fetchall()
                for row in rows:
                    total += count_tokens(row["value"])
        except Exception:
            pass
        return total

    def evict_by_priority(self, needed_tokens: int = 0):
        """Evicts the lowest-priority, oldest facts until budget constraints are satisfied."""
        try:
            with get_db_conn() as conn:
                # Query all facts for this agent sorted by timestamp (oldest first)
                rows = [dict(r) for r in conn.execute(
                    "SELECT id, key, value, priority FROM soul_memory WHERE agent = ? ORDER BY timestamp ASC",
                    (self.agent,)
                ).fetchall()]
                
                # Sort facts: lowest priority value first. Oldest first is preserved from the SQL order.
                rows.sort(key=lambda x: PRIORITY_VALUES.get(x["priority"], 2))

                # Evict until we fit within available_for_context (including the new fact's tokens)
                for row in rows:
                    if self.current_usage + needed_tokens <= self.available_for_context:
                        break
                    
                    # Evict this fact
                    tokens = count_tokens(row["value"])
                    with conn:
                        conn.execute("DELETE FROM soul_memory WHERE id = ?", (row["id"],))
                    self.current_usage -= tokens
        except Exception as e:
            import logging
            logging.getLogger("db").error(f"[ContextManager] Eviction failed: {e}")

    def add_fact(self, fact: str, priority: Literal["critical", "high", "medium", "low"]):
        tokens = count_tokens(fact)
        
        if self.current_usage + tokens > self.available_for_context:
            # Evict lowest-priority old facts
            self.evict_by_priority(needed_tokens=tokens)
        
        self.current_usage += tokens
        add_to_soul_memory(fact, priority=priority, agent=self.agent)
