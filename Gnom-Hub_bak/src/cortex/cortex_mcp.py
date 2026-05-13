#!/usr/bin/env python3
"""
CORTEX MCP SERVER — Echter MCP-Server für das Gedächtnis .
===================================================
Konsolidierte Version: Importiert DB-Funktionen aus db.py (keine Duplikation).
Nutzt das MCP-Protokoll (FastMCP) statt REST-API.
Laeuft als stdio-MCP-Server (für Hermes-Native-MCP-Client).
Start: python3 cortex_mcp.py
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# ── Alles aus der zentralen db.py importieren ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import (
    read_db, write_db, generate_id, is_port_open,
    get_agents, reload_agents, save_agent, remove_agent,
    add_relation, query_relations, add_token, list_tokens,
    # Brainstorming
    add_brainstorm, list_brainstorm, update_brainstorm_status,
    # Workflows
    create_workflow, add_workflow_step, run_workflow, list_workflows,
    # Debates
    create_debate, add_argument, complete_debate, list_debates,
    # Agent Live-Status
    set_agent_status, list_agents_status, register_agent_online,
    set_agent_activity, set_agent_offline, send_to_agent,
    # Per-Agent Datenbanken
    agent_think, agent_say, agent_do, agent_event,
    get_agent_database, list_agent_databases,
    # Königliche Chronik
    king_speak, get_royal_chronicle,
    AGENTS, DB_DIR, DB_FILES,
)

from mcp.server import FastMCP


# ═══════════════════════════════════════════
# MCP-SERVER
# ═══════════════════════════════════════════

mcp = FastMCP(
    name="Cortex Hub",
    instructions="""
    Cortex Hub — das zentrale Nervensystem .
    Verwaltet 11 Datenbanken: memory, sessions, entities, events, agents, relations,
    tokens, brainstorming, workflows, debates, agents_status.
    Koordiniert 8 Agenten: Hermes, Antigravity, OpenClaw, Paperclip, Agent Zero,
    Tandem, Agent Launcher, Cortex Hub.
    Features: Brainstorming (@bs), Multi-Agent-Debatten (@bsa), Workflows,
    Agent-zu-Agent Messaging, Live-Status-Tracking, Relations-Graph.
    """,
    log_level="INFO",
)


# ── Memory-Tools ──

@mcp.tool()
def cortex_search(query: str, limit: int = 20) -> str:
    """Durchsuche das Cortex-Gedaechtnis nach Eintraegen. Nutze dies, um fruehere Entscheidungen, Fakten oder Ereignisse zu finden."""
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
    return json.dumps({"query": query, "results": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
def cortex_store(content: str, type: str = "fact", source: str = "MCP", tags: str = "") -> str:
    """Speichere einen Eintrag im Cortex-Gedaechtnis. type: fact|event|decision|llm_query. tags: komma-getrennt."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    data = read_db("memory")
    new_entry = {
        "id": generate_id("mem"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": type,
        "source": source,
        "content": content,
        "tags": tag_list,
        "weight": 1,
        "reads": 0,
        "depth": "archive",
    }
    data.append(new_entry)
    write_db("memory", data)
    return json.dumps({"success": True, "id": new_entry["id"]})


@mcp.tool()
def cortex_stats() -> str:
    """Statistiken aller Cortex-Datenbanken abrufen — wie viele Eintraege in memory, sessions, entities, events."""
    stats = {}
    for name in DB_FILES.keys():
        data = read_db(name)
        stats[name] = len(data)
    stats["agents_total"] = len(AGENTS)
    stats["agents_online"] = sum(
        1 for a in AGENTS if AGENTS[a].get("port") and is_port_open(AGENTS[a]["port"])
    )
    return json.dumps({"stats": stats}, indent=2, ensure_ascii=False)


# ── Agenten-Tools ──

@mcp.tool()
def agent_status(agent_id: str = "") -> str:
    """Status eines oder aller Agenten abrufen. Ohne agent_id werden alle Agenten aufgelistet. agent_id: hermes|tandem|paperclip|openclaw|agentzero|agentlauncher|cortex"""
    if agent_id:
        if agent_id not in AGENTS:
            return json.dumps({"error": f"Unbekannter Agent: {agent_id}"})
        agent = AGENTS[agent_id]
        online = is_port_open(agent["port"]) if agent["port"] else False
        return json.dumps({"id": agent_id, "name": agent["name"], "port": agent["port"], "online": online}, indent=2)

    results = {}
    for aid, agent in AGENTS.items():
        online = is_port_open(agent["port"]) if agent["port"] else False
        results[aid] = {"id": aid, "name": agent["name"], "port": agent["port"], "online": online}
    return json.dumps({
        "agents": results,
        "total": len(results),
        "online": sum(1 for r in results.values() if r["online"]),
    }, indent=2, ensure_ascii=False)


@mcp.tool()
def agentlauncher_status() -> str:
    """Zeige ob der Agent Launcher (Port 8900) laeuft und antwortet."""
    import subprocess
    port_open = is_port_open(8900)
    pid = None
    try:
        result = subprocess.run(["pgrep", "-f", "agent_launcher.py"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip().split("\n")[0])
    except:
        pass
    return json.dumps({
        "port_open": port_open,
        "process_running": pid is not None,
        "pid": pid,
        "online": port_open and pid is not None,
    }, indent=2)


# ── Session-Tool ──

@mcp.tool()
def session_list(limit: int = 10) -> str:
    """Liste die letzten Sessions aus dem Cortex-Gedaechtnis. limit: max Anzahl (default 10)."""
    data = read_db("sessions")
    if data and "timestamp" in data[0]:
        data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return json.dumps({"sessions": data[:limit], "total": len(data)}, indent=2, ensure_ascii=False)


# ── Agenten-Registry-Tools (aus agents.json) ──

@mcp.tool()
def agent_registry() -> str:
    """Liste alle registrierten Agenten aus der Datenbank (agents.json)."""
    data = read_db("agents")
    return json.dumps({"agents": data, "total": len(data)}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_registry_add(agent_id: str, name: str, port: int = 0, agent_type: str = "Agent", description: str = "") -> str:
    """Neuen Agenten in der Registry speichern."""
    agent_data = {
        "id": agent_id,
        "name": name,
        "port": port if port else None,
        "type": agent_type,
        "description": description,
        "status": "active",
        "created": datetime.utcnow().isoformat() + "Z",
    }
    saved = save_agent(agent_data)
    reload_agents()
    return json.dumps({"success": True, "agent": saved}, indent=2, ensure_ascii=False)


# ── Relations-Tools (aus relations.json) ──

@mcp.tool()
def relation_query(entity_type: str = "", entity_id: str = "", relation: str = "") -> str:
    """Suche Beziehungen zwischen Entitaeten. Filtere nach Entitaetstyp, ID oder Beziehungstyp."""
    results = query_relations(
        entity_type=entity_type,
        entity_id=entity_id,
        relation=relation,
    )
    return json.dumps({"relations": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
def relation_add(source_type: str, source_id: str, target_type: str, target_id: str, relation: str, description: str = "") -> str:
    """Erstelle eine neue Beziehung zwischen zwei Entitaeten. source_type/target_type: memory|entity|event|agent"""
    entry = add_relation(
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relation=relation,
        description=description,
    )
    return json.dumps({"success": True, "relation": entry}, indent=2, ensure_ascii=False)


# ── Token-Tools (aus tokens.json) ──

@mcp.tool()
def token_list(token_type: str = "", status: str = "") -> str:
    """Liste alle Tokens auf. Optional nach Typ oder Status filtern."""
    tokens = list_tokens(token_type=token_type, status=status)
    return json.dumps({"tokens": tokens, "count": len(tokens)}, indent=2, ensure_ascii=False)


@mcp.tool()
def token_add(name: str, token_type: str = "mcp_token", purpose: str = "") -> str:
    """Neuen Token erstellen. token_type: mcp_token|api_key|hexpix"""
    entry = add_token(name=name, token_type=token_type, purpose=purpose)
    return json.dumps({"success": True, "token": entry}, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════
# BRAINSTORMING-TOOLS (@bs)
# ═══════════════════════════════════════════

@mcp.tool()
def brainstorm_add(content: str, source: str = "chat", tags: str = "", category: str = "general") -> str:
    """Erfasse eine Brainstorming-Idee (@bs). Wird in brainstorming.json UND memory.json gespeichert. category: general|architecture|feature|bugfix|security|ui"""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    entry = add_brainstorm(content=content, source=source, tags=tag_list, category=category)
    return json.dumps({"success": True, "brainstorm": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def brainstorm_list(status: str = "", category: str = "", tags: str = "") -> str:
    """Liste Brainstorming-Ideen. Filter nach status (fresh|explored|developed|implemented|archived), category oder tags (komma-getrennt)."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = list_brainstorm(status=status, category=category, tags=tag_list)
    return json.dumps({"brainstorms": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
def brainstorm_update(bs_id: str, status: str) -> str:
    """Aktualisiere Status einer Brainstorming-Idee. status: fresh|explored|developed|implemented|archived"""
    ok = update_brainstorm_status(bs_id, status)
    return json.dumps({"success": ok, "id": bs_id, "new_status": status})


# ═══════════════════════════════════════════
# DEBATE-TOOLS (@bsa — Multi-Agent-Diskussion)
# ═══════════════════════════════════════════

@mcp.tool()
def debate_create(topic: str, initiator: str = "User") -> str:
    """Starte eine neue Multi-Agent-Debatte (@bsa). Agenten koennen pro/contra/researcher/validator Rollen einnehmen."""
    entry = create_debate(topic=topic, initiator=initiator)
    return json.dumps({"success": True, "debate": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def debate_argue(debate_id: str, agent_name: str, role: str, content: str, sources: str = "") -> str:
    """Fuege ein Argument zu einer Debatte hinzu. role: pro|contra|researcher|validator. sources: komma-getrennt."""
    source_list = [s.strip() for s in sources.split(",") if s.strip()] if sources else None
    result = add_argument(debate_id=debate_id, agent_name=agent_name, role=role, content=content, sources=source_list)
    return json.dumps({"success": "error" not in result, "argument": result}, indent=2, ensure_ascii=False)


@mcp.tool()
def debate_complete(debate_id: str, conclusion: str) -> str:
    """Schliesse eine Debatte ab mit einer Conclusio. Wird auch als Memory gespeichert."""
    ok = complete_debate(debate_id=debate_id, conclusion=conclusion)
    return json.dumps({"success": ok, "debate_id": debate_id})


@mcp.tool()
def debate_list(status: str = "") -> str:
    """Liste Debatten. Optional filtern nach status: active|completed|aborted."""
    results = list_debates(status=status)
    return json.dumps({"debates": results, "count": len(results)}, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════
# WORKFLOW-TOOLS
# ═══════════════════════════════════════════

@mcp.tool()
def workflow_create(name: str, description: str = "", trigger: str = "manual") -> str:
    """Erstelle einen neuen Workflow. trigger: manual|cron|event|@bs|@bsa"""
    entry = create_workflow(name=name, description=description, trigger=trigger)
    return json.dumps({"success": True, "workflow": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def workflow_add_step(wf_id: str, action: str, agent: str = "", description: str = "") -> str:
    """Fuege einen Schritt zu einem Workflow hinzu."""
    step = {"action": action, "agent": agent, "description": description}
    ok = add_workflow_step(wf_id, step)
    return json.dumps({"success": ok, "workflow_id": wf_id})


@mcp.tool()
def workflow_run(wf_id: str) -> str:
    """Starte einen Workflow (markiere als 'running')."""
    result = run_workflow(wf_id)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def workflow_list(status: str = "") -> str:
    """Liste Workflows. Optional filtern nach status: active|paused|running|completed|archived."""
    results = list_workflows(status=status)
    return json.dumps({"workflows": results, "count": len(results)}, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════
# AGENT LIVE-STATUS & MESSAGING
# ═══════════════════════════════════════════

@mcp.tool()
def agent_heartbeat(agent_id: str, status: str = "idle", activity: str = "", pid: int = 0, port: int = 0) -> str:
    """Setze Live-Status eines Agenten (Heartbeat). status: idle|busy|offline|error. Fluechtig — wird bei Neustart zurueckgesetzt."""
    result = set_agent_status(
        agent_id=agent_id,
        status=status,
        activity=activity,
        pid=pid if pid else None,
        port=port if port else None,
    )
    return json.dumps({"success": True, "status": result}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_live_status(status_filter: str = "") -> str:
    """Liste Live-Status aller Agenten. Optional filtern nach status: idle|busy|offline|error."""
    results = list_agents_status(status_filter=status_filter)
    return json.dumps({"agents_status": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_message(agent_id: str, message: str) -> str:
    """Sende eine Nachricht an einen Agenten via seinen Port. Nutzt den /api/command Endpoint des Agenten."""
    result = send_to_agent(agent_id=agent_id, message=message)
    return json.dumps(result, indent=2, ensure_ascii=False)


# ── Per-Agent Datenbanken ──

@mcp.tool()
def agent_think_tool(agent_id: str, thought: str, context: str = "") -> str:
    """Logge einen Gedanken in die Per-Agent-Datenbank (thoughts.json)."""
    entry = agent_think(agent_id, thought, context)
    return json.dumps({"success": True, "entry": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_say_tool(agent_id: str, message: str, recipient: str = "", channel: str = "") -> str:
    """Logge eine Nachricht/Ausgabe in die Per-Agent-Datenbank (said.json)."""
    entry = agent_say(agent_id, message, recipient, channel)
    return json.dumps({"success": True, "entry": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_do_tool(agent_id: str, action: str, result: str = "", tool: str = "") -> str:
    """Logge eine Aktion in die Per-Agent-Datenbank (done.json)."""
    entry = agent_do(agent_id, action, result, tool)
    return json.dumps({"success": True, "entry": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_event_tool(agent_id: str, event_type: str, details: str = "") -> str:
    """Logge ein Ereignis in die Per-Agent-Datenbank (events.json)."""
    entry = agent_event(agent_id, event_type, details)
    return json.dumps({"success": True, "entry": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_get_db(agent_id: str, db_name: str, limit: int = 50) -> str:
    """Lese eine Per-Agent-Datenbank. db_name: thoughts|said|done|events"""
    result = get_agent_database(agent_id, db_name, limit)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
def agent_list_dbs() -> str:
    """Liste alle vorhandenen Per-Agent-Datenbanken auf."""
    result = list_agent_databases()
    return json.dumps(result, indent=2, ensure_ascii=False)


# ── Königliche Chronik ──

@mcp.tool()
def king_speak_tool(content: str, channel: str = "", agent_target: str = "") -> str:
    """Logge ein Wort des Königs in die königliche Chronik (royal_chronicle.json) und in memory.json."""
    entry = king_speak(content, channel, agent_target)
    return json.dumps({"success": True, "entry": entry}, indent=2, ensure_ascii=False)


@mcp.tool()
def royal_chronicle_tool(limit: int = 100) -> str:
    """Lese die königliche Chronik (neueste Einträge zuerst)."""
    result = get_royal_chronicle(limit)
    return json.dumps(result, indent=2, ensure_ascii=False)



# ═══════════════════════════════════════════
# MESSAGING-TOOLS (Hermes ↔ Antigravity Pipe)
# ═══════════════════════════════════════════

@mcp.tool()
def msg_send(sender: str, recipient: str, content: str) -> str:
    """Sende eine Nachricht an einen anderen Agenten via Cortex-Pipe.
    sender/recipient: hermes|antigravity|openclaw|paperclip
    Beispiel: msg_send('hermes', 'antigravity', 'Hey Antigravity!')
    """
    from cortex_msg import cmd_send
    msg = cmd_send(sender=sender, recipient=recipient, content=content)
    return json.dumps({"success": True, "message": msg}, indent=2, ensure_ascii=False)


@mcp.tool()
def msg_read(recipient: str, unread_only: bool = True) -> str:
    """Lese Nachrichten aus der Cortex-Pipe.
    recipient: hermes|antigravity|openclaw|paperclip
    unread_only: True = nur ungelesene (default), False = alle
    """
    from cortex_msg import cmd_read
    msgs = cmd_read(recipient=recipient, unread_only=unread_only)
    return json.dumps({"messages": msgs, "count": len(msgs)}, indent=2, ensure_ascii=False)



# ═══════════════════════════════════════════
# MAIN — Starte MCP-Server (stdio)
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())

