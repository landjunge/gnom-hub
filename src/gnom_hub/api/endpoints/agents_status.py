from datetime import datetime, timezone
import json
import logging
import os
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from gnom_hub.agents.entities import Agent
from gnom_hub.db.agent_repo import SQLiteAgentRepository
from gnom_hub.db.chat_repo import SQLiteChatRepository

router = APIRouter()

class AgentEntry(BaseModel):
    name: str
    description: str
    status: str

class StatusUpdate(BaseModel):
    status: str

DEFAULT_SETTINGS = {
    "personality": 3,
    "response_style": 3,
    "memory_strength": 3,
    "creativity": 3,
    "risk_tolerance": 3,
    "custom_prompt": ""
}

class AgentSettings(BaseModel):
    personality: int
    response_style: int
    memory_strength: int
    creativity: int
    risk_tolerance: int
    custom_prompt: str

class ImportData(BaseModel):
    settings: Optional[dict] = None
    soul_facts: Optional[list] = None
    prompt_versions: Optional[list] = None

class SavePresetPayload(BaseModel):
    name: str
    description: str

def get_agent_token_stats(agent_name: str) -> dict:
    from gnom_hub.core.config import TOKENS_FILE
    res = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, "r") as f:
                data = json.load(f)
                for entry in data.get("history", []):
                    key = entry.get("key") or ""
                    if key.lower() == agent_name.lower():
                        res["prompt_tokens"] += entry.get("prompt", 0)
                        res["completion_tokens"] += entry.get("completion", 0)
                        res["total_tokens"] += entry.get("total", 0)
        except Exception as e: logging.getLogger(__name__).error('Fehler in Laden der Token-Statistik: %s', e)
    return res

@router.get("/api/agents/{a_id}/status")
def get_agent_status(a_id: str):
    repo = SQLiteAgentRepository()
    a = repo.get_by_id(a_id)
    st = a.status if a else "offline"
    if st == "running": st = "online"
    return {"status": st}

@router.api_route("/api/agents/{a_id}/status", methods=["PUT", "POST"])
async def set_status(a_id: str, request: Request, update: Optional[StatusUpdate] = None, status: Optional[str] = Query(None)):
    real_status = status
    if not real_status and request.method == "POST":
        try:
            body = await request.json()
            real_status = body.get("status") if isinstance(body, dict) else None
        except Exception as e: logging.getLogger(__name__).error('Fehler in Parsen des Request-Body: %s', e)
    if not real_status and update:
        real_status = update.status
    if not real_status: raise HTTPException(422, "Missing 'status'")
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    repo.update_status(agent.name, real_status)
    return {"status": real_status}

@router.post("/api/agents")
def create_agent(a: AgentEntry):
    repo = SQLiteAgentRepository()
    agent = Agent(name=a.name, id=str(uuid4()), port=0, description=a.description, status=a.status, capabilities=[], role="normal", active_job=None, last_seen=datetime.now(timezone.utc))
    repo.save(agent)
    return agent.__dict__

@router.delete("/api/agents/{a_id}")
def delete_agent(a_id: str):
    SQLiteAgentRepository().delete_by_id(a_id)
    SQLiteChatRepository().delete_by_agent(a_id)
    return {"status": "deleted"}

@router.get("/api/agents/{a_id}/settings")
def get_agent_settings(a_id: str):
    from gnom_hub.db.legacy_db import get_state_value
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    all_settings = get_state_value("agent_settings", {})
    agent_settings = all_settings.get(agent.name.lower(), {})
    return {k: agent_settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}

@router.put("/api/agents/{a_id}/settings")
def update_agent_settings(a_id: str, settings: AgentSettings):
    from gnom_hub.db.legacy_db import get_state_value, set_state_value
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    all_settings = get_state_value("agent_settings", {})
    all_settings[agent.name.lower()] = settings.dict()
    set_state_value("agent_settings", all_settings)
    return {"status": "success", "settings": all_settings[agent.name.lower()]}

@router.get("/api/agents/{a_id}/stats")
def get_agent_stats(a_id: str):
    from gnom_hub.infrastructure.monitoring import METRICS
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    name = agent.name.lower()
    m = METRICS.get(name, {"total": 0, "failed": 0, "avg_time_ms": 0.0})
    t_stats = get_agent_token_stats(agent.name)
    return {
        "total_calls": m["total"],
        "errors": m["failed"],
        "avg_latency_ms": m["avg_time_ms"],
        "prompt_tokens": t_stats["prompt_tokens"],
        "completion_tokens": t_stats["completion_tokens"],
        "total_tokens": t_stats["total_tokens"]
    }

@router.get("/api/agents/{a_id}/export")
def export_agent(a_id: str):
    from gnom_hub.db.legacy_db import get_state_value, get_db_conn
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    all_settings = get_state_value("agent_settings", {})
    agent_settings = all_settings.get(agent.name.lower(), {})
    settings = {k: agent_settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    with get_db_conn() as conn:
        facts = [
            {"key": r["key"], "value": r["value"], "priority": r["priority"]}
            for r in conn.execute("SELECT key, value, priority FROM soul_memory WHERE agent = ?", (agent.name,)).fetchall()
        ]
        versions = [
            {
                "id": r["id"], "base_prompt": r["base_prompt"], "modifications": r["modifications"],
                "performance_score": r["performance_score"], "created_at": r["created_at"],
                "feedback_count": r["feedback_count"], "is_active": r["is_active"], "parent_id": r["parent_id"]
            }
            for r in conn.execute("SELECT id, base_prompt, modifications, performance_score, created_at, feedback_count, is_active, parent_id FROM prompt_versions WHERE agent = ?", (agent.name,)).fetchall()
        ]
    return {
        "agent": {"name": agent.name, "description": agent.description, "role": agent.role},
        "settings": settings,
        "soul_facts": facts,
        "prompt_versions": versions
    }

@router.post("/api/agents/{a_id}/import")
def import_agent(a_id: str, data: ImportData):
    from gnom_hub.db.legacy_db import get_state_value, set_state_value, get_db_conn, save_soul_fact
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    if data.settings:
        all_settings = get_state_value("agent_settings", {})
        merged = {k: data.settings.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS}
        all_settings[agent.name.lower()] = merged
        set_state_value("agent_settings", all_settings)
    if data.soul_facts is not None:
        with get_db_conn() as conn:
            conn.execute("DELETE FROM soul_memory WHERE agent = ?", (agent.name,))
            conn.commit()
        for f in data.soul_facts:
            save_soul_fact(f.get("key"), f.get("value"), agent=agent.name, priority=f.get("priority", "medium"))
    if data.prompt_versions is not None:
        with get_db_conn() as conn:
            conn.execute("DELETE FROM prompt_versions WHERE agent = ?", (agent.name,))
            for pv in data.prompt_versions:
                conn.execute(
                    "INSERT INTO prompt_versions (id, agent, base_prompt, modifications, performance_score, created_at, feedback_count, is_active, parent_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (pv["id"], agent.name, pv["base_prompt"], pv["modifications"], pv["performance_score"], pv["created_at"], pv["feedback_count"], pv["is_active"], pv["parent_id"])
                )
            conn.commit()
    return {"status": "success"}

@router.post("/api/presets/save")
def save_preset(p: SavePresetPayload):
    from gnom_hub.core.config import CONFIG_DIR
    from gnom_hub.db.legacy_db import get_state_value
    all_settings = get_state_value("agent_settings", {})
    prompt_modifiers = {}
    for a_name, a_set in all_settings.items():
        if a_set.get("custom_prompt"):
            prompt_modifiers[a_name] = a_set["custom_prompt"]
    preset_data = {
        "name": p.name,
        "description": p.description,
        "prompt_modifier": prompt_modifiers,
        "agent_settings": all_settings,
        "model": {"primary": "stage_3"},
        "allowed_tools": ["coderag"]
    }
    pdir = CONFIG_DIR / "presets"
    pdir.mkdir(parents=True, exist_ok=True)
    fn = p.name.lower().replace(" ", "_") + ".json"
    preset_file = pdir / fn
    with open(preset_file, "w", encoding="utf-8") as f:
        json.dump(preset_data, f, indent=2, ensure_ascii=False)
    return {"status": "success", "file": str(preset_file)}
