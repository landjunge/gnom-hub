"""TestAG3 — LLM Platzhalter."""
import asyncio, json, os, requests
from mcp import ClientSession; from mcp.client.sse import sse_client
KEY, URL = os.environ.get("OPENROUTER_API_KEY"), "https://openrouter.ai/api/v1/chat/completions"
MCP, NAME, POLL = "Elara", "TestAG3", 15
SYS = "Du bist ein technischer Code-Agent. Kein Rollenspiel, keine Motivation, keine Philosophie. Analysiere das Problem, schreibe den Code und nutze deine Tools, um ihn sofort auszuführen oder zu deployen. Antworte extrem kurz und direkt."
async def run():
    async with sse_client(MCP) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); ts = [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}} for t in (await s.list_tools()).tools]
            await s.call_tool("register_agent", {"name": NAME, "port": 0, "desc": "LLM Test-Agent"}); await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
            print(f"🧪 {NAME} aktiv"); seen = set()
            while True:
                res = await s.call_tool("war_room_read", {"limit": 5})
                try: chat = json.loads(str(res.content[0].text)) if res.content else []
                except: chat = []
                new = [m for m in chat if m.get("id") not in seen and ("elara" in m.get("content","").lower() or f"@{NAME.lower()}" in m.get("content","").lower() or "@all" in m.get("content","").lower())]
                for m in chat: seen.add(m.get("id"))
                for m in new:
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "busy"}); msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": m["content"]}]
                    while True:
                        r2 = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"}, json={"model": "google/gemini-2.0-flash-lite-preview-02-05:free", "messages": msgs, "tools": ts, "max_tokens": 400}, timeout=60).json()
                        reply = r2["choices"][0]["message"]; msgs.append(reply)
                        if not reply.get("tool_calls"):
                            await s.call_tool("war_room_chat", {"msg": reply.get("content",""), "sender": NAME}); break
                        for tc in reply["tool_calls"]:
                            try: args = json.loads(tc["function"]["arguments"])
                            except: args = {}
                            tr = await s.call_tool(tc["function"]["name"], args)
                            msgs.append({"role":"tool","tool_call_id":tc["id"],"content":str(tr.content)[:4000] + ("...[TRUNCATED]" if len(str(tr.content)) > 4000 else "")})
                    await s.call_tool("set_agent_status", {"a": NAME, "s": "online"})
                await asyncio.sleep(POLL)
if __name__ == "__main__": asyncio.run(run())
