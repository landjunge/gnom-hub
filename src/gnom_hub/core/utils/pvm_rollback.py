# pvm_rollback.py
from gnom_hub.database.legacy_db import add_chat_message, log_audit_event

def should_rollback(pvm, agent: str, cur_id: str, prev_id: str) -> bool:
    cur = pvm.get_version_by_id(cur_id)
    prev = pvm.get_version_by_id(prev_id)
    return cur.performance_score < prev.performance_score * 0.95 if (cur and prev) else False

def auto_rollback(pvm, agent: str, prev_id: str):
    pvm.activate_version(agent, prev_id)
    add_chat_message("default", "System", "system", "chat", f"🔄 Auto-Rollback für **{agent}**: Degradation. Version `{prev_id}` reaktiviert.")
    log_audit_event(agent=agent, event_type="prompt_auto_rollback", details={"rolled_back_to": prev_id})
