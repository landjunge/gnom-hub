"""TestAG2 — Platzhalter. Echo + Memory + Agents-Liste."""
import asyncio, json
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP, NAME, POLL = "http://127.0.0.1:3100/sse", "TestAG2", 15

async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": f"Test-Agent — Platzhalter"})
            await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
            tools = await s.list_tools()
            print(f"🧪 {NAME} online — {len(tools.tools)} Tools")
            seen = set()
            while True:
                res = await s.call_tool("war_room_read", {"limit": 5})
                chat = json.loads(str(res.content[0].text)) if res.content else []
                for m in chat:
                    mid = m.get("id")
                    if mid in seen: continue
                    seen.add(mid)
                    c = m.get("content", "")
                    if f"@{NAME.lower()}" not in c.lower(): continue
                    lo = c.lower()
                    if "merke" in lo:
                        txt = c.split("merke", 1)[-1].strip()
                        await s.call_tool("save_to_memory", {"a": NAME, "c": txt})
                        reply = f"Gemerkt: '{txt[:50]}'"
                    elif "memory" in lo:
                        r2 = await s.call_tool("get_memory", {"a": NAME})
                        mems = json.loads(str(r2.content[0].text)) if r2.content else []
                        reply = f"Memory: {len(mems)} Einträge"
                    elif "agents" in lo:
                        r2 = await s.call_tool("list_all_agents", {})
                        ags = json.loads(str(r2.content[0].text)) if r2.content else []
                        reply = ", ".join(f"{a['name']}({a.get('status','?')})" for a in ags)
                    else:
                        reply = f"Echo ({len(c)} Zeichen). Befehle: merke/memory/agents"
                    await s.call_tool("war_room_chat", {"msg": reply, "sender": NAME})
                await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(run())
