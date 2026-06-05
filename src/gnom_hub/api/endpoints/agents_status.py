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
    "custom_prompt": "",
    "sys_prompt": ""
}

class AgentSettings(BaseModel):
    personality: int
    response_style: int
    memory_strength: int
    creativity: int
    risk_tolerance: int
    custom_prompt: str
    sys_prompt: str

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

class SliderUpdatePayload(BaseModel):
    personality: Optional[int] = None
    creativity: Optional[int] = None
    risk_tolerance: Optional[int] = None
    response_style: Optional[int] = None
    memory_strength: Optional[int] = None
    obedience: Optional[int] = None

@router.get("/api/agents/{a_id}/sliders")
def get_agent_sliders(a_id: str):
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    from gnom_hub.core.utils.slider_prompt import get_all_sliders
    return get_all_sliders(agent.name)

@router.put("/api/agents/{a_id}/sliders")
def update_agent_sliders(a_id: str, data: SliderUpdatePayload):
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    from gnom_hub.core.utils.slider_prompt import set_all_sliders
    values = {k: v for k, v in data.dict().items() if v is not None}
    if not values:
        raise HTTPException(400, "No values provided")
    ok = set_all_sliders(agent.name, values)
    return {"status": "ok" if ok else "error"}

class StateConfigPayload(BaseModel):
    key: str
    value: bool

@router.post("/api/admin/config")
def set_state_config(data: StateConfigPayload):
    from gnom_hub.db import set_state_value
    set_state_value(data.key, data.value)
    return {"status": "ok", "key": data.key, "value": data.value}

@router.get("/api/state/{key}")
def get_state_config(key: str):
    from gnom_hub.db import get_state_value
    return {"key": key, "value": get_state_value(key)}

class ToolToggle(BaseModel):
    tool: str

@router.post("/api/agents/{a_id}/tools/toggle")
def toggle_agent_tool(a_id: str, data: ToolToggle):
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    from gnom_hub.db import get_state_value, set_state_value
    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
    from gnom_hub.agents.tool_registry import get_tools_for_agent
    all_settings = get_state_value("agent_settings", {})
    key = agent.name.lower()
    agent_cfg = all_settings.get(key, {})

    # Check if tool is a definition tool
    defn = AGENT_DEFINITIONS.get(key, {})
    lang_block = defn.get("de") or defn.get("en") or {}
    perm_soul = {"role": defn.get("role", "normal"), "permissions": lang_block.get("permissions", []),
                 "character": "", "directive": ""}
    def_tools = list(get_tools_for_agent(perm_soul).keys())
    is_def_tool = data.tool in def_tools

    disabled = agent_cfg.get("tools_disabled", [])
    enabled = agent_cfg.get("tools_enabled", [])

    if is_def_tool:
        # Toggle in tools_disabled
        if data.tool in disabled:
            disabled.remove(data.tool)
            enabled_now = True
        else:
            disabled.append(data.tool)
            enabled_now = False
    else:
        # Toggle in tools_enabled
        if data.tool in enabled:
            enabled.remove(data.tool)
            enabled_now = False
        else:
            enabled.append(data.tool)
            enabled_now = True

    agent_cfg["tools_disabled"] = disabled
    agent_cfg["tools_enabled"] = enabled
    all_settings[key] = agent_cfg
    set_state_value("agent_settings", all_settings)
    return {"status": "ok", "tool": data.tool, "enabled": enabled_now}

@router.get("/api/agents/{a_id}/settings")
def get_agent_settings(a_id: str):
    from gnom_hub.db import get_state_value
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent: raise HTTPException(404, "Agent not found")
    all_settings = get_state_value("agent_settings", {})
    agent_settings = all_settings.get(agent.name.lower(), {})
    res = {k: agent_settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    if not res.get("sys_prompt"):
        from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
        res["sys_prompt"] = AGENT_DEFINITIONS.get(agent.name.lower(), {}).get("sys_prompt", "")
    return res

@router.put("/api/agents/{a_id}/settings")
def update_agent_settings(a_id: str, settings: AgentSettings):
    from gnom_hub.db import get_state_value, set_state_value
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
    from gnom_hub.db import get_state_value
    from gnom_hub.db.connection import get_db_conn
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
    from gnom_hub.db import get_state_value, set_state_value, save_soul_fact
    from gnom_hub.db.connection import get_db_conn
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

@router.get("/api/agents/{a_id}/profile")
def get_agent_profile(a_id: str):
    """One-shot endpoint: permissions, tools, LLM routing, soul summary."""
    from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
    from gnom_hub.agents.tool_registry import get_tools_for_agent
    from gnom_hub.db.state_repo import SQLiteStateRepository
    from gnom_hub.db.connection import get_db_conn
    repo = SQLiteAgentRepository()
    agent = repo.get_by_id(a_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    key = agent.name.lower()
    defn = AGENT_DEFINITIONS.get(key, {})
    lang_block = defn.get("de") or defn.get("en") or {}
    permissions = lang_block.get("permissions", [])
    # Build soul dict for tool_registry (mirrors what agent_base uses)
    soul = {"role": defn.get("role", "normal"), "permissions": permissions,
            "character": lang_block.get("character", ""), "directive": lang_block.get("directive", "")}
    tools = list(get_tools_for_agent(soul).keys())
    # Apply tool overrides from agent_settings
    from gnom_hub.db import get_state_value as gsv
    all_settings = gsv("agent_settings", {})
    agent_cfg = all_settings.get(key, {})
    for t in agent_cfg.get("tools_disabled", []):
        if t in tools:
            tools.remove(t)
    for t in agent_cfg.get("tools_enabled", []):
        if t not in tools:
            tools.append(t)
    # LLM routing
    state_db = SQLiteStateRepository()
    llm_map = state_db.get_value("llm_agents", {})
    agent_llm = llm_map.get(key, {}) if isinstance(llm_map, dict) else {}
    llm_provider = agent_llm.get("provider", "–")
    llm_model = agent_llm.get("model", "–")
    # Soul facts summary
    try:
        with get_db_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM soul_memory WHERE agent = ?", (agent.name,)
            ).fetchone()[0]
            top_rows = conn.execute(
                "SELECT key, value, priority FROM soul_memory WHERE agent = ? "
                "ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, rowid DESC LIMIT 20",
                (agent.name,)
            ).fetchall()
            top_facts = [{"key": r["key"], "value": r["value"][:80], "priority": r["priority"]}
                         for r in top_rows]
    except Exception:
        total = 0
        top_facts = []
    return {
        "name": agent.name,
        "role": defn.get("role", agent.role or "normal"),
        "permissions": permissions,
        "tools": tools,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "soul_fact_count": total,
        "top_soul_facts": top_facts,
    }


@router.post("/api/presets/save")
def save_preset(p: SavePresetPayload):
    from gnom_hub.core.config import CONFIG_DIR
    from gnom_hub.db import get_state_value
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


@router.get("/api/presets")
def list_presets():
    from gnom_hub.core.config import CONFIG_DIR
    pdir = CONFIG_DIR / "presets"
    if not pdir.exists():
        return []
    presets = []
    for f in sorted(pdir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            presets.append({"name": data.get("name","?"), "description": data.get("description",""), "file": f.name})
        except Exception:
            pass
    return presets


class LoadPresetPayload(BaseModel):
    file: str

@router.post("/api/presets/load")
def load_preset(p: LoadPresetPayload):
    from gnom_hub.core.config import CONFIG_DIR
    from gnom_hub.db import set_state_value
    preset_file = CONFIG_DIR / "presets" / p.file
    if not preset_file.exists():
        raise HTTPException(404, "Preset not found")
    data = json.loads(preset_file.read_text(encoding="utf-8"))
    if data.get("agent_settings"):
        set_state_value("agent_settings", data["agent_settings"])
    return {"status": "ok", "name": data.get("name","")}


class SwarmCompletePayload(BaseModel):
    context_id: str
    agent_name: str
    result: dict


@router.post("/api/swarm/complete")
def swarm_complete(data: SwarmCompletePayload):
    from gnom_hub.db.connection import get_db_conn
    from gnom_hub.agents.swarm.swarm_coordinator import signal_completion
    import time
    import json
    import logging

    workflow_msg_id = None

    # Check first if this belongs to a workflow task to build a unique idempotency key
    with get_db_conn() as conn:
        try:
            task_row = conn.execute("""
                SELECT t.msg_id
                FROM workflow_tasks t
                JOIN agent_messages m ON m.id = t.msg_id
                WHERE t.workflow_id = ?
                  AND t.status = 'running'
                  AND LOWER(m.recipient) = LOWER(?)
            """, (data.context_id, data.agent_name)).fetchone()
            if task_row:
                workflow_msg_id = task_row["msg_id"]
        except Exception:
            pass

    if workflow_msg_id is not None:
        key = f"{data.context_id}:{data.agent_name}:{workflow_msg_id}"
    else:
        key = f"{data.context_id}:{data.agent_name}"

    with get_db_conn() as conn:
        existing = conn.execute(
            "SELECT http_status FROM swarm_callbacks WHERE idempotency_key = ?",
            (key,)
        ).fetchone()

        if existing:
            logging.getLogger(__name__).info("Duplikat-Callback ignoriert: %s", key)
            return {"status": "already_processed", "code": existing["http_status"]}

        conn.execute("""
            INSERT INTO swarm_callbacks
                (idempotency_key, context_id, agent_name, result_json, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, data.context_id, data.agent_name, json.dumps(data.result), time.time()))

        # Circuit Breaker Logic
        is_error = data.result.get("status") == "error"
        if is_error:
            conn.execute("""
                UPDATE agents 
                SET consecutive_failures = consecutive_failures + 1
                WHERE name = ?
            """, (data.agent_name,))
            failures = conn.execute(
                "SELECT consecutive_failures FROM agents WHERE name = ?", 
                (data.agent_name,)
            ).fetchone()
            if failures and failures["consecutive_failures"] >= 5:
                conn.execute("""
                    UPDATE agents 
                    SET circuit_state = 'OPEN', status = 'degraded'
                    WHERE name = ?
                """, (data.agent_name,))
                logging.getLogger(__name__).warning(
                    "🚨 [CIRCUIT BREAKER] Agent %s hat 5 aufeinanderfolgende Fehler erreicht. Circuit OPEN, Status degraded.",
                    data.agent_name
                )
        else:
            agent_row = conn.execute(
                "SELECT status FROM agents WHERE name = ?", 
                (data.agent_name,)
            ).fetchone()
            if agent_row:
                if agent_row["status"] == "degraded":
                    conn.execute("""
                        UPDATE agents 
                        SET consecutive_failures = 0, circuit_state = 'CLOSED', status = 'online'
                        WHERE name = ?
                    """, (data.agent_name,))
                else:
                    conn.execute("""
                        UPDATE agents 
                        SET consecutive_failures = 0, circuit_state = 'CLOSED'
                        WHERE name = ?
                    """, (data.agent_name,))

        conn.commit()

    if workflow_msg_id is not None:
        try:
            from gnom_hub.agents.swarm.workflow_engine import handle_task_completion
            handle_task_completion(workflow_msg_id, data.result)
        except Exception as e:
            logging.getLogger(__name__).error("Failed handling workflow task completion: %s", e)

    signal_completion(data.context_id, data.agent_name, data.result)
    return {"status": "accepted"}

