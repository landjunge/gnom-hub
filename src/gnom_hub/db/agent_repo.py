"""Agent repository — CRUD operations for agent records.

This module contains two layers:
1. The OOP AgentRepository / SQLiteAgentRepository (used by newer code paths)
2. Legacy functional API (re-exported from legacy_db.py for backward compatibility)
"""

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
from .connection import get_db_conn, Await, parse_dt
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
        with get_db_conn() as c: return Await(_to_ag(c.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (str(a_id), str(a_id))).fetchone()))
    def get_by_name(self, name: str) -> Await:
        with get_db_conn() as c: return Await(_to_ag(c.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()))
    def list_all(self) -> Await:
        with get_db_conn() as c: return Await([_to_ag(r) for r in c.execute("SELECT * FROM agents").fetchall()])
    get_all = list_all
    def save(self, a: Agent) -> Await:
        with get_db_conn() as c:
            from gnom_hub.db import validate_agent_limit_db
            validate_agent_limit_db(c, a.role, a.name)
            ls = a.last_seen.isoformat() if a.last_seen else datetime.now().isoformat()
            c.execute("INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (a.name, str(a.id), a.port, a.description, a.status, json.dumps(a.capabilities or []), a.role, a.active_job, ls)); c.commit()
        if a.model:
            from gnom_hub.db import get_state_value, set_state_value
            db = get_state_value("llm_agents") or {}; db[a.name.lower()] = db.get(a.name.lower(), {}); db[a.name.lower()]["model"] = a.model; set_state_value("llm_agents", db)
        return Await(a)
    def delete(self, a_id) -> Await:
        with get_db_conn() as c: cur = c.execute("DELETE FROM agents WHERE id = ? OR name = ?", (str(a_id), str(a_id))); c.commit(); return Await(cur.rowcount > 0)
    def delete_by_id(self, a_id) -> None: self.delete(a_id)
    def delete_offline(self) -> None:
        with get_db_conn() as c: c.execute("DELETE FROM agents WHERE status = 'offline'"); c.commit()
    def update_status(self, name: str, status: str) -> None:
        with get_db_conn() as c: c.execute("UPDATE agents SET status = ?, last_seen = ? WHERE name = ?", (status, datetime.now().isoformat(), name)); c.commit()
    def update_active_job(self, name: str, job: str) -> None:
        from gnom_hub.db import update_agent_active_job; update_agent_active_job(name, job)
    def clear_jobs(self, name: str = None) -> None:
        from gnom_hub.db import clear_agent_jobs; clear_agent_jobs(name)


# =====================================================================
# LEGACY FUNCTIONAL API
# Functions moved here from legacy_db.py for decomposition.
# =====================================================================

import sqlite3
import uuid
from datetime import timezone

from gnom_hub.core.logger import get_logger
from gnom_hub.db.connection import get_db_conn
from gnom_hub.db.system_repo import is_testing
from gnom_hub.db.schema import _seed_agents

_logger = get_logger("db")


def validate_agent_limit_db(conn, role: str, name: str) -> bool:
    if is_testing():
        return True
    sys_roles = {"soul", "general", "watchdog", "security"}
    is_sys = role in sys_roles
    rows = conn.execute("SELECT name, role FROM agents").fetchall()
    existing = next((r for r in rows if r["name"].lower() == name.lower()), None)
    if existing:
        was_sys = existing["role"] in sys_roles
        if was_sys == is_sys:
            return True
    count = sum(1 for r in rows if (r["role"] in sys_roles) == is_sys and r["name"].lower() != name.lower())
    if count >= 4:
        from gnom_hub.core.exceptions import ValidationError
        raise ValidationError(f"Limit von 4 {'System' if is_sys else 'Worker'}-Agenten überschritten.")
    return True

def create_agent_record(name: str, description: str = "", status: str = "offline", role: str = "normal", capabilities: list = None) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                validate_agent_limit_db(conn, role, name)
                agent_id = str(uuid.uuid4())
                caps = capabilities or []
                conn.execute("""
                    INSERT INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen)
                    VALUES (?, ?, 0, ?, ?, ?, ?, NULL, ?)
                """, (name, agent_id, description, status, json.dumps(caps), role, datetime.now(timezone.utc).isoformat()))
                return {"id": agent_id, "name": name, "description": description, "status": status, "capabilities": caps, "role": role}
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to create agent record: {e}")
        return None

def get_all_agents():
    """Gibt alle Agenten aus der agents-Tabelle zurück."""
    try:
        with get_db_conn() as conn:
            rows = conn.execute("SELECT * FROM agents").fetchall()
            if not rows:
                with conn:
                    _seed_agents(conn)
                rows = conn.execute("SELECT * FROM agents").fetchall()
            
            res = []
            for r in rows:
                d = dict(r)
                try:
                    d["capabilities"] = json.loads(d["capabilities"])
                except (json.JSONDecodeError, TypeError) as e:
                    _logger.error(f"[DB] Failed to parse capabilities JSON for agent {d.get('name')}: {e}")
                    d["capabilities"] = []
                res.append(d)
            return res
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to retrieve agents list: {e}")
        return []

def agent_exists(agent_id: str) -> bool:
    try:
        with get_db_conn() as conn:
            row = conn.execute("SELECT 1 FROM agents WHERE id = ? OR name = ?", (agent_id, agent_id)).fetchone()
            return row is not None
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to check agent existence: {e}")
        return False

def set_agent_status(agent_ref: str, status: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = ?, last_seen = ? 
                    WHERE id = ? OR name = ?
                """, (status, datetime.now(timezone.utc).isoformat(), agent_ref, agent_ref))
                row = conn.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (agent_ref, agent_ref)).fetchone()
                if row:
                    d = dict(row)
                    d["capabilities"] = json.loads(d["capabilities"])
                    return d
                return None
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to set agent status for {agent_ref}: {e}")
        return None

def update_agent_status(name: str, status: str, active_job: str = None):
    """Aktualisiert atomar und transaktionssicher den Online-Status eines Agenten."""
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = ?, active_job = ?, last_seen = ? 
                    WHERE name = ?
                """, (status, active_job, datetime.now(timezone.utc).isoformat(), name))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to update agent status for {name}: {e}")

def delete_agent_by_id(agent_id: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM agents WHERE id = ? OR name = ?", (agent_id, agent_id))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete agent {agent_id}: {e}")

def delete_non_system_agents(system_agents: list):
    try:
        with get_db_conn() as conn:
            with conn:
                placeholders = ",".join("?" for _ in system_agents)
                conn.execute(f"DELETE FROM agents WHERE LOWER(name) NOT IN ({placeholders})", [n.lower() for n in system_agents])
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete non-system agents: {e}")

def delete_offline_agents():
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM agents WHERE status = 'offline'")
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to delete offline agents: {e}")

def set_agent_role(agent_ref: str, role: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                row = conn.execute("SELECT name FROM agents WHERE id = ? OR name = ?", (agent_ref, agent_ref)).fetchone()
                name = row["name"] if row else agent_ref
                validate_agent_limit_db(conn, role, name)
                if role == "general":
                    conn.execute("UPDATE agents SET role = 'normal' WHERE role = 'general'")
                conn.execute("UPDATE agents SET role = ? WHERE id = ? OR name = ?", (role, agent_ref, agent_ref))
                row = conn.execute("SELECT * FROM agents WHERE id = ? OR name = ?", (agent_ref, agent_ref)).fetchone()
                return dict(row) if row else None
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to set agent role for {agent_ref}: {e}")
        return None

def update_agent_role_memory(agent_id: str, role_content: str = None):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("DELETE FROM chat WHERE agent_id = ? AND msg_type = 'role'", (agent_id,))
                if role_content:
                    msg_id = str(uuid.uuid4())
                    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    meta = {"type": "role", "sender": "System"}
                    conn.execute("""
                        INSERT INTO chat (id, project, sender, agent_id, msg_type, content, timestamp, metadata)
                        VALUES (?, 'default', 'System', ?, 'role', ?, ?, ?)
                    """, (msg_id, agent_id, role_content, ts, json.dumps(meta)))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to update agent role memory: {e}")

def register_agent_in_db(name: str, port: int, description: str) -> dict:
    try:
        with get_db_conn() as conn:
            with conn:
                row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
                now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                if row:
                    conn.execute("""
                        UPDATE agents 
                        SET status = 'online', port = ?, description = ?, last_seen = ? 
                        WHERE name = ?
                    """, (port, description or str(port), now_str, name))
                else:
                    validate_agent_limit_db(conn, "normal", name)
                    agent_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen)
                        VALUES (?, ?, ?, ?, 'online', '[]', 'normal', NULL, ?)
                    """, (name, agent_id, port, description or str(port), now_str))
                
                updated = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
                if updated:
                    d = dict(updated)
                    d["capabilities"] = json.loads(d["capabilities"])
                    return d
                return None
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to register agent {name}: {e}")
        return None

def pulse_agent_alive(name: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("""
                    UPDATE agents 
                    SET status = 'online', last_seen = ? 
                    WHERE name = ?
                """, (datetime.now(timezone.utc).isoformat(), name))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to pulse agent alive: {e}")

def clear_agent_jobs(agent_name: str = None):
    try:
        with get_db_conn() as conn:
            with conn:
                if agent_name:
                    conn.execute("UPDATE agents SET active_job = NULL WHERE LOWER(name) = ?", (agent_name.lower(),))
                else:
                    conn.execute("UPDATE agents SET active_job = NULL")
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to clear agent jobs: {e}")

def update_agent_active_job(name: str, active_job: str):
    try:
        with get_db_conn() as conn:
            with conn:
                conn.execute("UPDATE agents SET active_job = ? WHERE LOWER(name) = ?", (active_job or None, name.lower()))
    except sqlite3.Error as e:
        _logger.error(f"[DB] Failed to update agent active job for {name}: {e}")
