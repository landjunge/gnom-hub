#!/usr/bin/env python3
"""
CORTEX MCP CLIENT — Standalone MCP-Server für Antigravity (Gemini).
===================================================================
Greift direkt auf die Gnom-Hub JSON-Datenbanken zu.
Kein REST nötig — liest/schreibt die selben Dateien wie cortex_mcp.py.

Tools:
  - search_cortex(query)  → Durchsucht memory.json
  - save_cortex(content)  → Speichert in memory.json
  - cortex_stats()        → Statistiken aller DBs
  - list_agents()         → Zeigt registrierte Agenten

Start: python3.11 cortex_mcp_client.py
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict

from config import get_data_dir

# ── Pfade zur Gnom-Hub DB (identisch mit db.py) ──
DB_DIR = str(get_data_dir())
DB_FILES = {
    "memory":      os.path.join(DB_DIR, "memory.json"),
    "sessions":    os.path.join(DB_DIR, "sessions.json"),
    "entities":    os.path.join(DB_DIR, "entities.json"),
    "events":      os.path.join(DB_DIR, "events.json"),
    "agents":      os.path.join(DB_DIR, "agents.json"),
    "relations":   os.path.join(DB_DIR, "relations.json"),
    "tokens":      os.path.join(DB_DIR, "tokens.json"),
    "brainstorming": os.path.join(DB_DIR, "brainstorming.json"),
}


def read_db(table: str) -> List[Dict]:
    """Lese eine JSON-Tabelle."""
    filepath = DB_FILES.get(table)
    if not filepath or not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def write_db(table: str, data: List[Dict]):
    """Schreibe eine JSON-Tabelle."""
    filepath = DB_FILES.get(table)
    if not filepath:
        raise ValueError(f"Unbekannte Tabelle: {table}")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_id(prefix: str = "mem") -> str:
    """Erzeuge eine eindeutige ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"{prefix}_{timestamp}"


# ═══════════════════════════════════════════
# MCP-SERVER (FastMCP)
# ═══════════════════════════════════════════

from mcp.server import FastMCP

mcp = FastMCP(
    name="Gnom-Hub Client",
    instructions="""
    Gnom-Hub Client — Direktzugriff auf den Gnom-Hub Speicher.
    Liest und schreibt die gleichen JSON-Datenbanken wie GNOM-HUB.
    Tools: search_cortex, save_cortex, cortex_stats, list_agents.
    """,
    log_level="WARNING",
)


@mcp.tool()
def search_cortex(query: str, limit: int = 20) -> str:
    """Durchsuche den Gnom-Hub Speicher nach Eintraegen. Findet Fakten, Entscheidungen, Events."""
    data = read_db("memory")
    results = []
    q = query.lower()
    for entry in data:
        content = entry.get("content", "").lower()
        tags = [t.lower() for t in entry.get("tags", [])]
        if q in content or any(q in tag for tag in tags):
            results.append(entry)
        if len(results) >= limit:
            break
    return json.dumps(
        {"query": query, "results": results, "count": len(results)},
        indent=2, ensure_ascii=False,
    )


@mcp.tool()
def save_cortex(content: str, entry_type: str = "fact", source: str = "Antigravity", tags: str = "") -> str:
    """Speichere einen Eintrag im Gnom-Hub Speicher. entry_type: fact|event|decision|brainstorm. tags: komma-getrennt."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    data = read_db("memory")
    new_entry = {
        "id": generate_id("mem"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": entry_type,
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
    """Statistiken aller Cortex-Datenbanken — Anzahl Eintraege pro Tabelle."""
    stats = {}
    for name in DB_FILES:
        stats[name] = len(read_db(name))
    return json.dumps({"stats": stats}, indent=2, ensure_ascii=False)


@mcp.tool()
def list_agents() -> str:
    """Zeige alle registrierten Agenten aus der Cortex-Registry."""
    data = read_db("agents")
    return json.dumps(
        {"agents": data, "total": len(data)},
        indent=2, ensure_ascii=False,
    )


# ═══════════════════════════════════════════
# MAIN — stdio-MCP-Server
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
