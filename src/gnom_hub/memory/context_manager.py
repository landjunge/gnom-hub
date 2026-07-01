# context_manager.py — Dynamic context budget management and priority eviction
import hashlib
import logging
from typing import Literal

from gnom_hub.db import add_to_soul_memory, get_db_conn
from gnom_hub.db.soul_repo import save_soul_fact_smart

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
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in _calculate_current_usage: %s', e)
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
        # SoulAG ist der einzige Schreiber — Quell-Agent im value-Prefix
        tagged = f"[source:{self.agent}] {fact}" if self.agent and self.agent.lower() != "soulag" else fact

        # Pre-Dedup via Smart-Engine: deterministischer Key ohne UUID.
        # Engine returnt canonical key (string) auf success, None auf reject.
        # Wenn None (rejected) ODER der zurückgegebene key != unser dedup_key
        # (= dedup hat in einen existierenden Slot gemerged), überspringen wir
        # den UUID-basierten Insert in add_to_soul_memory.
        # md5 als Non-Crypto-Content-Hash für Dedup-Key — Kollisionsresistenz irrelevant, Geschwindigkeit zählt.
        dedup_key = f"ctx:{self.agent.lower()}:{hashlib.md5(fact.encode('utf-8')).hexdigest()[:12]}"  # noqa: S324
        try:
            result = save_soul_fact_smart(dedup_key, tagged, agent="SoulAG", priority=priority)
            if isinstance(result, str):
                if result is None:
                    # Smart-Engine hat verworfen (Wert zu kurz oder leer)
                    logging.getLogger(__name__).debug(
                        "[ContextManager] Smart-Engine rejected dedup_key=%s — skip UUID insert",
                        dedup_key,
                    )
                    return
                if result != dedup_key:
                    # Engine hat in einen bestehenden Slot gemerged
                    # (Jaccard-Match oder Prefix-Match) — UUID-Insert überflüssig
                    logging.getLogger(__name__).debug(
                        "[ContextManager] Smart-Engine merged %s -> %s — skip UUID insert",
                        dedup_key, result,
                    )
                    return
            elif isinstance(result, dict):
                # Forward-compat: dict-Rückgabe
                action = result.get("action", "inserted")
                if action in ("merged", "rejected"):
                    return
        except Exception as e:
            logging.getLogger(__name__).warning(
                "[ContextManager] Smart-Dedup pre-check failed: %s — fallback to direct insert", e,
            )

        # Smart-Engine hat inserted (result == dedup_key) oder war nicht verfügbar
        # → normaler UUID-Insert für kompatibilität mit altem Code
        add_to_soul_memory(tagged, priority=priority, agent="SoulAG")
