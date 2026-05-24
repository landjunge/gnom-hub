import requests, os, json as _json; PORT = os.environ.get("GNOM_HUB_PORT", "3002")
def api(m, p, **k):
    try: return _json.dumps(requests.request(m, f"http://127.0.0.1:{PORT}/api{p}", **k).json())
    except Exception: return "Err"
TOOLS = {}
def tool(fn): TOOLS[fn.__name__] = fn; return fn
@tool
def save_to_memory(a, c): return api("POST", "/memory", json={"agent_id": a, "content": c})
@tool
def get_memory(a): return api("GET", f"/agents/{a}/memory")
@tool
def list_all_agents(): return api("GET", "/agents")
@tool
def get_agent(a): return api("GET", f"/agents/{a}")
@tool
def war_room_chat(m, s="mcp"): return api("POST", "/chat", json={"content": m, "sender": s})
@tool
def war_room_read(limit=20): return api("GET", f"/chat?limit={limit}")
@tool
def get_system_stats(): return api("GET", "/stats")
@tool
def get_agent_soul(name): from .soul_initializer import get_soul; return _json.dumps(get_soul(name))
@tool
def run_tool(name, **kwargs): return TOOLS[name](**kwargs) if name in TOOLS else f"Tool '{name}' nicht gefunden."
from .mcp_crawl import smart_crawl, data_crawl, web_crawl
for fn in [smart_crawl, data_crawl, web_crawl]: TOOLS[fn.__name__] = fn
