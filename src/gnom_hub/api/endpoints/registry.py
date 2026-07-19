import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from gnom_hub.db.write_serial import serialized_db_write

router = APIRouter()
logger = logging.getLogger("gnom_hub.api.registry")

class RegisterPayload(BaseModel):
    name: str
    port: int
    description: str = ""


def _touch_agent(name: str, port: int = 0, description: str = "") -> dict:
    """Lightweight online/last_seen update — avoids full INSERT OR REPLACE storms."""
    now = datetime.now(timezone.utc).isoformat()
    with serialized_db_write() as c:
        cur = c.execute(
            "UPDATE agents SET status='online', last_seen=?, port=COALESCE(NULLIF(?, 0), port), "
            "description=CASE WHEN ?!='' THEN ? ELSE description END WHERE name=? OR lower(name)=lower(?)",
            (now, port, description or "", description or "", name, name),
        )
        if cur.rowcount == 0:
            # First-time register only
            aid = str(uuid4())
            c.execute(
                "INSERT INTO agents (name, id, port, description, status, capabilities, role, active_job, last_seen) "
                "VALUES (?, ?, ?, ?, 'online', '[]', 'normal', NULL, ?)",
                (name, aid, port, description or str(port), now),
            )
            return {
                "name": name, "id": aid, "port": port, "description": description,
                "status": "online", "role": "normal", "last_seen": now,
            }
        row = c.execute(
            "SELECT name, id, port, description, status, role, last_seen FROM agents "
            "WHERE name=? OR lower(name)=lower(?) LIMIT 1",
            (name, name),
        ).fetchone()
        if not row:
            return {"name": name, "status": "online", "last_seen": now}
        return {
            "name": row["name"], "id": row["id"], "port": row["port"],
            "description": row["description"], "status": row["status"],
            "role": row["role"], "last_seen": row["last_seen"],
        }


@router.post("/api/agents/register")
def register_agent(p: RegisterPayload):
    """Register/heartbeat-style online mark. Never hard-fail the agent loop on DB lock."""
    try:
        return _touch_agent(p.name, p.port, p.description or str(p.port))
    except sqlite3.OperationalError as e:
        # Soft-OK: agent stays in reconnect loop less aggressively if hub is contending
        logger.warning("register soft-fail %s: %s", p.name, e)
        return {
            "name": p.name, "port": p.port, "description": p.description,
            "status": "online", "soft": True, "error": str(e)[:80],
        }
    except Exception as e:
        logger.error("Failed to register agent %r: %s", p.name, e)
        return {
            "name": p.name, "port": p.port, "status": "online", "soft": True, "error": str(e)[:80],
        }


@router.post("/api/agents/{a_id}/heartbeat")
def heartbeat(a_id: str):
    """Cheap last_seen touch — never overwrite busy/processing/running status."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        with serialized_db_write() as c:
            # Keep busy/processing/running; only force online when idle/stale.
            cur = c.execute(
                """
                UPDATE agents
                SET last_seen = ?,
                    status = CASE
                        WHEN lower(COALESCE(status, '')) IN ('busy', 'processing', 'running')
                        THEN status
                        ELSE 'online'
                    END
                WHERE name=? OR id=? OR lower(name)=lower(?)
                """,
                (now, a_id, a_id, a_id),
            )
            if cur.rowcount == 0:
                # Fallback: create from definitions if known
                from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
                key = a_id.lower()
                if key in AGENT_DEFINITIONS:
                    defn = AGENT_DEFINITIONS[key]
                    c.execute(
                        "INSERT OR IGNORE INTO agents "
                        "(name, id, port, description, status, capabilities, role, active_job, last_seen) "
                        "VALUES (?, ?, 0, ?, 'online', ?, ?, NULL, ?)",
                        (
                            defn["name"], str(uuid4()), defn["description"],
                            __import__("json").dumps(defn.get("capabilities", [])),
                            defn["role"], now,
                        ),
                    )
                    return {"status": "online"}
                return {"error": "not found"}
            row = c.execute(
                "SELECT status FROM agents WHERE name=? OR id=? OR lower(name)=lower(?) LIMIT 1",
                (a_id, a_id, a_id),
            ).fetchone()
            return {"status": (row["status"] if row else "online")}
    except sqlite3.OperationalError as e:
        logger.warning("heartbeat soft-fail %s: %s", a_id, e)
        return {"status": "online", "soft": True}
    except Exception as e:
        logger.error("heartbeat failed %s: %s", a_id, e)
        return {"status": "online", "soft": True}
