# structured_log.py — Structured JSON & DB logging with trace tracking
import json, uuid, contextvars
from gnom_hub.db import log_audit_event

trace_var = contextvars.ContextVar("trace_id", default=None)

def set_trace_id(t_id: str = None) -> str:
    val = t_id or str(uuid.uuid4())
    trace_var.set(val)
    return val

def get_trace_id() -> str:
    val = trace_var.get()
    if not val:
        val = str(uuid.uuid4())
        trace_var.set(val)
    return val

class AgentLogger:
    def __init__(self, agent_name: str):
        self.agent = agent_name
    def log_event(self, event_type: str, **details):
        t_id = get_trace_id()
        log_audit_event(self.agent, event_type, details, t_id)
        print(f"[AUDIT] {json.dumps({'agent': self.agent, 'event': event_type, 'details': details, 'trace_id': t_id})}")
