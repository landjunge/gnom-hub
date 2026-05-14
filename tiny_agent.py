"""Tiny MCP Agent für Gnom-Hub — unter 40 Zeilen."""
import asyncio, json, os, requests
from mcp import ClientSession
from mcp.client.sse import sse_client

DS = os.environ.get("DEEPSEEK_API_KEY", "")
URL = "https://api.deepseek.com/chat/completions"
HUB = os.environ.get("GNOM_MCP", "http://127.0.0.1:3100/sse")

async def run():
    async with sse_client(HUB) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            raw = await s.list_tools()
            tools = [{"type": "function", "function": {"name": t.name,
                "description": t.description or "", "parameters": t.inputSchema}} for t in raw.tools]
            print(f"🧠 {len(tools)} tools geladen. Los gehts.")
            msgs = [{"role": "system", "content": "Du bist ein Gnom-Hub Agent. Nutze die verfügbaren Tools."}]
            while True:
                msgs.append({"role": "user", "content": await asyncio.to_thread(input, ">>> ")})
                while True:
                    resp = requests.post(URL, headers={"Authorization": f"Bearer {DS}"},
                        json={"model": "deepseek-chat", "messages": msgs, "tools": tools}, timeout=120)
                    reply = resp.json()["choices"][0]["message"]
                    msgs.append(reply)
                    if not reply.get("tool_calls"):
                        print(f"\n{reply.get('content', '')}\n"); break
                    for tc in reply["tool_calls"]:
                        res = await s.call_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]))
                        print(f"  🔧 {tc['function']['name']}")
                        msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": str(res.content)})

if __name__ == "__main__":
    asyncio.run(run())
