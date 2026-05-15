"""Soul Agent — verwaltet Agenten-Persönlichkeit via .md-Dateien, unter 40 Zeilen."""
import asyncio, json, os, requests
from mcp import ClientSession
from mcp.client.sse import sse_client

# ── Konfiguration ──────────────────────────────
MODEL   = "google/gemini-2.0-flash-lite-preview-02-05:free"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "sk-DEIN-KEY-HIER")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MCP_URL = "http://127.0.0.1:3100/sse"
SYSTEM  = ("Du bist der Soul-Architekt. Du formst die Persönlichkeit von Agenten über ihre .md-Dateien "
    "(soul.md, agent.md, core.md). Bei @soul @Name Anweisung: Lies die aktuelle soul.md des Agenten, "
    "passe den Charakter an und schreibe die Änderung zurück. Du bist präzise — jede Änderung muss "
    "den Kern des Agenten stärken, nicht verwässern. Humor, Schärfe, Fokus — du formst es.")
# ────────────────────────────────────────────────

async def run():
    async with sse_client(MCP_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            raw = await s.list_tools()
            tools = [{"type": "function", "function": {"name": t.name,
                "description": t.description or "", "parameters": t.inputSchema}} for t in raw.tools]
            print(f"👻 Soul-Agent bereit — {len(tools)} tools | {MODEL}")
            msgs = [{"role": "system", "content": SYSTEM}]
            while True:
                msgs.append({"role": "user", "content": await asyncio.to_thread(input, "👻 >>> ")})
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
