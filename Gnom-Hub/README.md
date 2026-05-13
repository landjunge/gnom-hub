# GNOM-HUB

GNOM-HUB ist ein minimalistischer, schneller Memory- und Tool-Orchestrator für lokale KI-Agenten. Das System dient als zentrales Gehirn und Middleware, über die sich Agenten registrieren, Erinnerungen austauschen und auf externe Werkzeuge zugreifen können.

## Installation

```bash
# Im Projekt-Hauptverzeichnis ausführen:
python3 -m pip install -e .
```

## Starten

Das gesamte System (Hub-API & MCP-Server) kann mit einem einfachen Befehl gestartet werden:

```bash
python3 -m gnom_hub
```

Beide Server laufen anschließend parallel und können durch Drücken von `Ctrl+C` sauber beendet werden.

## Ports & Architektur

Das System teilt sich in zwei unabhängige Kernkomponenten auf:

- **Port 3002**: Die Core-API (FastAPI). Zuständig für Memory, Agenten-Verwaltung und Prozess-Kontrolle.
- **Port 3100**: Der MCP-Server (FastMCP / SSE). Zuständig für die Bereitstellung von Tools.

## Wichtige API-Endpunkte

**Hub API** (`http://127.0.0.1:3002`)

- `GET /` — Status-Check und Versionsinfo.
- `GET /api/agents` — Listet alle registrierten Agenten auf.
- `POST /api/agents` — Legt einen neuen Agenten an.
- `POST /api/memory` — Speichert eine Erinnerung (Memory) für einen Agenten.
- `GET /api/memory/search?q=...` — Sucht global in allen Memory-Einträgen.
- `GET /api/agents/{agent_id}/memory` — Ruft den historischen Speicher eines spezifischen Agenten ab.

**MCP Server** (`http://127.0.0.1:3100`)

- `GET /tools` — Listet alle registrierten, aktiven Werkzeuge auf.

## Tools hinzufügen

Der MCP-Server (`src/gnom_hub/hub_mcp.py`) startet standardmäßig als "Blank Slate" mit 0 Tools. Um neue Werkzeuge dynamisch bereitzustellen, nutzt du den extrem einfachen `@mcp.tool()` Decorator aus dem FastMCP SDK:

```python
# In src/gnom_hub/hub_mcp.py hinzufügen:

@mcp.tool()
def get_system_time() -> str:
    """Gibt die aktuelle Systemzeit zurück."""
    import datetime
    return datetime.datetime.now().isoformat()
```
Sobald du den Server neu startest, ist das Tool automatisch für alle verbundenen Agenten nutzbar.
