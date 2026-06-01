import json; import logging; from uuid import UUID; from datetime import datetime; from typing import List, Optional
from abc import ABC, abstractmethod
from gnom_hub.agents.entities import Agent

class AgentRepository(ABC):
    @abstractmethod
    def get_by_id(self, agent_id) -> Optional[Agent]: pass
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Agent]: pass
    @abstractmethod
    def list_all(self) -> List[Agent]: pass
    @abstractmethod
    def save(self, agent: Agent) -> Agent: pass
    @abstractmethod
    def delete(self, agent_id) -> bool: pass
from .connection import get_db_connection, Await, parse_dt
def _to_ag(r) -> Optional[Agent]:
    if not r: return None
    from gnom_hub.core.config import RUN_DIR; from gnom_hub.db import get_state_value
    n, pid = r["name"], None
    for pn in (n, n[0].lower() + n[1:] if n else ""):
        try: pid = int((RUN_DIR / f"{pn}.pid").read_text().strip())
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in PID-Datei-Lesen: %s', e)
    model = (get_state_value("llm_agents") or {}).get(n.lower(), {}).get("model")
    return Agent(id=UUID(r["id"]), name=n, status=r["status"], pid=pid, model=model, last_seen=parse_dt(r["last_seen"]), port=r["port"], description=r["description"], capabilities=json.loads(r["capabilities"] or "[]"), role=r["role"], active_job=r["active_job"])
class SQLiteAgentRepository(AgentRepository):
    def get_by_id(self, a_id) -> Await:
        with get_db_connection() as c: return Await(_to_ag(c.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (str(a_id), str(a_id))).fetchone()))
    def get_by_name(self, name: str) -> Await:
        with get_db_connection() as c: return Await(_to_ag(c.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()))
    def list_all(self) -> Await:
        with get_db_connection() as c: return Await([_to_ag(r) for r in c.execute("SELECT * FROM agents").fetchall()])
    get_all = list_all
    def save(self, a: Agent) -> Await:
        with get_db_connection() as c:
            from gnom_hub.db import validate_agent_limit_db
            validate_agent_limit_db(c, a.role, a.name)
            ls = a.last_seen.isoformat() if a.last_seen else datetime.now().isoformat()
            c.execute("INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (a.name, str(a.id), a.port, a.description, a.status, json.dumps(a.capabilities or []), a.role, a.active_job, ls)); c.commit()
        if a.model:
            from gnom_hub.db import get_state_value, set_state_value
            db = get_state_value("llm_agents") or {}; db[a.name.lower()] = db.get(a.name.lower(), {}); db[a.name.lower()]["model"] = a.model; set_state_value("llm_agents", db)
        return Await(a)
    def delete(self, a_id) -> Await:
        with get_db_connection() as c: cur = c.execute("DELETE FROM agents WHERE id = ? OR name = ?", (str(a_id), str(a_id))); c.commit(); return Await(cur.rowcount > 0)
    def delete_by_id(self, a_id) -> None: self.delete(a_id)
    def delete_offline(self) -> None:
        with get_db_connection() as c: c.execute("DELETE FROM agents WHERE status = 'offline'"); c.commit()
    def update_status(self, name: str, status: str) -> None:
        with get_db_connection() as c: c.execute("UPDATE agents SET status = ?, last_seen = ? WHERE name = ?", (status, datetime.now().isoformat(), name)); c.commit()
    def update_active_job(self, name: str, job: str) -> None:
        from gnom_hub.db import update_agent_active_job; update_agent_active_job(name, job)
    def clear_jobs(self, name: str = None) -> None:
        from gnom_hub.db import clear_agent_jobs; clear_agent_jobs(name)
