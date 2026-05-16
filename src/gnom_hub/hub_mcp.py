import requests, os, json as _json; from mcp.server.fastmcp import FastMCP
mcp = FastMCP("HUB", host="127.0.0.1", port=int(os.environ.get("GNOM_MCP_PORT", 3100)))
def api(m, p, **k):
    try: return _json.dumps(requests.request(m, f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT','3002')}/api"+p, **k).json())
    except: return "Err"
T = ["save_to_memory|a:str,c:str|api('POST','/memory',json={'agent_id':a,'content':c})",
     "get_memory|a:str|api('GET',f'/agents/{a}/memory')",
     "search_memory|q:str|api('GET','/memory/search',params={'q':q})",
     "delete_memory|m:str|api('DELETE',f'/memory/{m}')",
     "update_memory|m:str,c:str|api('PUT',f'/memory/{m}',params={'content':c})",
     "set_agent_status|a:str,s:str|api('PUT',f'/agents/{a}/status',params={'status':s})",
     "list_all_agents||api('GET','/agents')",
     "get_agent|a:str|api('GET',f'/agents/{a}')",
     "clear_agent_memory|a:str|api('DELETE',f'/agents/{a}/memory')",
     "create_agent|n:str,d:str=''|api('POST','/agents',json={'name':n,'description':d,'status':'offline'})",
     "delete_agent|a:str|api('DELETE',f'/agents/{a}')",
     "get_system_stats||api('GET','/stats')",
     "register_agent|n:str,p:int,d:str=''|api('POST','/agents/register',json={'name':n,'port':p,'description':d})",
     "nudge_agent|a:str,r:str='manual'|api('POST',f'/agents/{a}/nudge',params={'reason':r})",
     "war_room_chat|m:str,s:str='mcp'|api('POST','/chat',json={'content':m,'sender':s})",
     "war_room_read|limit:int=20|api('GET',f'/chat?limit={limit}')",
     "set_agent_role|a:str,role:str|api('PUT',f'/admin/agents/{a}/role',params={'role':role})"]
for t in T:
    n, a, b = t.split("|"); exec(f"@mcp.tool()\ndef {n}({a}): return {b}")
@mcp.tool()
def read_file(path: str):
    try: return open(path, "r", encoding="utf-8").read()
    except Exception as e: return f"Fehler: {e}"
@mcp.tool()
def write_file(path: str, content: str):
    try: open(path, "w", encoding="utf-8").write(content); return "Erfolg"
    except Exception as e: return f"Fehler: {e}"
@mcp.tool()
def run_command(cmd: str):
    import subprocess; return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
@mcp.tool()
def distribute_job(job: str): from gnom_hub.role_tools import distribute_job as dj; return dj(job)
@mcp.tool()
def summarize_chat(): from gnom_hub.role_tools import summarize_chat as sc; return sc()
def main(): from gnom_hub.swarm_checkpoint import load_latest_checkpoint as L; from gnom_hub.db import save_db as S; c = L(); (S("agents", c["souls"]), S("memory", c["war_room_state"])) if c else None; mcp.run(transport="sse")
