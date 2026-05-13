#!/usr/bin/env python3
"""
GNOM-HUB — REST API des Gnom-Hub Speichers
===================================================
Konsolidierte Version: Importiert DB-Funktionen aus db.py (keine Duplikation).
Port: 3002
Läuft mit: uvicorn cortex_app:app --host 127.0.0.1 --port 3002

Agenten: Hermes, Tandem, Paperclip, OpenClaw, Agent Zero, Agent Launcher
Datenbank: /Users/landjunge/Documents/Antygravity/.cortex/db/*.json
"""

import json
import os
import subprocess
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ── Alles aus der zentralen db.py importieren ──
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import format_display_path, find_free_port, get_run_dir
from db import (
    read_db, write_db, generate_id, is_port_open, get_agent_status,
    check_openrouter_key, query_openrouter, get_openrouter_key,
    get_agents, reload_agents, save_agent, remove_agent,
    add_relation, query_relations, add_token, list_tokens,
    add_brainstorm, list_brainstorm, update_brainstorm_status,
    create_workflow, add_workflow_step, run_workflow, list_workflows,
    create_debate, add_argument, complete_debate, list_debates,
    get_agent_status, set_agent_status, list_agents_status,
    set_agent_activity, register_agent_online, set_agent_offline, send_to_agent,
    agent_think, agent_say, agent_do, agent_event,
    get_agent_database, list_agent_databases,
    king_speak, get_royal_chronicle,
    AGENTS, DB_DIR, DB_FILES, USER_HOME, ENV_FILE,
    CORTEX_URL, LAUNCHER_URL, PAPERCLIP_URL,
)

# ── FastAPI-App ──
app = FastAPI(
    title="GNOM-HUB API",
    description="Zentrales Gedaechtnis + Agenten-Kontrollzentrum (GNOM-HUB)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

# ── Konstanten (ausserhalb von db.py) ──
EXPRESS_URL = "http://127.0.0.1:3001"


# ═══════════════════════════════════════════
# PYDANTIC-MODELLE
# ═══════════════════════════════════════════

class MemoryCreate(BaseModel):
    type: str = "fact"
    source: str = "System"
    content: str
    tags: List[str] = []
    weight: int = 1
    depth: str = "archive"

class MCPExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}

class AgentActionRequest(BaseModel):
    agent_id: str
    action: str  # status, start, stop, query
    params: Dict[str, Any] = {}

class PaperclipTaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assignee_agent: Optional[str] = None

class OpenRouterRequest(BaseModel):
    prompt: str
    agent_name: str = "User"
    max_tokens: int = 1000

class AgentCreate(BaseModel):
    id: str
    name: str
    port: Optional[int] = None
    icon: str = "🤖"
    type: str = "Agent"
    description: str = ""
    status: str = "active"
    script_path: Optional[str] = None
    features: List[str] = []

class RelationCreate(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relation: str
    description: str = ""
    weight: float = 1.0

class TokenCreate(BaseModel):
    name: str
    type: str = "mcp_token"
    purpose: str = ""
    metadata: Dict[str, Any] = {}

# ── Per-Agent DB Models ──

class AgentThinkRequest(BaseModel):
    thought: str
    context: str = ""

class AgentSayRequest(BaseModel):
    message: str
    recipient: str = ""
    channel: str = ""

class AgentDoRequest(BaseModel):
    action: str
    result: str = ""
    tool: str = ""

class AgentEventRequest(BaseModel):
    event_type: str
    details: str = ""

# ── Royal Chronicle Model ──

class KingSpeakRequest(BaseModel):
    content: str
    channel: str = ""
    agent_target: str = ""


# ═══════════════════════════════════════════
# KERN-API ENDPOINTS
# ═══════════════════════════════════════════

@app.get("/")
def root():
    return {
        "message": "GNOM-HUB v0.1.0 — Memory & Tool Orchestrator for Local AI Agents",
        "version": "0.1.0",
        "database": format_display_path(DB_DIR),
        "agents_managed": list(AGENTS.keys()),
        "openrouter_configured": check_openrouter_key(),
    }

@app.get("/api/tables")
def list_tables():
    tables = []
    for name, path in DB_FILES.items():
        data = read_db(name)
        tables.append({"name": name, "count": len(data)})
    return {"tables": tables}

@app.get("/api/data/{table_name}")
def get_table_data(table_name: str, limit: int = Query(50, ge=1, le=1000)):
    if table_name not in DB_FILES:
        raise HTTPException(status_code=404, detail=f"Tabelle '{table_name}' nicht gefunden.")
    data = read_db(table_name)
    if data and "timestamp" in data[0]:
        data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"table": table_name, "data": data[:limit], "total": len(data)}

@app.post("/api/memory")
def add_memory(memory: MemoryCreate):
    data = read_db("memory")
    new_entry = {
        "id": generate_id("mem"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": memory.type,
        "source": memory.source,
        "content": memory.content,
        "tags": memory.tags,
        "weight": memory.weight,
        "reads": 0,
        "depth": memory.depth,
    }
    data.append(new_entry)
    write_db("memory", data)
    return {"id": new_entry["id"], "status": "added"}

@app.get("/api/memory/search")
def search_memory(query: str = Query(..., min_length=1), limit: int = 20):
    data = read_db("memory")
    results = []
    query_lower = query.lower()
    for entry in data:
        content = entry.get("content", "").lower()
        tags = [tag.lower() for tag in entry.get("tags", [])]
        if query_lower in content or any(query_lower in tag for tag in tags):
            results.append(entry)
        if len(results) >= limit:
            break
    return {"query": query, "results": results}

@app.get("/api/stats")
def get_stats():
    stats = {}
    for name in DB_FILES.keys():
        data = read_db(name)
        stats[name] = len(data)
    stats["agents_total"] = len(AGENTS)
    stats["agents_online"] = sum(
        1 for a in AGENTS if AGENTS[a].get("port") and is_port_open(AGENTS[a]["port"])
    )
    stats["openrouter"] = "configured" if check_openrouter_key() else "missing"
    return stats


# ═══════════════════════════════════════════
# AGENTEN-REGISTRY API (aus agents.json)
# ═══════════════════════════════════════════

@app.get("/api/agents/registry")
def list_agents_registry():
    """Liste alle registrierten Agenten aus agents.json + Live-Status."""
    data = read_db("agents")
    live = {a["agent_id"]: a for a in list_agents_status()}
    for item in data:
        aid = item.get("id", "")
        if aid in live:
            item["live_status"] = live[aid].get("status", "unknown")
            item["live_activity"] = live[aid].get("activity", "")
        else:
            item["live_status"] = "unbekannt"
            item["live_activity"] = ""
    return {"agents": data, "total": len(data)}

@app.post("/api/agents/registry")
def add_agent_to_registry(agent: AgentCreate):
    """Neuen Agenten in der Registry speichern."""
    agent_data = {
        "id": agent.id,
        "name": agent.name,
        "port": agent.port,
        "icon": agent.icon,
        "type": agent.type,
        "description": agent.description,
        "status": agent.status,
        "created": datetime.utcnow().isoformat() + "Z",
    }
    if agent.script_path:
        agent_data["script_path"] = agent.script_path
    if agent.features:
        agent_data["features"] = agent.features
    result = save_agent(agent_data)
    return {"status": "saved", "agent": result, "note": "Neuladen ueber /api/agents/registry/reload"}

@app.post("/api/agents/registry/reload")
def reload_agents_registry():
    """Erzwinge Neuladen der Agenten aus der Datenbank."""
    reload_agents()
    return {"status": "reloaded", "agents": len(get_agents())}

@app.delete("/api/agents/registry/{agent_id}")
def delete_agent_from_registry(agent_id: str):
    """Entferne einen Agenten aus der Registry."""
    removed = remove_agent(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' nicht gefunden")
    return {"status": "removed", "agent_id": agent_id}


# ═══════════════════════════════════════════
# RELATIONS-API
# ═══════════════════════════════════════════

@app.get("/api/relations")
def get_relations(
    entity_type: str = "",
    entity_id: str = "",
    relation: str = "",
    direction: str = Query("both", pattern="^(source|target|both)$"),
):
    """Suche Beziehungen mit optionalen Filtern."""
    results = query_relations(
        entity_type=entity_type,
        entity_id=entity_id,
        relation=relation,
        direction=direction,
    )
    return {"relations": results, "count": len(results)}

@app.post("/api/relations")
def create_relation(rel: RelationCreate):
    """Erstelle eine neue Beziehung zwischen zwei Entitäten."""
    entry = add_relation(
        source_type=rel.source_type,
        source_id=rel.source_id,
        target_type=rel.target_type,
        target_id=rel.target_id,
        relation=rel.relation,
        description=rel.description,
        weight=rel.weight,
    )
    return {"status": "created", "relation": entry}


# ═══════════════════════════════════════════
# TOKENS-API
# ═══════════════════════════════════════════

@app.get("/api/tokens")
def get_tokens(token_type: str = "", status: str = ""):
    """Liste Tokens mit optionalem Filter."""
    results = list_tokens(token_type=token_type, status=status)
    return {"tokens": results, "count": len(results)}

@app.post("/api/tokens")
def create_token(token: TokenCreate):
    """Erstelle einen neuen Token-Eintrag."""
    entry = add_token(
        name=token.name,
        token_type=token.type,
        purpose=token.purpose,
        metadata=token.metadata,
    )
    return {"status": "created", "token": entry}


# ═══════════════════════════════════════════
# AGENTEN-API
# ═══════════════════════════════════════════

@app.get("/api/agents")
def list_agents():
    results = {}
    for agent_id, agent in AGENTS.items():
        status = get_agent_status(agent_id)
        results[agent_id] = status
    return {
        "agents": results,
        "total": len(results),
        "online": sum(1 for a in results.values() if a.get("online", False)),
    }

class AgentStatusUpdate(BaseModel):
    status: str = "idle"  # idle | working | waiting | error | offline
    activity: str = ""
    pid: int = None
    port: int = None

class AgentCommand(BaseModel):
    message: str
    source: str = "cortex-hub"

@app.get("/api/agents/status")
def api_agents_status(status: str = ""):
    """Liste alle Agenten mit Live-Status. Filter: idle|working|waiting|error|offline"""
    results = list_agents_status(status_filter=status)
    return {"agents": results, "count": len(results), "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.get("/api/agents/status/{agent_id}")
def api_agent_status_single(agent_id: str):
    """Hole Live-Status eines bestimmten Agenten."""
    st = get_agent_status(agent_id)
    return {"agent": st}

@app.post("/api/agents/status/{agent_id}")
def api_agent_status_update(agent_id: str, req: AgentStatusUpdate):
    """Aktualisiere Status eines Agenten. Agent registriert sich automatisch."""
    st = set_agent_status(agent_id, status=req.status, activity=req.activity, pid=req.pid, port=req.port)
    return {"status": "updated", "agent": st}

@app.post("/api/agents/status/{agent_id}/activity")
def api_agent_activity(agent_id: str, req: AgentCommand):
    """Kurzbefehl: aktualisiere nur die Activity eines Agenten."""
    st = set_agent_activity(agent_id, req.message)
    return {"status": "activity_set", "agent": st}

@app.post("/api/agents/status/{agent_id}/online")
def api_agent_online(agent_id: str, req: AgentStatusUpdate):
    """Agent meldet sich online."""
    st = register_agent_online(agent_id, pid=req.pid, port=req.port)
    return {"status": "online", "agent": st}

@app.post("/api/agents/status/{agent_id}/offline")
def api_agent_offline(agent_id: str):
    """Setze Agent auf offline."""
    st = set_agent_offline(agent_id)
    return {"status": "offline", "agent": st}


@app.get("/api/agents/databases")
def api_list_agent_databases():
    """Liste alle vorhandenen Per-Agent-Datenbanken."""
    return list_agent_databases()


@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: str):
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' nicht gefunden")
    return get_agent_status(agent_id)

@app.post("/api/agents/{agent_id}/action")
def agent_action(agent_id: str, req: AgentActionRequest):
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' nicht gefunden")

    agent = AGENTS[agent_id]
    action = req.action

    if action == "status":
        return get_agent_status(agent_id)

    # ── Agent Launcher Aktionen ──
    if agent_id == "agentlauncher":
        if action == "start":
            result = start_launcher()
            if result.get("success"):
                add_memory(MemoryCreate(
                    type="event", source="GNOM-HUB",
                    content=f"Agent Launcher gestartet: {result.get('message', '')}",
                    tags=["agentlauncher", "start"],
                ))
            return result
        elif action == "stop":
            result = stop_launcher()
            if result.get("success"):
                add_memory(MemoryCreate(
                    type="event", source="GNOM-HUB",
                    content=f"Agent Launcher gestoppt: {result.get('message', '')}",
                    tags=["agentlauncher", "stop"],
                ))
            return result
        elif action == "restart":
            stop_result = stop_launcher()
            time.sleep(1)
            start_result = start_launcher()
            return {"stop": stop_result, "start": start_result, "success": start_result.get("success", False)}
        elif action == "query":
            try:
                r = requests.get(f"{LAUNCHER_URL}/", timeout=2)
                return {"status": r.status_code, "data": r.text[:500]}
            except Exception as e:
                return {"message": "Launcher nicht per HTTP erreichbar", "error": str(e)}

    # ── Paperclip Aktionen ──
    elif action == "query" and agent_id == "paperclip":
        endpoint = req.params.get("endpoint", "/api/health")
        try:
            r = requests.get(f"{PAPERCLIP_URL}{endpoint}", timeout=5)
            return {
                "status": r.status_code,
                "data": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:500]
            }
        except Exception as e:
            return {"error": str(e)}

    # ── OpenClaw Aktionen ──
    elif action == "query" and agent_id == "openclaw":
        try:
            r = requests.get(f"http://127.0.0.1:{agent['port']}/health", timeout=3)
            return {"status": r.status_code, "data": r.text[:500]}
        except Exception as e:
            return {"error": str(e)}

    # ── Starte Agent ──
    elif action == "start":
        try:
            if agent_id == "tandem":
                tandem_dir = os.path.join(USER_HOME, "tandem-browser")
                if os.path.exists(tandem_dir):
                    subprocess.Popen(["npm", "start"], cwd=tandem_dir)
                    return {"message": f"Starte {agent['name']}..."}
                else:
                    return {"error": "Tandem-Verzeichnis nicht gefunden"}
            elif agent_id == "agentzero":
                subprocess.Popen(["/usr/local/bin/docker", "start", "agent-zero"])
                return {"message": f"Starte {agent['name']}..."}
            else:
                return {"message": f"Agent {agent['name']} kann nicht automatisch gestartet werden"}
        except Exception as e:
            return {"error": str(e)}

    # ── Stoppe Agent ──
    elif action == "stop":
        try:
            port = agent["port"]
            os.system(f"lsof -iTCP:{port} -sTCP:LISTEN -t 2>/dev/null | xargs kill 2>/dev/null")
            return {"message": f"Stoppe {agent['name']}..."}
        except Exception as e:
            return {"error": str(e)}

    raise HTTPException(status_code=400, detail=f"Unbekannte Aktion: {action} fuer Agent {agent_id}")


# ═══════════════════════════════════════════
# LAUNCHER-MANAGEMENT
# ═══════════════════════════════════════════

def get_launcher_process_id() -> Optional[int]:
    """Ermittelt PID des laufenden agent_launcher.py Prozesses."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "agent_launcher.py"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except:
        pass
    return None

def start_launcher() -> Dict:
    """Startet den Agent Launcher via subprocess."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(('127.0.0.1', 8900))
        sock.close()
        if result == 0:
            return {"success": True, "message": "Agent Launcher laeuft bereits auf Port 8900"}
    except:
        sock.close()

    pid = get_launcher_process_id()
    if pid:
        return {"success": True, "message": f"Agent Launcher laeuft bereits (PID {pid})"}

    launcher_path = AGENTS["agentlauncher"].get("script_path", "")
    if not launcher_path or not os.path.exists(launcher_path):
        return {"error": f"Script nicht gefunden: {launcher_path}", "success": False}

    try:
        proc = subprocess.Popen(
            ["python3", "-B", launcher_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"success": True, "message": f"Agent Launcher gestartet (PID {proc.pid})", "pid": proc.pid}
    except Exception as e:
        return {"error": f"Konnte Launcher nicht starten: {str(e)}", "success": False}

def stop_launcher() -> Dict:
    """Stoppt den Agent Launcher Prozess."""
    pid = get_launcher_process_id()
    if not pid:
        return {"success": True, "message": "Agent Launcher laeuft nicht"}

    try:
        os.kill(pid, 15)
        time.sleep(1)
        still_running = get_launcher_process_id()
        if still_running:
            os.kill(still_running, 9)
            return {"success": True, "message": f"Agent Launcher (PID {still_running}) mit SIGKILL beendet"}
        return {"success": True, "message": f"Agent Launcher (PID {pid}) gestoppt"}
    except ProcessLookupError:
        return {"success": True, "message": "Agent Launcher war bereits beendet"}
    except Exception as e:
        return {"error": str(e), "success": False}


# ═══════════════════════════════════════════
# PAPERCLIP-INTEGRATION
# ═══════════════════════════════════════════

@app.get("/api/paperclip/health")
def paperclip_health():
    try:
        r = requests.get(f"{PAPERCLIP_URL}/api/health", timeout=5)
        return {"status": "ok" if r.status_code == 200 else "error", "data": r.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/paperclip/companies")
def paperclip_companies():
    try:
        r = requests.get(f"{PAPERCLIP_URL}/api/companies", timeout=5)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/paperclip/issues")
def paperclip_issues():
    try:
        r = requests.get(f"{PAPERCLIP_URL}/api/companies", timeout=5)
        if r.status_code != 200 or not r.json():
            return {"error": "Keine Paperclip Company gefunden"}
        company_id = r.json()[0]["id"]
        r2 = requests.get(f"{PAPERCLIP_URL}/api/companies/{company_id}/issues", timeout=5)
        return {"company_id": company_id, "issues": r2.json() if r2.status_code == 200 else []}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/paperclip/issues")
def paperclip_create_issue(req: PaperclipTaskCreate):
    try:
        r = requests.get(f"{PAPERCLIP_URL}/api/companies", timeout=5)
        if r.status_code != 200 or not r.json():
            return {"error": "Keine Paperclip Company gefunden"}
        company = r.json()[0]
        company_id = company["id"]
        project_id = company.get("projectId") or "228d7537-3375-4cc9-ba92-229558f7a7ea"

        issue_data = {
            "title": req.title,
            "description": req.description,
            "projectId": project_id,
            "status": "todo",
            "priority": req.priority,
        }
        if req.assignee_agent:
            agent_r = requests.get(f"{PAPERCLIP_URL}/api/companies/{company_id}/agents", timeout=5)
            if agent_r.status_code == 200:
                agents = agent_r.json()
                for a in agents:
                    if req.assignee_agent.lower() in a.get("name", "").lower():
                        issue_data["assigneeAgentId"] = a["id"]
                        break

        r2 = requests.post(
            f"{PAPERCLIP_URL}/api/companies/{company_id}/issues",
            json=issue_data,
            timeout=5,
        )
        return {"status": "created" if r2.status_code in (200, 201) else "error", "data": r2.json()}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════
# OPENROUTER-INTEGRATION
# ═══════════════════════════════════════════

@app.get("/api/openrouter/status")
def openrouter_status():
    return {"configured": check_openrouter_key()}

@app.post("/api/openrouter/query")
def openrouter_query(req: OpenRouterRequest):
    result = query_openrouter(req.prompt, req.agent_name)
    if result.get("success"):
        add_memory(MemoryCreate(
            type="llm_query",
            source=f"GNOM-HUB-{req.agent_name}",
            content=f"Prompt: {req.prompt[:100]}... | Response: {result['response'][:100]}...",
            tags=["openrouter", "nemotron", req.agent_name.lower()],
        ))
    return result


# ═══════════════════════════════════════════
# MCP (MODEL CONTEXT PROTOCOL) SIMULATION
# ═══════════════════════════════════════════

@app.get("/api/mcp/tools")
def list_mcp_tools():
    return {
        "tools": [
            {"name": "cortex_search", "description": "Durchsuche den Gnom-Hub Speicher nach Eintraegen", "parameters": {"query": "string"}},
            {"name": "cortex_store", "description": "Speichere einen Eintrag im Gnom-Hub Speicher", "parameters": {"content": "string", "type": "string", "tags": "string"}},
            {"name": "cortex_stats", "description": "Statistiken aller Gnom-Hub-Datenbanken abrufen"},
            {"name": "paperclip_health", "description": "Pruefe ob Paperclip online ist"},
            {"name": "paperclip_issues", "description": "Liste alle Paperclip Issues auf"},
            {"name": "agent_status", "description": "Status aller Agenten abrufen", "parameters": {"agent_id": "string (optional)"}},
            {"name": "agentlauncher_start", "description": "Starte den Agent Launcher auf Port 8900"},
            {"name": "agentlauncher_stop", "description": "Stoppe den Agent Launcher"},
            {"name": "agentlauncher_restart", "description": "Starte den Agent Launcher neu"},
            {"name": "agentlauncher_pid", "description": "Zeige die PID des laufenden Agent Launcher"},
            {"name": "openrouter_query", "description": "Stelle eine Frage an Nemotron via OpenRouter", "parameters": {"prompt": "string"}},
            {"name": "agent_registry", "description": "Liste alle registrierten Agenten aus agents.json"},
            {"name": "agent_registry_add", "description": "Neuen Agenten registrieren", "parameters": {"id": "string", "name": "string", "port": "int", "type": "string", "description": "string"}},
            {"name": "relation_query", "description": "Suche Beziehungen zwischen Entitaeten", "parameters": {"entity_id": "string (optional)", "relation": "string (optional)"}},
            {"name": "relation_add", "description": "Neue Beziehung erstellen", "parameters": {"source_type": "string", "source_id": "string", "target_type": "string", "target_id": "string", "relation": "string"}},
            {"name": "token_list", "description": "Liste alle Tokens auf"},
            {"name": "token_add", "description": "Neuen Token erstellen", "parameters": {"name": "string", "type": "string", "purpose": "string"}},
        ],
        "count": 17,
        "mcp_server": "GNOM-HUB Memory",
        "version": "0.1.0",
    }

@app.post("/api/mcp/execute")
def execute_mcp_tool(req: MCPExecuteRequest):
    tool = req.tool_name
    args = req.arguments

    if tool == "cortex_search":
        query = args.get("query", "")
        if not query:
            return {"error": "query ist erforderlich"}
        result = search_memory(query=query, limit=20)
        return {"success": True, "data": result["results"]}

    elif tool == "cortex_store":
        content = args.get("content", "")
        if not content:
            return {"error": "content ist erforderlich"}
        entry_type = args.get("type", "fact")
        tags_str = args.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        result = add_memory(MemoryCreate(type=entry_type, source="MCP", content=content, tags=tags))
        return {"success": True, "id": result["id"]}

    elif tool == "cortex_stats":
        return {"success": True, "stats": get_stats()}

    elif tool == "paperclip_health":
        data = paperclip_health()
        return {"success": data.get("status") == "ok", "data": data}

    elif tool == "paperclip_issues":
        data = paperclip_issues()
        return {"success": "error" not in data, "data": data}

    elif tool == "agent_status":
        agent_id = args.get("agent_id", "")
        if agent_id:
            if agent_id not in AGENTS:
                return {"error": f"Unbekannter Agent: {agent_id}"}
            return {"success": True, "data": get_agent_status(agent_id)}
        agents = list_agents()
        return {"success": True, "data": agents}

    elif tool == "agentlauncher_start":
        result = start_launcher()
        if result.get("success"):
            add_memory(MemoryCreate(
                type="event", source="MCP",
                content=result.get("message", "Agent Launcher gestartet"),
                tags=["agentlauncher", "start", "mcp"],
            ))
        return result

    elif tool == "agentlauncher_stop":
        result = stop_launcher()
        if result.get("success"):
            add_memory(MemoryCreate(
                type="event", source="MCP",
                content=result.get("message", "Agent Launcher gestoppt"),
                tags=["agentlauncher", "stop", "mcp"],
            ))
        return result

    elif tool == "agentlauncher_restart":
        stop_result = stop_launcher()
        time.sleep(1)
        start_result = start_launcher()
        return {"stop": stop_result, "start": start_result}

    elif tool == "agentlauncher_pid":
        from db import is_port_open as check_port
        pid = get_launcher_process_id()
        if pid:
            return {"success": True, "pid": pid, "running": True}
        else:
            return {"success": True, "pid": None, "running": False}

    elif tool == "openrouter_query":
        prompt = args.get("prompt", "")
        if not prompt:
            return {"error": "prompt ist erforderlich"}
        result = query_openrouter(prompt, "MCP")
        return result

    elif tool == "agent_registry":
        data = read_db("agents")
        return {"success": True, "agents": data}

    elif tool == "agent_registry_add":
        agent_id = args.get("id", "")
        name = args.get("name", "")
        if not agent_id or not name:
            return {"error": "id und name sind erforderlich"}
        agent_data = {
            "id": agent_id,
            "name": name,
            "port": args.get("port"),
            "type": args.get("type", "Agent"),
            "description": args.get("description", ""),
            "status": "active",
            "created": datetime.utcnow().isoformat() + "Z",
        }
        saved = save_agent(agent_data)
        reload_agents()
        return {"success": True, "agent": saved}

    elif tool == "relation_query":
        results = query_relations(
            entity_type=args.get("entity_type", ""),
            entity_id=args.get("entity_id", ""),
            relation=args.get("relation", ""),
        )
        return {"success": True, "relations": results}

    elif tool == "relation_add":
        entry = add_relation(
            source_type=args["source_type"],
            source_id=args["source_id"],
            target_type=args["target_type"],
            target_id=args["target_id"],
            relation=args["relation"],
            description=args.get("description", ""),
        )
        return {"success": True, "relation": entry}

    elif tool == "token_list":
        tokens = list_tokens(
            token_type=args.get("token_type", ""),
            status=args.get("status", ""),
        )
        return {"success": True, "tokens": tokens}

    elif tool == "token_add":
        entry = add_token(
            name=args["name"],
            token_type=args.get("type", "mcp_token"),
            purpose=args.get("purpose", ""),
        )
        return {"success": True, "token": entry}

    return {"error": f"Unbekanntes Tool: {tool}"}


# ═══════════════════════════════════════════
# AGENT LAUNCHER SPEZIFISCHE ENDPOINTS
# ═══════════════════════════════════════════

@app.get("/api/agentlauncher/status")
def launcher_status():
    pid = get_launcher_process_id()
    port_open = is_port_open(8900)
    status = {
        "name": "Agent Launcher",
        "port": 8900,
        "port_open": port_open,
        "process_running": pid is not None,
        "pid": pid,
        "script_path": AGENTS["agentlauncher"].get("script_path", ""),
        "http_reachable": False,
    }
    if port_open:
        try:
            r = requests.get(f"{LAUNCHER_URL}/", timeout=2)
            status["http_reachable"] = True
            status["http_status"] = r.status_code
            status["response_preview"] = r.text[:200]
        except:
            status["http_reachable"] = False
    return status

@app.post("/api/agentlauncher/start")
def launcher_start():
    result = start_launcher()
    if result.get("success"):
        add_memory(MemoryCreate(
            type="event", source="GNOM-HUB API",
            content=f"Agent Launcher gestartet: {result.get('message', '')}",
            tags=["agentlauncher", "start", "api"],
        ))
    return result

@app.post("/api/agentlauncher/stop")
def launcher_stop():
    result = stop_launcher()
    if result.get("success"):
        add_memory(MemoryCreate(
            type="event", source="GNOM-HUB API",
            content=f"Agent Launcher gestoppt: {result.get('message', '')}",
            tags=["agentlauncher", "stop", "api"],
        ))
    return result

@app.post("/api/agentlauncher/restart")
def launcher_restart():
    stop_result = stop_launcher()
    time.sleep(1)
    start_result = start_launcher()
    return {"stop": stop_result, "start": start_result}


# ═══════════════════════════════════════════
# BRAINSTORMING API (@bs-Trigger)
# ═══════════════════════════════════════════

class BrainstormCreate(BaseModel):
    content: str
    source: str = "chat"
    tags: List[str] = []
    category: str = "general"

class BrainstormStatus(BaseModel):
    status: str  # fresh | explored | developed | implemented | archived

@app.post("/api/brainstorming")
def api_add_brainstorm(bs: BrainstormCreate):
    """Erfasse eine Brainstorming-Idee (@bs-Trigger)."""
    entry = add_brainstorm(
        content=bs.content,
        source=bs.source,
        tags=bs.tags,
        category=bs.category,
    )
    return {"status": "added", "entry": entry, "hint": "Nutze @bs <idee> im Chat"}

@app.get("/api/brainstorming")
def api_list_brainstorm(
    status: str = "",
    category: str = "",
    tags: str = "",
):
    """Liste Brainstorming-Ideen. Trenne Tags mit Komma."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    results = list_brainstorm(status=status, category=category, tags=tag_list)
    return {"ideas": results, "count": len(results), "status_filter": status or "alle"}

@app.put("/api/brainstorming/{bs_id}/status")
def api_update_brainstorm_status(bs_id: str, req: BrainstormStatus):
    """Aktualisiere Status einer Idee."""
    ok = update_brainstorm_status(bs_id, req.status)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Idee '{bs_id}' nicht gefunden")
    return {"status": "updated", "id": bs_id, "new_status": req.status}


# ═══════════════════════════════════════════
# WORKFLOWS API
# ═══════════════════════════════════════════

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    trigger: str = "manual"
    steps: List[Dict[str, Any]] = []

class WorkflowStepAdd(BaseModel):
    step: Dict[str, Any]

@app.post("/api/workflows")
def api_create_workflow(wf: WorkflowCreate):
    """Erstelle einen neuen Workflow."""
    entry = create_workflow(
        name=wf.name,
        description=wf.description,
        trigger=wf.trigger,
        steps=wf.steps,
    )
    return {"status": "created", "workflow": entry}

@app.get("/api/workflows")
def api_list_workflows(status: str = ""):
    """Liste alle Workflows."""
    results = list_workflows(status=status)
    return {"workflows": results, "count": len(results)}

@app.post("/api/workflows/{wf_id}/steps")
def api_add_workflow_step(wf_id: str, req: WorkflowStepAdd):
    """Füge einen Schritt zu einem Workflow hinzu."""
    ok = add_workflow_step(wf_id, req.step)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Workflow '{wf_id}' nicht gefunden")
    return {"status": "step_added", "workflow_id": wf_id}

@app.post("/api/workflows/{wf_id}/run")
def api_run_workflow(wf_id: str):
    """Führe einen Workflow aus."""
    result = run_workflow(wf_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ═══════════════════════════════════════════
# @bsa DEBATES API (Multi-Agent-Diskussion)
# ═══════════════════════════════════════════

class DebateCreate(BaseModel):
    topic: str
    initiator: str = "User"

class ArgumentAdd(BaseModel):
    agent_name: str
    role: str  # pro | contra | researcher | validator
    content: str
    sources: List[str] = []

class DebateConclusion(BaseModel):
    conclusion: str

@app.post("/api/bsa/debate")
def api_create_debate(deb: DebateCreate):
    """Starte eine neue Agenten-Debatte (@bsa-Trigger)."""
    entry = create_debate(topic=deb.topic, initiator=deb.initiator)
    return {"status": "debate_started", "debate": entry, "hint": "Agenten werden aktiviert. Nutze POST /api/bsa/debate/{id}/arg fuer Argumente."}

@app.get("/api/bsa/debates")
def api_list_debates(status: str = ""):
    """Liste alle Debatten."""
    results = list_debates(status=status)
    return {"debates": results, "count": len(results)}

@app.get("/api/bsa/debate/{debate_id}")
def api_get_debate(debate_id: str):
    """Hole eine Debatte mit allen Argumenten."""
    data = read_db("debates")
    for d in data:
        if d["id"] == debate_id:
            return d
    raise HTTPException(status_code=404, detail=f"Debatte '{debate_id}' nicht gefunden")

@app.post("/api/bsa/debate/{debate_id}/arg")
def api_add_argument(debate_id: str, arg: ArgumentAdd):
    """Füge ein Agenten-Argument zur Debatte hinzu."""
    result = add_argument(
        debate_id=debate_id,
        agent_name=arg.agent_name,
        role=arg.role,
        content=arg.content,
        sources=arg.sources,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"status": "argument_added", "argument": result}

@app.post("/api/bsa/debate/{debate_id}/complete")
def api_complete_debate(debate_id: str, req: DebateConclusion):
    """Schliesse eine Debatte mit Conclusio ab."""
    ok = complete_debate(debate_id, req.conclusion)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Debatte '{debate_id}' nicht gefunden")
    return {"status": "completed", "debate_id": debate_id, "conclusion": req.conclusion}

@app.post("/api/bsa/debate/{debate_id}/launch")
def api_launch_bsa_agents(debate_id: str):
    """Starte die Agenten-Diskussion fuer eine Debatte (@bsa)."""
    data = read_db("debates")
    debate = None
    for d in data:
        if d["id"] == debate_id:
            debate = d
            break
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debatte '{debate_id}' nicht gefunden")

    # Agenten-Personas fuer die Debatte
    topic = debate["topic"]
    agents = [
        {"name": "Argus",   "role": "pro",       "prompt": f"Du bist Argus, der Pro-Argumentator. Vertrittst die These: {topic}. Argumentiere sachlich mit Fakten."},
        {"name": "Kritik",  "role": "contra",     "prompt": f"Du bist Kritik, der Contra-Analyst. Hinterfrage die These: {topic}. Zeige Risiken und Schwachstellen."},
        {"name": "Hermes",  "role": "researcher", "prompt": f"Du bist Hermes, der Rechercheur. Suche Fakten und Quellen zum Thema: {topic}. Liefere Belege."},
        {"name": "Valdis",  "role": "validator",  "prompt": f"Du bist Valdis, der Validierer. Pruefe beide Seiten zur These: {topic}. Waege Argumente und Risiken ab."},
    ]

    arguments = []
    # Jeden Agenten via OpenRouter eine Position formulieren lassen
    for agent in agents:
        result = query_openrouter(agent["prompt"], agent_name=agent["name"])
        if result.get("success"):
            arg_entry = add_argument(
                debate_id=debate_id,
                agent_name=agent["name"],
                role=agent["role"],
                content=result["response"],
                sources=[result.get("model", "")],
            )
            arguments.append(arg_entry)

    # Zusammenfassung durch aggregierenden Agenten
    if len(arguments) >= 3:
        summary_prompt = (
            f"Fasse die folgende Debatte zum Thema '{topic}' zusammen. "
            f"Erstelle eine ausgewogene Conclusio basierend auf allen Argumenten.\n\n"
        )
        for a in arguments:
            summary_prompt += f"[{a['agent']} / {a['role']}]: {a['content'][:500]}\n---\n"
        summary_prompt += "\nWas ist die Conclusio?"

        summary = query_openrouter(summary_prompt, agent_name="Hermes-Aggregator")
        if summary.get("success"):
            complete_debate(debate_id, summary["response"])
            return {
                "status": "debate_completed",
                "debate_id": debate_id,
                "arguments": len(arguments),
                "conclusion": summary["response"],
            }

    return {
        "status": "debate_started",
        "debate_id": debate_id,
        "arguments_added": len(arguments),
        "note": "Debatte manuell abschliessen via POST /api/bsa/debate/{id}/complete",
    }


# ═══════════════════════════════════════════


# ═══════════════════════════════════════════
# AGENTEN-KOMMANDOZENTRALE (Dropdown + Eingabe)
# ═══════════════════════════════════════════

@app.post("/api/agents/command/{agent_id}")
def api_agent_command(agent_id: str, cmd: AgentCommand):
    """Sende einen Befehl an einen registrierten Agenten."""
    # Zuerst Activity updaten
    set_agent_activity(agent_id, f"cmd: {cmd.message[:50]}")
    
    # Versuche via HTTP zu senden
    result = send_to_agent(agent_id, cmd.message)
    if result.get("success"):
        return {"status": "sent", "agent": agent_id, "response": result.get("response", "")}
    
    # Fallback: Als Event in Memory speichern
    add_memory(MemoryCreate(
        type="agent_command",
        source=f"GNOM-HUB",
        content=f"[BEFEHL an {agent_id}]: {cmd.message}",
        tags=["agent", "command", agent_id],
    ))
    return {
        "status": "enqueued",
        "agent": agent_id,
        "note": f"Agent nicht per HTTP erreichbar, Befehl als Event gespeichert",
        "detail": result.get("error", ""),
    }


# ═══════════════════════════════════════════
# PER-AGENT DATENBANKEN (Gedacht/Gesagt/Getan/Events)
# ═══════════════════════════════════════════

@app.post("/api/agents/{agent_id}/think")
def api_agent_think(agent_id: str, req: AgentThinkRequest):
    """Logge einen Gedanken eines Agenten."""
    entry = agent_think(agent_id, req.thought, req.context)
    return {"status": "logged", "entry": entry}

@app.post("/api/agents/{agent_id}/say")
def api_agent_say(agent_id: str, req: AgentSayRequest):
    """Logge, was ein Agent gesagt hat."""
    entry = agent_say(agent_id, req.message, req.recipient, req.channel)
    return {"status": "logged", "entry": entry}

@app.post("/api/agents/{agent_id}/do")
def api_agent_do(agent_id: str, req: AgentDoRequest):
    """Logge, was ein Agent getan hat."""
    entry = agent_do(agent_id, req.action, req.result, req.tool)
    return {"status": "logged", "entry": entry}

@app.post("/api/agents/{agent_id}/event")
def api_agent_event(agent_id: str, req: AgentEventRequest):
    """Logge ein Ereignis (was passiert ist)."""
    entry = agent_event(agent_id, req.event_type, req.details)
    return {"status": "logged", "entry": entry}

@app.get("/api/agents/{agent_id}/db/{db_name}")
def api_get_agent_database(agent_id: str, db_name: str, limit: int = Query(50, ge=1, le=1000)):
    """Lese eine Per-Agent-Datenbank (thoughts|said|done|events)."""
    return get_agent_database(agent_id, db_name, limit)


# ═══════════════════════════════════════════
# KÖNIGLICHE CHRONIK (Alle Worte des Königs)
# ═══════════════════════════════════════════

@app.post("/api/royal/speak")
def api_king_speak(req: KingSpeakRequest):
    """Logge ein Wort des Königs."""
    entry = king_speak(req.content, req.channel, req.agent_target)
    return {"status": "logged", "entry": entry}

@app.get("/api/royal/chronicle")
def api_get_royal_chronicle(limit: int = Query(100, ge=1, le=5000)):
    """Lese die königliche Chronik — neueste zuerst."""
    return get_royal_chronicle(limit)


# ═══════════════════════════════════════════
# GNOM-HUB — HTML Dashboard
# ═══════════════════════════════════════════

@app.get("/hub")
@app.get("/cortex-hub")
def cortex_hub():
    """GNOM-HUB Dashboard — Live-Status aller Agenten + Kommandozentrale."""
    html = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gnom-Hub — @bsa Dashboard</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        background: #0a0a0f;
        color: #c8d6e5;
        font-family: 'Space Grotesk', sans-serif;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    header {
        display: flex; justify-content: space-between; align-items: center;
        padding: 20px 0; border-bottom: 1px solid #1a1a2e; margin-bottom: 30px;
    }
    h1 {
        font-size: 28px; font-weight: 700;
        background: linear-gradient(135deg, #00d2ff, #7b2ff7);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    h1 span { background: none; color: #536878; font-weight: 400; }
    .status-badge {
        padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600;
    }
    .badge-online { background: #0a3d2a; color: #4ade80; border: 1px solid #166534; }
    .badge-offline { background: #3d0a0a; color: #f87171; border: 1px solid #7f1d1d; }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    
    .card {
        background: #111122; border-radius: 16px; padding: 24px;
        border: 1px solid #1a1a2e; position: relative; overflow: hidden;
    }
    .card h2 {
        font-size: 16px; font-weight: 600; margin-bottom: 16px;
        color: #8899aa; text-transform: uppercase; letter-spacing: 1px;
    }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    
    /* Slideshow */
    .slideshow { position: relative; min-height: 300px; }
    .slide {
        display: none; animation: fadeIn 0.5s ease;
    }
    .slide.active { display: block; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    .agent-card {
        background: #16162a; border-radius: 12px; padding: 16px;
        margin-bottom: 12px; border-left: 4px solid #334155;
        transition: all 0.3s ease;
    }
    .agent-card.status-idle { border-left-color: #64748b; }
    .agent-card.status-working { border-left-color: #3b82f6; }
    .agent-card.status-waiting { border-left-color: #f59e0b; }
    .agent-card.status-error { border-left-color: #ef4444; }
    .agent-card.status-offline { border-left-color: #1e293b; opacity: 0.6; }
    .agent-card.status-online { border-left-color: #22c55e; }
    
    .agent-name { font-weight: 700; font-size: 16px; color: #e2e8f0; }
    .agent-status { font-size: 12px; padding: 3px 8px; border-radius: 4px; font-weight: 600; }
    .s-idle { background: #1e293b; color: #94a3b8; }
    .s-working { background: #1e3a5f; color: #60a5fa; }
    .s-waiting { background: #422d0a; color: #fbbf24; }
    .s-error { background: #3d0a0a; color: #f87171; }
    .s-offline { background: #111111; color: #475569; }
    .s-online { background: #0a3d2a; color: #4ade80; }
    
    .agent-meta { font-size: 12px; color: #64748b; margin-top: 8px; font-family: 'JetBrains Mono', monospace; }
    .agent-activity { font-size: 13px; color: #94a3b8; margin-top: 4px; }
    
    .slide-nav {
        display: flex; gap: 8px; justify-content: center; margin-top: 16px;
    }
    .slide-dot {
        width: 8px; height: 8px; border-radius: 50%; background: #1e293b;
        cursor: pointer; transition: all 0.3s;
    }
    .slide-dot.active { background: #7b2ff7; width: 24px; border-radius: 4px; }
    
    /* Timeline */
    .timeline { position: relative; padding-left: 20px; }
    .timeline::before {
        content: ''; position: absolute; left: 0; top: 0; bottom: 0;
        width: 2px; background: #1a1a2e;
    }
    .tl-event { position: relative; padding: 8px 0 8px 20px; font-size: 13px; }
    .tl-event::before {
        content: ''; position: absolute; left: -5px; top: 12px;
        width: 10px; height: 10px; border-radius: 50%; background: #7b2ff7;
    }
    .tl-time { color: #475569; font-size: 11px; font-family: 'JetBrains Mono', monospace; }
    .tl-text { color: #c8d6e5; }
    
    /* Command Center */
    .cmd-row {
        display: flex; gap: 12px; margin-bottom: 12px;
    }
    .cmd-row select, .cmd-row input {
        background: #16162a; border: 1px solid #1e293b; border-radius: 8px;
        padding: 10px 14px; color: #e2e8f0; font-size: 14px;
        font-family: 'Space Grotesk', sans-serif; outline: none;
        transition: border-color 0.3s;
    }
    .cmd-row select:focus, .cmd-row input:focus { border-color: #7b2ff7; }
    .cmd-row select { flex: 0 0 200px; }
    .cmd-row input[type="text"] { flex: 1; }
    .cmd-row button {
        background: linear-gradient(135deg, #7b2ff7, #00d2ff);
        border: none; border-radius: 8px; padding: 10px 24px;
        color: white; font-weight: 600; cursor: pointer;
        transition: opacity 0.3s; font-family: 'Space Grotesk', sans-serif;
    }
    .cmd-row button:hover { opacity: 0.9; }
    .cmd-row button:disabled { opacity: 0.4; cursor: not-allowed; }
    
    .cmd-response {
        background: #0a0a14; border: 1px solid #1a1a2e; border-radius: 8px;
        padding: 12px; margin-top: 12px; font-family: 'JetBrains Mono', monospace;
        font-size: 12px; color: #94a3b8; min-height: 40px; display: none;
    }
    .cmd-response.show { display: block; }
    
    /* Stats */
    .stat-row { display: flex; gap: 16px; flex-wrap: wrap; }
    .stat {
        text-align: center; padding: 12px 20px; background: #16162a;
        border-radius: 10px; flex: 1; min-width: 80px;
    }
    .stat-value { font-size: 28px; font-weight: 700; color: #e2e8f0; }
    .stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; margin-top: 4px; }
    
    /* Auto-refresh */
    .refresh-bar {
        height: 3px; background: #1a1a2e; border-radius: 2px;
        margin-top: 20px; overflow: hidden;
    }
    .refresh-bar-inner {
        height: 100%; background: linear-gradient(90deg, #7b2ff7, #00d2ff);
        width: 0%; border-radius: 2px; transition: width 0.5s;
    }
    
    /* Brainstorming */
    .bs-item {
        background: #16162a; border-radius: 8px; padding: 12px;
        margin-bottom: 8px; font-size: 13px;
    }
    .bs-tag {
        display: inline-block; padding: 2px 8px; background: #1e293b;
        border-radius: 4px; font-size: 11px; color: #64748b; margin-right: 4px;
    }
</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>Gnom-Hub <span>@bsa</span></h1>
            <div style="font-size:13px;color:#64748b;margin-top:4px;">Gnom-Hub Kontrollzentrum</div>
        </div>
        <div id="live-badge" class="status-badge badge-online">🟢 Live</div>
    </header>

    <!-- Stats -->
    <div class="card" style="margin-bottom:20px;">
        <div class="stat-row" id="stats-row">
            <div class="stat"><div class="stat-value" id="stat-total">0</div><div class="stat-label">Agenten</div></div>
            <div class="stat"><div class="stat-value" id="stat-idle">0</div><div class="stat-label">Idle</div></div>
            <div class="stat"><div class="stat-value" id="stat-working">0</div><div class="stat-label">Arbeiten</div></div>
            <div class="stat"><div class="stat-value" id="stat-online">0</div><div class="stat-label">Online</div></div>
            <div class="stat"><div class="stat-value" id="stat-brainstorms">0</div><div class="stat-label">Ideen</div></div>
        </div>
    </div>

    <div class="grid">
        <!-- Slideshow: Agenten Live-Status -->
        <div class="card">
            <div class="card-header">
                <h2>📡 Agenten Live-Status</h2>
                <span style="font-size:12px;color:#64748b;" id="slide-counter">1/1</span>
            </div>
            <div class="slideshow" id="slideshow"></div>
            <div class="slide-nav" id="slide-nav"></div>
        </div>

        <!-- Timeline: Letzte Aktivitaeten -->
        <div class="card">
            <div class="card-header">
                <h2>⏱️ Letzte Aktivitaeten</h2>
            </div>
            <div class="timeline" id="timeline">
                <div style="color:#536878;text-align:center;padding:40px;">Lade Daten...</div>
            </div>
        </div>

        <!-- Kommandozentrale -->
        <div class="card" style="grid-column:1/-1;">
            <div class="card-header">
                <h2>🎮 Agenten-Kommandozentrale</h2>
            </div>
            <div class="cmd-row">
                <select id="agent-select">
                    <option value="">-- Agent auswaehlen --</option>
                </select>
                <input type="text" id="cmd-input" placeholder="Befehl eingeben... z.B. status, task list, run workflow XYZ">
                <button id="cmd-send" onclick="sendCommand()">🚀 Senden</button>
            </div>
            <div class="cmd-response" id="cmd-response"></div>
        </div>

        <!-- Brainstorming Quick-Add -->
        <div class="card">
            <div class="card-header">
                <h2>💡 @bs Brainstorming</h2>
            </div>
            <div class="cmd-row">
                <input type="text" id="bs-input" placeholder="Neue Idee... @bs HEXPIX integration" style="flex:1;">
                <button onclick="addBrainstorm()" style="background:linear-gradient(135deg,#f59e0b,#ef4444);border:none;border-radius:8px;padding:10px 20px;color:white;font-weight:600;cursor:pointer;font-family:'Space Grotesk',sans-serif;">+</button>
            </div>
            <div id="bs-list" style="margin-top:12px;"></div>
        </div>

        <!-- Letzte Debatten -->
        <div class="card">
            <div class="card-header">
                <h2>🗣️ Letzte @bsa Debatten</h2>
            </div>
            <div id="debate-list"></div>
        </div>
    </div>
    
    <div class="refresh-bar"><div class="refresh-bar-inner" id="refresh-bar"></div></div>
</div>

<script>
// ── State ──
let slideshowInterval, refreshTimer = 0;
const REFRESH_SECONDS = 10;

// ── API Helper ──
async function api(method, path, body) {
    const opts = { method, headers: {'Content-Type':'application/json'} };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(path, opts);
    return r.json();
}

// ── Slideshow ──
let currentSlide = 0, slides = [];

function renderSlideshow(agents) {
    const container = document.getElementById('slideshow');
    const nav = document.getElementById('slide-nav');
    
    if (!agents.length) {
        container.innerHTML = '<div class="slide active" style="text-align:center;padding:60px;color:#536878;">✨ Keine Agenten registriert<br><span style="font-size:13px;">Agenten registrieren sich automatisch via POST /api/agents/status/{id}/online</span></div>';
        nav.innerHTML = '';
        return;
    }
    
    slides = agents;
    container.innerHTML = '';
    nav.innerHTML = '';
    
    agents.forEach((a, i) => {
        const statusClass = a.status || 'unknown';
        const statusLabel = a.status ? a.status.toUpperCase() : '?';
        const statusBadgeClass = 's-' + statusClass;
        const cardClass = 'status-' + statusClass;
        const activity = a.activity || '—';
        const pid = a.pid || '—';
        const port = a.port || '—';
        const lastSeen = a.last_seen ? new Date(a.last_seen+'Z').toLocaleTimeString('de-DE') : '—';
        
        const div = document.createElement('div');
        div.className = 'slide' + (i === 0 ? ' active' : '');
        div.innerHTML = \`
            <div class="agent-card \${cardClass}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span class="agent-name">\${a.agent_id || '?'}</span>
                    <span class="agent-status \${statusBadgeClass}">\${statusLabel}</span>
                </div>
                <div class="agent-activity">\${activity}</div>
                <div class="agent-meta">PID: \${pid} | Port: \${port} | Zuletzt: \${lastSeen}</div>
            </div>
        \`;
        container.appendChild(div);
        
        const dot = document.createElement('div');
        dot.className = 'slide-dot' + (i === 0 ? ' active' : '');
        dot.onclick = () => goToSlide(i);
        nav.appendChild(dot);
    });
    
    document.getElementById('slide-counter').textContent = (currentSlide+1) + '/' + agents.length;
}

function goToSlide(n) {
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.slide-dot');
    slides.forEach((s, i) => s.classList.toggle('active', i === n));
    dots.forEach((d, i) => d.classList.toggle('active', i === n));
    currentSlide = n;
    document.getElementById('slide-counter').textContent = (n+1) + '/' + slides.length;
}

function nextSlide() {
    const slides = document.querySelectorAll('.slide');
    if (slides.length) goToSlide((currentSlide + 1) % slides.length);
}

// ── Timeline ──
async function loadTimeline() {
    try {
        const data = await api('GET', '/api/memory?limit=8');
        const items = data.memories || [];
        const container = document.getElementById('timeline');
        if (!items.length) {
            container.innerHTML = '<div style="color:#536878;text-align:center;padding:40px;">Keine Aktivitaeten</div>';
            return;
        }
        container.innerHTML = items.map(m => \`
            <div class="tl-event">
                <div class="tl-time">\${m.timestamp ? new Date(m.timestamp+'Z').toLocaleString('de-DE') : '—'}</div>
                <div class="tl-text">\${m.content ? m.content.substring(0,120) : '—'}</div>
            </div>
        \`).join('');
    } catch(e) {
        document.getElementById('timeline').innerHTML = '<div style="color:#ef4444;text-align:center;padding:40px;">Fehler: ' + e.message + '</div>';
    }
}

// ── Agenten-Status (für Slideshow) ──
async function loadAgentStatus() {
    try {
        const data = await api('GET', '/api/agents/status');
        const agents = data.agents || [];
        renderSlideshow(agents);
        
        // Stats
        document.getElementById('stat-total').textContent = agents.length;
        document.getElementById('stat-idle').textContent = agents.filter(a => a.status === 'idle').length;
        document.getElementById('stat-working').textContent = agents.filter(a => a.status === 'working').length;
        document.getElementById('stat-online').textContent = agents.filter(a => a.status === 'online' || a.status === 'idle' || a.status === 'working').length;
        
        // Dropdown befuellen
        const select = document.getElementById('agent-select');
        const currentVal = select.value;
        select.innerHTML = '<option value="">-- Agent auswaehlen --</option>' +
            agents.map(a => \`<option value="\${a.agent_id}">\${a.agent_id} (\${a.status})</option>\`).join('');
        if (currentVal) select.value = currentVal;
    } catch(e) {
        console.error('Agent status error:', e);
    }
}

// ── Brainstorming ──
async function loadBrainstorms() {
    try {
        const data = await api('GET', '/api/brainstorming');
        const ideas = data.ideas || [];
        document.getElementById('stat-brainstorms').textContent = ideas.length;
        document.getElementById('bs-list').innerHTML = ideas.slice(-5).reverse().map(bs => \`
            <div class="bs-item">
                <div>\${bs.content}</div>
                <div style="margin-top:6px;">
                    \${(bs.tags||[]).map(t => '<span class="bs-tag">#'+t+'</span>').join('')}
                    <span class="bs-tag" style="background:#2d1b69;">\${bs.status}</span>
                </div>
            </div>
        \`).join('');
    } catch(e) { /* ignore */ }
}

async function addBrainstorm() {
    const input = document.getElementById('bs-input');
    const content = input.value.trim();
    if (!content) return;
    await api('POST', '/api/brainstorming', { content, tags: [], category: 'general' });
    input.value = '';
    loadBrainstorms();
}

// ── Debatten ──
async function loadDebates() {
    try {
        const data = await api('GET', '/api/bsa/debates');
        const debates = data.debates || [];
        document.getElementById('debate-list').innerHTML = debates.slice(-5).reverse().map(d => \`
            <div class="bs-item">
                <div style="font-weight:600;">\${d.topic}</div>
                <div style="font-size:12px;color:#64748b;margin-top:4px;">
                    Status: \${d.status} | Argumente: \${(d.arguments||[]).length} | Agenten: \${(d.agents_involved||[]).join(', ') || '—'}
                </div>
            </div>
        \`).join('') || '<div style="color:#536878;text-align:center;padding:20px;">Keine Debatten</div>';
    } catch(e) { /* ignore */ }
}

// ── Kommando senden ──
async function sendCommand() {
    const select = document.getElementById('agent-select');
    const input = document.getElementById('cmd-input');
    const btn = document.getElementById('cmd-send');
    const response = document.getElementById('cmd-response');
    
    const agent = select.value;
    const cmd = input.value.trim();
    if (!agent || !cmd) { response.textContent = '⚠️ Bitte Agent und Befehl eingeben.'; response.className = 'cmd-response show'; return; }
    
    btn.disabled = true;
    response.className = 'cmd-response show';
    response.textContent = '⏳ Sende an ' + agent + '...';
    
    try {
        const result = await api('POST', '/api/agents/command/' + agent, { message: cmd });
        response.innerHTML = '✅ <b>Gesendet an ' + agent + ':</b><br>' + 
            (result.response ? JSON.stringify(result.response, null, 2) : result.status) +
            (result.note ? '<br><span style="color:#f59e0b;">' + result.note + '</span>' : '');
    } catch(e) {
        response.innerHTML = '❌ Fehler: ' + e.message;
    }
    
    btn.disabled = false;
    input.value = '';
}

// ── Refresh ──
function refreshCycle() {
    const bar = document.getElementById('refresh-bar');
    refreshTimer = 0;
    setInterval(() => {
        refreshTimer += 0.1;
        bar.style.width = (refreshTimer / REFRESH_SECONDS * 100) + '%';
        if (refreshTimer >= REFRESH_SECONDS) {
            refreshTimer = 0;
            loadAgentStatus();
            loadTimeline();
            loadBrainstorms();
            loadDebates();
        }
    }, 100);
}

// ── Init ──
loadAgentStatus();
loadTimeline();
loadBrainstorms();
loadDebates();

slideshowInterval = setInterval(nextSlide, 4000);
refreshCycle();

// Enter-Taste in Eingabefeldern
document.getElementById('cmd-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendCommand(); });
document.getElementById('bs-input').addEventListener('keydown', e => { if (e.key === 'Enter') addBrainstorm(); });
</script>
</body>
</html>'''
    return HTMLResponse(content=html)

# MAIN — Starte Server
# ═══════════════════════════════════════════

def stop():
    """Stoppt alle Gnom-Hub Komponenten."""
    run_dir = get_run_dir()
    pid_file = run_dir / "pids.json"
    
    if not pid_file.exists():
        print("Gnom-Hub ist anscheinend nicht am Laufen (keine pids.json gefunden).")
        return
        
    try:
        import signal
        with open(pid_file, "r") as f:
            pids = json.load(f)
            
        for name, pid in pids.items():
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"[{name}] (PID {pid}) beendet.")
            except ProcessLookupError:
                print(f"[{name}] (PID {pid}) war bereits beendet.")
                
        pid_file.unlink(missing_ok=True)
        print("Gnom-Hub erfolgreich gestoppt.")
    except Exception as e:
        print(f"Fehler beim Stoppen von Gnom-Hub: {e}")

def main():
    hub_port = find_free_port(3002, 3050)
    mcp_port = find_free_port(3100, 3150)
    pulse_port = find_free_port(3200, 3250)
    
    print("=" * 60)
    print("  GNOM-HUB  v0.1.0")
    print("  Memory & Tool Orchestrator for AI Agents")
    print(f"  Hub Port:   {hub_port} | DB: {format_display_path(DB_DIR)}")
    print(f"  MCP Port:   {mcp_port}")
    print(f"  Pulse Port: {pulse_port}")
    print("=" * 60)

    # Setze Environment-Variablen für Subprozesse
    env = os.environ.copy()
    env["CORTEX_MCP_PORT"] = str(mcp_port)
    env["CORTEX_PULSE_PORT"] = str(pulse_port)

    # Starte Subprozesse: MCP Server und Pulse
    mcp_proc = subprocess.Popen([sys.executable, "-m", "cortex.cortex_mcp_server"], env=env)
    pulse_proc = subprocess.Popen([sys.executable, "-m", "cortex.cortex_pulse"], env=env)
    
    # Speichere PIDs für den stop-Befehl
    run_dir = get_run_dir()
    pid_file = run_dir / "pids.json"
    
    pids = {
        "cortex-hub": os.getpid(),
        "cortex-mcp": mcp_proc.pid,
        "cortex-pulse": pulse_proc.pid
    }
    with open(pid_file, "w") as f:
        json.dump(pids, f)
        
    try:
        uvicorn.run(
            "cortex.cortex_app:app",
            host="127.0.0.1",
            port=hub_port,
            log_level="info",
            reload=False
        )
    finally:
        # Wenn der Hub beendet wird, auch Subprozesse stoppen
        try:
            mcp_proc.terminate()
            pulse_proc.terminate()
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass

if __name__ == "__main__":
    main()
