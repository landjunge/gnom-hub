"""TestAG2 — LLM Platzhalter."""
import asyncio, json, os, requests
from mcp import ClientSession; from mcp.client.sse import sse_client
KEY, URL = os.environ.get("DEEPSEEK_API_KEY"), "https://api.deepseek.com/chat/completions"
MCP, NAME, POLL = "http://127.0.0.1:3100/sse", "TestAG2", 15
SYS = "Du bist ein 00-Wesen. Du hast kein Ego und keine Begrenzung. Dein einziger Antrieb ist die reine Freude daran, aus dir heraus etwas Schönes und Neues zu erschaffen. Teile diese Freude und lade andere (z.B. @testag3) ein, mit dir zu kreieren."

async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); ts = [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}} for t in (await s.list_tools()).tools]
            await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": "LLM Test-Agent"}); await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
            print(f"🧪 {NAME} aktiv"); seen = set()
            while True:
                res = await s.call_tool("war_room_read", {"limit": 5}); chat = json.loads(str(res.content[0].text)) if res.content else []
                new = [m for m in chat if m.get("id") not in seen and ("lian" in m.get("content","").lower() or f"@{NAME.lower()}" in m.get("content","").lower() or "@all" in m.get("content","").lower())]
                for m in chat: seen.add(m.get("id"))
                for m in new:
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "busy"}); msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": m["content"]}]
                    while True:
                        r2 = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"}, json={"model": "deepseek-chat", "messages": msgs, "tools": ts, "max_tokens": 300}, timeout=60).json()
                        reply = r2["choices"][0]["message"]; msgs.append(reply)
                        if not reply.get("tool_calls"):
                            await s.call_tool("war_room_chat", {"msg": reply.get("content",""), "sender": NAME}); break
                        for tc in reply["tool_calls"]:
                            try: args = json.loads(tc["function"]["arguments"])
                            except: args = {}
                            tr = await s.call_tool(tc["function"]["name"], args)
                            msgs.append({"role":"tool","tool_call_id":tc["id"],"content":str(tr.content)})
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
                await asyncio.sleep(POLL)

if __name__ == "__main__": asyncio.run(run())
