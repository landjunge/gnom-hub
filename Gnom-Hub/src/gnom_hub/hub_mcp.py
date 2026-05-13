import requests, os
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
API = os.environ.get("GNOM_HUB_PORT", "3002")
mcp = FastMCP("HUB", host="127.0.0.1", port=int(os.environ.get("GNOM_MCP_PORT", 3100)))
def api(m, p, **k):
    try: return str(requests.request(m, f"http://127.0.0.1:{API}/api{p}", **k).json())
    except Exception as e: return f"Err: {e}"
@mcp.tool()
def save_to_memory(a: str, c: str) -> str:
    """Speichert einen Text-Eintrag im Memory eines Agenten."""
    return api("POST", "/memory", json={"agent_id": a, "content": c})
@mcp.tool()
def get_memory(a: str) -> str:
    """Liest alle Memory-Einträge eines Agenten aus."""
    return api("GET", f"/agents/{a}/memory")
@mcp.tool()
def search_memory(q: str) -> str:
    """Sucht global im Memory nach einem Begriff."""
    return api("GET", "/memory/search", params={"q": q})
@mcp.tool()
def delete_memory(m: str) -> str:
    """Löscht einen Memory-Eintrag anhand ID."""
    return api("DELETE", f"/memory/{m}")
@mcp.tool()
def update_memory(m: str, c: str) -> str:
    """Ändert den Inhalt eines Memory-Eintrags."""
    return api("PUT", f"/memory/{m}", params={"content": c})
@mcp.tool()
def set_agent_status(a: str, s: str) -> str:
    """Setzt den Status (online/offline)."""
    return api("PUT", f"/agents/{a}/status", params={"status": s})
@mcp.tool()
def list_all_agents() -> str:
    """Gibt alle Agenten zurück."""
    return api("GET", "/agents")
@mcp.tool()
def clear_agent_memory(a: str) -> str:
    """Löscht alle Memory-Einträge eines Agenten."""
    return api("DELETE", f"/agents/{a}/memory")
@mcp.custom_route("/tools", methods=["GET"])
async def tools_route(r): return JSONResponse([{"name": t.name, "desc": t.description} for t in await mcp.list_tools()])
def main(): mcp.run(transport="sse")
