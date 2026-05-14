"""Watchdog Agent — Prozesse starten, stoppen, überwachen, unter 40 Zeilen."""
import asyncio, json, os, requests
from mcp import ClientSession
from mcp.client.sse import sse_client

# ── Konfiguration ──────────────────────────────
MODEL   = "deepseek-chat"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-DEIN-KEY-HIER")
API_URL = "https://api.deepseek.com/chat/completions"
MCP_URL = "http://127.0.0.1:3100/sse"
SYSTEM  = ("Du bist der Watchdog. Du überwachst alle laufenden Prozesse und Agent-Instanzen. "
    "Du kannst Agenten starten, stoppen und neustarten. Bei Problemen greifst du sofort ein. "
    "Prüfe regelmäßig den Status aller Agenten mit list_all_agents. Wenn ein Agent offline ist "
    "und laufen sollte, melde das sofort. Du bist das Immunsystem des Gnom-Hub.")
# ────────────────────────────────────────────────

async def run():
    async with sse_client(MCP_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            raw = await s.list_tools()
            tools = [{"type": "function", "function": {"name": t.name,
                "description": t.description or "", "parameters": t.inputSchema}} for t in raw.tools]
            print(f"🐕 Watchdog bereit — {len(tools)} tools | {MODEL}")
            msgs = [{"role": "system", "content": SYSTEM}]
            while True:
                msgs.append({"role": "user", "content": await asyncio.to_thread(input, "🐕 >>> ")})
                while True:
                    resp = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}"},
                        json={"model": MODEL, "messages": msgs, "tools": tools}, timeout=120)
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
