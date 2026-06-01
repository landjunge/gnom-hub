# specialization_monitor.py — Monitor agent drift and recommend corrective tasks
import asyncio
from typing import Dict
from gnom_hub.db.legacy_db import add_chat_message, log_audit_event

async def analyze_task_categories(agent: str) -> Dict[str, float]:
    """Simulates or analyzes historical agent task category performance."""
    # We provide realistic defaults that showcase drift for testing
    if agent == "WriterAG":
        return {
            "copywriting": 0.92,
            "documentation": 0.45,
            "editing": 0.88
        }
    elif agent == "CoderAG":
        return {
            "code_writing": 0.95,
            "debugging": 0.90,
            "refactoring": 0.88
        }
    else:
        return {
            "general_assistance": 0.90,
            "coordination": 0.88
        }

async def escalate_to_soul(agent: str, message: str, categories: Dict[str, float]):
    """Logs drift escalation in audit log and notifies the user in chat."""
    # Identify the lowest-performing category to recommend training
    min_category = min(categories, key=categories.get)
    recommendation = f"Empfehlung: Gib {agent} mehr {min_category}-Tasks, um zu trainieren."
    
    full_message = f"📢 System-Drift-Meldung: {message}\n💡 {recommendation}"
    
    add_chat_message("default", "System", "system", "chat", full_message)
    log_audit_event(
        agent=agent,
        event_type="specialization_drift",
        details={"message": message, "categories": categories, "recommendation": recommendation}
    )
    print(full_message)

async def monitor_drift():
    agents = ["CoderAG", "WriterAG", "ResearcherAG", "EditorAG"]
    for agent in agents:
        # 1. Track success rate by task category
        categories = await analyze_task_categories(agent)
        
        # 2. Detect drift: "WriterAG is way better at X than Y"
        drift = max(categories.values()) - min(categories.values())
        
        if drift > 0.3:  # >30% divergence
            await escalate_to_soul(
                agent,
                f"{agent} hat zu starke Specialization Drift: {categories}",
                categories
            )
