#!/usr/bin/env python3
"""
GNOM-HUB DB — Gemeinsame Datenbankfunktionen.
Einzige Quelle der Wahrheit fuer read_db, write_db, generate_id, is_port_open.
Wird von cortex_app.py (REST) UND cortex_mcp.py (MCP stdio) importiert.
Keine Duplikation — eine Aenderung, zwei Interfaces.
"""

import json
import os
import sys
import socket
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import get_data_dir, get_agents_dir

# ── Datenbankpfad (konsolidiert im Gnom-Hub-Ordner) ──
DB_DIR = str(get_data_dir())
DB_FILES = {
    "memory":      os.path.join(DB_DIR, "memory.json"),
    "sessions":    os.path.join(DB_DIR, "sessions.json"),
    "entities":    os.path.join(DB_DIR, "entities.json"),
    "events":      os.path.join(DB_DIR, "events.json"),
    "agents":      os.path.join(DB_DIR, "agents.json"),
    "relations":   os.path.join(DB_DIR, "relations.json"),
    "tokens":      os.path.join(DB_DIR, "tokens.json"),
    # ── Neue DBs ──
    "brainstorming": os.path.join(DB_DIR, "brainstorming.json"),
    "workflows":     os.path.join(DB_DIR, "workflows.json"),
    "debates":       os.path.join(DB_DIR, "debates.json"),
    # ── Fluechtige Live-DBs ──
    "agents_status": os.path.join(DB_DIR, "agents_status.json"),
    # ── Königliches Chronik ──
    "royal_chronicle": os.path.join(DB_DIR, "royal_chronicle.json"),
}


# ═══════════════════════════════════════════
# BASIS-DATENBANK-FUNKTIONEN (vor Agent-Import benoetigt)
# ═══════════════════════════════════════════

def read_db(table: str) -> List[Dict]:
    """Lese eine JSON-Tabelle aus der Datenbank."""
    filepath = DB_FILES.get(table)
    if not filepath or not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def write_db(table: str, data: List[Dict]):
    """Schreibe eine JSON-Tabelle in die Datenbank."""
    filepath = DB_FILES.get(table)
    if not filepath:
        raise ValueError(f"Unbekannte Tabelle: {table}")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_id(prefix: str = "mem") -> str:
    """Erzeuge eine eindeutige ID mit Zeitstempel."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"{prefix}_{timestamp}"


# ── Agenten-Registry (aus DB, nicht hardcoded) ──

def _load_agents() -> dict:
    """Lade Agenten aus agents.json. Fallback auf leeres Dict, wenn nicht vorhanden."""
    data = read_db("agents")
    agents = {}
    for a in data:
        aid = a.get("id", "")
        if aid:
            # Kompatibel zum alten AGENTS-Format
            entry = {k: v for k, v in a.items() if k != "id"}
            agents[aid] = entry
    return agents


# Initialer Ladevorgang — wird einmal beim Import ausgefuehrt
_AGENTS_CACHE = _load_agents()


def get_agents() -> dict:
    """Liefere aktuelle Agenten-Liste (mit Cache-Refresh, aber ohne Festplattenzugriff)."""
    global _AGENTS_CACHE
    return _AGENTS_CACHE


def reload_agents() -> dict:
    """Erzwinge Neuladen der Agenten aus der Datenbank."""
    global _AGENTS_CACHE
    _AGENTS_CACHE = _load_agents()
    return _AGENTS_CACHE


def save_agent(agent_data: dict) -> dict:
    """Speichere oder aktualisiere einen Agenten in agents.json."""
    data = read_db("agents")
    agent_id = agent_data.get("id", "")
    # Existierenden Eintrag finden/ersetzen
    for i, a in enumerate(data):
        if a.get("id") == agent_id:
            data[i] = agent_data
            break
    else:
        data.append(agent_data)
    write_db("agents", data)
    reload_agents()
    return agent_data


def remove_agent(agent_id: str) -> bool:
    """Entferne einen Agenten aus der Registry."""
    data = read_db("agents")
    new_data = [a for a in data if a.get("id") != agent_id]
    if len(new_data) == len(data):
        return False
    write_db("agents", new_data)
    reload_agents()
    return True


# ── Relations-Funktionen ──

def add_relation(source_type: str, source_id: str,
                 target_type: str, target_id: str,
                 relation: str, description: str = "",
                 weight: float = 1.0) -> dict:
    """Erstelle eine Beziehung zwischen zwei Entitaeten."""
    data = read_db("relations")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("rel"),
        "source_type": source_type,
        "source_id": source_id,
        "target_type": target_type,
        "target_id": target_id,
        "relation": relation,
        "description": description,
        "weight": weight,
        "created": now,
    }
    data.append(entry)
    write_db("relations", data)
    return entry


def query_relations(entity_type: str = "", entity_id: str = "",
                    relation: str = "", direction: str = "both") -> list:
    """Suche Beziehungen. entity: filtere nach Entitaet. relation: filtere nach Typ.
    direction: 'source' (ausgehend), 'target' (eingehend), 'both' (alle)."""
    data = read_db("relations")
    results = []
    for r in data:
        match = True
        if relation and r.get("relation") != relation:
            match = False
        if entity_id:
            if direction == "source":
                match = match and r.get("source_id") == entity_id
            elif direction == "target":
                match = match and r.get("target_id") == entity_id
            else:
                match = match and (r.get("source_id") == entity_id or r.get("target_id") == entity_id)
        if entity_type:
            if direction == "source":
                match = match and r.get("source_type") == entity_type
            elif direction == "target":
                match = match and r.get("target_type") == entity_type
            else:
                match = match and (r.get("source_type") == entity_type or r.get("target_type") == entity_type)
        if match:
            results.append(r)
    return results


# ── Tokens-Funktionen ──

def add_token(name: str, token_type: str, purpose: str = "",
              metadata: dict = None) -> dict:
    """Erstelle einen neuen Token-Eintrag."""
    data = read_db("tokens")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("tok"),
        "name": name,
        "type": token_type,
        "purpose": purpose,
        "status": "active",
        "created": now,
        "last_used": None,
        "expires": None,
        "metadata": metadata or {},
    }
    data.append(entry)
    write_db("tokens", data)
    return entry


def list_tokens(token_type: str = "", status: str = "") -> list:
    """Liste Tokens mit optionalem Filter nach Typ und Status."""
    data = read_db("tokens")
    if not token_type and not status:
        return data
    results = []
    for t in data:
        if token_type and t.get("type") != token_type:
            continue
        if status and t.get("status") != status:
            continue
        results.append(t)
    return results


# Alias fuer Abwaertskompatibilitaet — AGENTS ist ein Proxy
class _AgentsProxy:
    def __getitem__(self, key):
        return get_agents()[key]
    def __setitem__(self, key, value):
        agents = get_agents()
        agents[key] = value
    def __contains__(self, key):
        return key in get_agents()
    def __len__(self):
        return len(get_agents())
    def __iter__(self):
        return iter(get_agents())
    def get(self, key, default=None):
        return get_agents().get(key, default)
    def items(self):
        return get_agents().items()
    def keys(self):
        return get_agents().keys()
    def values(self):
        return get_agents().values()


AGENTS = _AgentsProxy()

USER_HOME = os.path.expanduser("~")
ENV_FILE = os.environ.get("HERMES_ENV", os.path.join(USER_HOME, ".hermes", ".env"))
CORTEX_URL = "http://127.0.0.1:3002"
LAUNCHER_URL = "http://127.0.0.1:8900"
PAPERCLIP_URL = "http://127.0.0.1:3100"
ROW_LABELS = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p']


# ═══════════════════════════════════════════
# WEITERE FUNKTIONEN
# ═══════════════════════════════════════════

def is_port_open(port: int) -> bool:
    """Pruefe ob ein Port offen ist (TCP-Verbindung moeglich)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


def get_agent_status(agent_id: str) -> Dict:
    """Ermittle den Status eines Agenten (online/offline + Details)."""
    agent = AGENTS.get(agent_id)
    if not agent:
        return {"id": agent_id, "online": False, "error": "Unbekannter Agent"}

    online = is_port_open(agent["port"]) if agent["port"] else False
    result = {
        "id": agent_id,
        "name": agent["name"],
        "icon": agent.get("icon", ""),
        "port": agent["port"],
        "online": online,
        "type": agent.get("type", ""),
    }

    # Antigravity: cloud-nativ, immer verfuegbar
    if agent_id == "antigravity":
        result["online"] = True
        result["docs_path"] = agent.get("docs_path", "")
        result["features"] = agent.get("features", [])

    # Agent Launcher: extra script_path
    if agent_id == "agentlauncher":
        result["script_path"] = agent.get("script_path", "")

    return result


# ═══════════════════════════════════════════
# OPENROUTER
# ═══════════════════════════════════════════

def check_openrouter_key() -> bool:
    """Prueft ob OpenRouter API-Key gesetzt ist."""
    env_key = os.environ.get("OPENROUTER_API_KEY", "")
    if env_key and len(env_key) > 10 and env_key != "***":
        return True

    env_path = os.path.join(USER_HOME, ".hermes", ".env")
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key and len(key) > 10 and key != "***":
                        return True
    return False


def get_openrouter_key() -> str:
    """Hole den OpenRouter API-Key aus Umgebungsvariable oder .env."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key and len(api_key) > 10 and api_key != "***":
        return api_key

    env_path = os.path.join(USER_HOME, ".hermes", ".env")
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                k = line.strip()
                if k.startswith("OPENROUTER_API_KEY="):
                    api_key = k.split("=", 1)[1].strip().strip('"').strip("'")
                    if api_key and len(api_key) > 10 and api_key != "***":
                        return api_key
    return ""


def query_openrouter(prompt: str, agent_name: str = "System") -> Dict:
    """Sendet eine Anfrage an Nemotron via OpenRouter."""
    import urllib.request
    import urllib.error
    api_key = get_openrouter_key()
    if not api_key:
        return {"error": "Kein OpenRouter API-Key gefunden", "success": False}

    try:
        payload = json.dumps({
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
            "temperature": 0.7,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/hermes-agent",
                "X-Title": f"GNOM-HUB-{agent_name}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "response": data["choices"][0]["message"]["content"],
                "model": data.get("model", "nemotron"),
                "usage": data.get("usage", {}),
            }
    except urllib.error.HTTPError as e:
        return {"error": f"OpenRouter HTTP {e.code}: {e.read().decode()[:200]}", "success": False}
    except Exception as e:
        return {"error": f"OpenRouter Fehler: {str(e)}", "success": False}


# ═══════════════════════════════════════════
# BRAINSTORMING-DB (@bs)
# ═══════════════════════════════════════════

def add_brainstorm(content: str, source: str = "chat", tags: list = None,
                   category: str = "general") -> dict:
    """Erfasse eine Brainstorming-Idee (@bs-Trigger)."""
    data = read_db("brainstorming")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("bs"),
        "timestamp": now,
        "source": source,
        "content": content,
        "tags": tags or [],
        "category": category,
        "status": "fresh",  # fresh | explored | developed | implemented | archived
        "references": [],
        "votes": 0,
    }
    data.append(entry)
    write_db("brainstorming", data)

    # Auch als Memory speichern für Kontext
    mem_data = read_db("memory")
    mem_entry = {
        "id": generate_id("mem"),
        "timestamp": now,
        "type": "brainstorm",
        "source": source,
        "content": f"[@bs] {content}",
        "tags": tags + ["brainstorm"] if tags else ["brainstorm"],
        "weight": 3,
        "reads": 0,
        "depth": "archive",
    }
    mem_data.append(mem_entry)
    write_db("memory", mem_data)

    return entry


def list_brainstorm(status: str = "", category: str = "", tags: list = None) -> list:
    """Liste Brainstorming-Einträge mit optionalen Filtern."""
    data = read_db("brainstorming")
    results = data[:]
    if status:
        results = [e for e in results if e.get("status") == status]
    if category:
        results = [e for e in results if e.get("category") == category]
    if tags:
        for tag in tags:
            results = [e for e in results if tag in e.get("tags", [])]
    return results


def update_brainstorm_status(bs_id: str, status: str) -> bool:
    """Aktualisiere Status einer Brainstorming-Idee."""
    data = read_db("brainstorming")
    for e in data:
        if e["id"] == bs_id:
            e["status"] = status
            e["updated"] = datetime.utcnow().isoformat() + "Z"
            write_db("brainstorming", data)
            return True
    return False


# ═══════════════════════════════════════════
# WORKFLOWS-DB
# ═══════════════════════════════════════════

def create_workflow(name: str, description: str = "", trigger: str = "",
                    steps: list = None) -> dict:
    """Erstelle einen neuen Workflow."""
    data = read_db("workflows")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("wf"),
        "name": name,
        "description": description,
        "trigger": trigger,  # z.B. "@bsa", "cron", "manual"
        "steps": steps or [],
        "status": "active",  # active | paused | completed | archived
        "created": now,
        "updated": now,
        "run_count": 0,
        "last_run": None,
    }
    data.append(entry)
    write_db("workflows", data)
    return entry


def add_workflow_step(wf_id: str, step: dict) -> bool:
    """Füge einen Schritt zu einem Workflow hinzu."""
    data = read_db("workflows")
    for wf in data:
        if wf["id"] == wf_id:
            step["id"] = generate_id("step")
            step["status"] = "pending"
            wf["steps"].append(step)
            wf["updated"] = datetime.utcnow().isoformat() + "Z"
            write_db("workflows", data)
            return True
    return False


def run_workflow(wf_id: str) -> dict:
    """Führe einen Workflow aus (markiere als gestartet)."""
    data = read_db("workflows")
    for wf in data:
        if wf["id"] == wf_id:
            wf["run_count"] += 1
            wf["last_run"] = datetime.utcnow().isoformat() + "Z"
            wf["status"] = "running"
            write_db("workflows", data)
            return {"status": "started", "workflow": wf}
    return {"error": "Workflow nicht gefunden"}


def list_workflows(status: str = "") -> list:
    """Liste Workflows, optional gefiltert nach Status."""
    data = read_db("workflows")
    if status:
        return [w for w in data if w.get("status") == status]
    return data


# ═══════════════════════════════════════════
# DEBATES-DB (@bsa — Multi-Agent-Diskussion)
# ═══════════════════════════════════════════

def create_debate(topic: str, initiator: str = "User") -> dict:
    """Erstelle eine neue Agenten-Debatte (@bsa-Trigger)."""
    data = read_db("debates")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("deb"),
        "topic": topic,
        "initiator": initiator,
        "status": "active",  # active | completed | aborted
        "created": now,
        "updated": now,
        "arguments": [],
        "agents_involved": [],
        "conclusion": None,
        "sources": [],
    }
    data.append(entry)
    write_db("debates", data)
    return entry


def add_argument(debate_id: str, agent_name: str, role: str,
                 content: str, sources: list = None) -> dict:
    """Füge ein Argument einer Debatte hinzu."""
    data = read_db("debates")
    for deb in data:
        if deb["id"] == debate_id:
            arg = {
                "id": generate_id("arg"),
                "agent": agent_name,
                "role": role,  # pro | contra | researcher | validator
                "content": content,
                "sources": sources or [],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            deb["arguments"].append(arg)
            if agent_name not in deb["agents_involved"]:
                deb["agents_involved"].append(agent_name)
            deb["updated"] = datetime.utcnow().isoformat() + "Z"
            write_db("debates", data)
            return arg
    return {"error": "Debatte nicht gefunden"}


def complete_debate(debate_id: str, conclusion: str) -> bool:
    """Schließe eine Debatte mit einer Conclusio ab."""
    data = read_db("debates")
    for deb in data:
        if deb["id"] == debate_id:
            deb["status"] = "completed"
            deb["conclusion"] = conclusion
            deb["updated"] = datetime.utcnow().isoformat() + "Z"

            # Auch als Memory speichern
            mem_data = read_db("memory")
            mem_entry = {
                "id": generate_id("mem"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "type": "debate_conclusion",
                "source": f"@bsa:{debate_id}",
                "content": f"[@bsa] {deb['topic']}: {conclusion}",
                "tags": ["debate", "bsa", "conclusion"],
                "weight": 5,
                "reads": 0,
                "depth": "archive",
            }
            mem_data.append(mem_entry)
            write_db("memory", mem_data)
            write_db("debates", data)
            return True
    return False


def list_debates(status: str = "") -> list:
    """Liste Debatten, optional gefiltert."""
    data = read_db("debates")
    if status:
        return [d for d in data if d.get("status") == status]
    return data
def get_agent_status(agent_id: str) -> dict:
    """Hole Live-Status eines Agenten. Gibt Default zurueck wenn nicht existiert."""
    data = read_db("agents_status")
    for a in data:
        if a["agent_id"] == agent_id:
            return a
    return {"agent_id": agent_id, "status": "unknown", "activity": "", "last_seen": "", "pid": None, "port": None, "uptime": 0}

def set_agent_status(agent_id: str, status: str = "idle", activity: str = "", pid: int = None, port: int = None) -> dict:
    """Setze Live-Status eines Agenten. Fluechtig — wird bei Gnom-Hub-Neustart zurückgesetzt."""
    data = read_db("agents_status")
    now = datetime.utcnow().isoformat() + "Z"
    found = False
    for a in data:
        if a["agent_id"] == agent_id:
            a["status"] = status
            a["activity"] = activity
            a["last_seen"] = now
            if pid is not None: a["pid"] = pid
            if port is not None: a["port"] = port
            a["uptime"] = a.get("uptime", 0) + 1
            found = True
            break
    if not found:
        entry = {
            "agent_id": agent_id,
            "status": status,
            "activity": activity,
            "last_seen": now,
            "created": now,
            "pid": pid,
            "port": port,
            "uptime": 0,
            "tasks_done": 0,
        }
        data.append(entry)
    write_db("agents_status", data)
    return entry if not found else a

def list_agents_status(status_filter: str = "") -> list:
    """Liste alle Agenten-Status. Optional filtern nach Status."""
    data = read_db("agents_status")
    if status_filter:
        return [a for a in data if a.get("status") == status_filter]
    return data

def set_agent_activity(agent_id: str, activity: str) -> dict:
    """Kurzbefehl: aktualisiere nur die Activity eines Agenten."""
    return set_agent_status(agent_id, activity=activity)

def register_agent_online(agent_id: str, pid: int = None, port: int = None) -> dict:
    """Agent meldet sich online."""
    return set_agent_status(agent_id, status="idle", activity="online", pid=pid, port=port)

def set_agent_offline(agent_id: str) -> dict:
    """Setze Agent auf offline."""
    return set_agent_status(agent_id, status="offline", activity="nicht erreichbar")

def send_to_agent(agent_id: str, message: str) -> dict:
    """Sende eine Nachricht an einen Agenten via seinen bekannten Port.
    Antigravity hat keinen Port — Kommunikation läuft über Gnom-Hub-Gedächtnis (cortex_store).
    """
    import urllib.request
    import urllib.error

    # Antigravity ist cloud-nativ — kein direkter HTTP-Port
    if agent_id == "antigravity":
        return {
            "success": False,
            "error": "Antigravity hat keinen direkten HTTP-Port. "
                     "Nutze cortex_store() um eine Nachricht ins Gedächtnis zu schreiben "
                     "— Antigravity liest beim nächsten Start daraus.",
            "hint": "cortex_store(content='<deine Nachricht>', type='event', tags='hermes,antigravity,ping')",
        }

    status = get_agent_status(agent_id)
    if status["status"] == "offline" or not status.get("port"):
        return {"success": False, "error": f"Agent {agent_id} ist offline oder kein Port bekannt"}
    try:
        url = f"http://127.0.0.1:{status['port']}/api/command"
        payload = json.dumps({"command": message, "source": "gnom-hub"}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return {"success": resp.status == 200, "response": body[:500], "agent": agent_id}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}", "agent": agent_id}
    except Exception as e:
        return {"success": False, "error": str(e), "agent": agent_id}


# ═══════════════════════════════════════════
# PER-AGENT DATENBANKEN (Gedacht/Gesagt/Getan/Events)
# ═══════════════════════════════════════════

AGENT_DB_BASE = str(get_agents_dir())

def _agent_db_path(agent_id: str, db_name: str) -> str:
    """Liefere Pfad zur Per-Agent-Datenbank."""
    return os.path.join(AGENT_DB_BASE, agent_id, f"{db_name}.json")

def _read_agent_db(agent_id: str, db_name: str) -> List[Dict]:
    """Lese eine Per-Agent-Datenbank."""
    fp = _agent_db_path(agent_id, db_name)
    if not os.path.exists(fp):
        return []
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def _write_agent_db(agent_id: str, db_name: str, data: List[Dict]):
    """Schreibe eine Per-Agent-Datenbank."""
    fp = _agent_db_path(agent_id, db_name)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def agent_think(agent_id: str, thought: str, context: str = "") -> dict:
    """Agent loggt einen Gedanken."""
    data = _read_agent_db(agent_id, "thoughts")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("thk"),
        "timestamp": now,
        "agent_id": agent_id,
        "type": "thought",
        "thought": thought,
        "context": context,
    }
    data.append(entry)
    _write_agent_db(agent_id, "thoughts", data)
    return entry

def agent_say(agent_id: str, message: str, recipient: str = "", channel: str = "") -> dict:
    """Agent loggt, was er gesagt hat."""
    data = _read_agent_db(agent_id, "said")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("say"),
        "timestamp": now,
        "agent_id": agent_id,
        "type": "said",
        "message": message,
        "recipient": recipient,
        "channel": channel,
    }
    data.append(entry)
    _write_agent_db(agent_id, "said", data)
    return entry

def agent_do(agent_id: str, action: str, result: str = "", tool: str = "") -> dict:
    """Agent loggt, was er getan hat."""
    data = _read_agent_db(agent_id, "done")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("do"),
        "timestamp": now,
        "agent_id": agent_id,
        "type": "action",
        "action": action,
        "result": result[:500],
        "tool": tool,
    }
    data.append(entry)
    _write_agent_db(agent_id, "done", data)
    return entry

def agent_event(agent_id: str, event_type: str, details: str = "") -> dict:
    """Agent loggt ein Ereignis (was passiert ist)."""
    data = _read_agent_db(agent_id, "events")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("evt"),
        "timestamp": now,
        "agent_id": agent_id,
        "type": "event",
        "event_type": event_type,
        "details": details[:500],
    }
    data.append(entry)
    _write_agent_db(agent_id, "events", data)
    return entry

def get_agent_database(agent_id: str, db_name: str, limit: int = 50) -> dict:
    """Lese eine Per-Agent-Datenbank (thoughts|said|done|events)."""
    valid = {"thoughts", "said", "done", "events"}
    if db_name not in valid:
        return {"error": f"Ungültige DB: {db_name}. Gültig: {', '.join(valid)}"}
    data = _read_agent_db(agent_id, db_name)
    # Neueste zuerst
    data_sorted = sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
    return {
        "agent_id": agent_id,
        "database": db_name,
        "data": data_sorted[:limit],
        "total": len(data),
    }


# ═══════════════════════════════════════════
# KÖNIGLICHES CHRONIK (Alle Worte des Königs)
# ═══════════════════════════════════════════

def king_speak(content: str, channel: str = "", agent_target: str = "") -> dict:
    """Logge ein Wort des Königs — egal wo und zu wem gesprochen."""
    data = read_db("royal_chronicle")
    now = datetime.utcnow().isoformat() + "Z"
    entry = {
        "id": generate_id("roy"),
        "timestamp": now,
        "type": "royal_word",
        "content": content,
        "channel": channel,
        "agent_target": agent_target,
    }
    data.append(entry)
    write_db("royal_chronicle", data)
    return entry

def get_royal_chronicle(limit: int = 100) -> dict:
    """Lese die königliche Chronik — neueste Einträge zuerst."""
    data = read_db("royal_chronicle")
    data_sorted = sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
    return {
        "data": data_sorted[:limit],
        "total": len(data),
    }

def list_agent_databases() -> dict:
    """Liste alle vorhandenen Per-Agent-Datenbanken."""
    if not os.path.exists(AGENT_DB_BASE):
        return {"agents": {}}
    result = {}
    for agent_id in os.listdir(AGENT_DB_BASE):
        agent_dir = os.path.join(AGENT_DB_BASE, agent_id)
        if os.path.isdir(agent_dir):
            dbs = {}
            for fn in os.listdir(agent_dir):
                if fn.endswith(".json"):
                    db_name = fn[:-5]
                    fp = os.path.join(agent_dir, fn)
                    try:
                        with open(fp, 'r') as f:
                            dbs[db_name] = len(json.load(f))
                    except:
                        dbs[db_name] = 0
            result[agent_id] = dbs
    return {"agents": result}
