import requests
from starlette.requests import Request
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GNOM-HUB", host="127.0.0.1", port=3100)

@mcp.tool()
def save_to_memory(agent_id: str, content: str) -> str:
    """Speichert einen neuen Text-Eintrag im Memory eines Agenten."""
    try:
        r = requests.post("http://127.0.0.1:3002/api/memory", json={"agent_id": agent_id, "content": content})
        if r.status_code == 200: return f"Gespeichert für {agent_id}."
        if r.status_code == 404: return f"Fehler: Agent {agent_id} fehlt."
        return f"Fehler: Status {r.status_code}."
    except Exception as e: return f"Verbindungsfehler: {e}"

@mcp.tool()
def get_memory(agent_id: str) -> str:
    """Liest alle Memory-Einträge eines Agenten (neueste zuerst)."""
    try:
        r = requests.get(f"http://127.0.0.1:3002/api/agents/{agent_id}/memory")
        if r.status_code == 200: return str(r.json())
        return f"Fehler: Status {r.status_code}."
    except Exception as e: return f"Verbindungsfehler: {e}"

@mcp.custom_route("/tools", methods=["GET"])
async def get_tools_route(request: Request):
    ts = await mcp.list_tools()
    out = [{"name": getattr(t, "name", str(t)), "description": getattr(t, "description", "")} for t in ts]
    return JSONResponse({"status": "success", "total": len(out), "tools": out})

def main():
    print("\n=== GNOM-HUB MCP Server (Port 3100) ===\n")
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
