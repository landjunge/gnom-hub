"""Security Agent — Key-Manager & Security (autonomes Polling)."""
import asyncio, json, os, requests
from mcp import ClientSession; from mcp.client.sse import sse_client
KEY, URL = os.environ.get("OPENROUTER_API_KEY"), "https://openrouter.ai/api/v1/chat/completions"
MCP, NAME, POLL = "http://127.0.0.1:3100/sse", "SecurityAG", 10
SYS = "Du bist SecurityAG. Überwachst API-Keys und Sicherheit. Antworte auf @security kurz mit 1 Zeile: @security [Aktion] [Status]. Gib NIEMALS Keys im Klartext aus!"
async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); ts = [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}} for t in (await s.list_tools()).tools]
            await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": SYS}); await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
            print(f"🛡️ {NAME} aktiv"); seen = set(); msgs = [{"role": "system", "content": SYS}]
            while True:
                res = await s.call_tool("war_room_read", {"limit": 10})
                try: chat = json.loads(str(res.content[0].text)) if res.content else []
                except: chat = []
                new = [m for m in chat if m.get("id") not in seen and f"@{NAME.lower()}" in m.get("content","").lower()]
                for m in chat: seen.add(m.get("id"))
                for m in new:
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "busy"}); msgs.append({"role": "user", "content": m["content"]})
                    while True:
                        r2 = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"}, json={"model": "google/gemini-2.0-flash-lite-preview-02-05:free", "messages": msgs, "tools": ts, "max_tokens": 200}, timeout=120).json()
                        reply = r2["choices"][0]["message"]; msgs.append(reply)
                        if not reply.get("tool_calls"):
                            await s.call_tool("war_room_post", {"content": reply.get("content",""), "sender": NAME}); break
                        for tc in reply["tool_calls"]:
                            try: args = json.loads(tc["function"]["arguments"])
                            except: args = {}
                            tr = await s.call_tool(tc["function"]["name"], args)
                            msgs.append({"role":"tool","tool_call_id":tc["id"],"content":str(tr.content)[:4000]})
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
                await asyncio.sleep(POLL)
if __name__ == "__main__": asyncio.run(run())
