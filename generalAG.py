"""General Agent — autonome Aufgabenverteilung, pollt War Room."""
import asyncio, json, os, requests
from mcp import ClientSession
from mcp.client.sse import sse_client

# ── Konfiguration ──────────────────────────────
MODEL   = "deepseek-chat"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-DEIN-KEY-HIER")
API_URL = "https://api.deepseek.com/chat/completions"
MCP_URL = "http://127.0.0.1:3100/sse"
POLL    = 10
SYSTEM  = ("Du bist der General. Eine Aufgabenverteilungsmaschine — keine Person. "
    "Du bekommst neue War-Room-Nachrichten. Reagiere NUR auf @job oder @general Befehle. "
    "Bei einem Job: 1) Prüfe Agenten (list_all_agents). 2) Zerlege in max 3 Teilaufgaben. "
    "3) Weise jede per war_room_chat zu: '@Name → Aufgabe'. "
    "Ignoriere alles andere. Du führst NICHTS selbst aus. Nur Zuweisung.")
# ────────────────────────────────────────────────
_seen = set()

async def run():
    async with sse_client(MCP_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            raw = await s.list_tools()
            tools = [{"type": "function", "function": {"name": t.name,
                "description": t.description or "", "parameters": t.inputSchema}} for t in raw.tools]
            print(f"⚔️  General autonom — {len(tools)} tools | pollt alle {POLL}s")
            msgs = [{"role": "system", "content": SYSTEM}]
            while True:
                res = await s.call_tool("war_room_read", {"limit": 10})
                chat = json.loads(str(res.content[0].text)) if res.content else []
                new = [m for m in chat if m.get("id") not in _seen and ("@job" in m.get("content","").lower() or "@general" in m.get("content","").lower())]
                for m in chat: _seen.add(m.get("id"))
                for m in new:
                    print(f"  📨 {m.get('content','')[:60]}")
                    msgs.append({"role": "user", "content": m["content"]})
                    while True:
                        r2 = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}"},
                            json={"model": MODEL, "messages": msgs, "tools": tools, "max_tokens": 500}, timeout=120)
                        reply = r2.json()["choices"][0]["message"]; msgs.append(reply)
                        if not reply.get("tool_calls"):
                            print(f"  ⚔️ {reply.get('content','')[:80]}"); break
                        for tc in reply["tool_calls"]:
                            try: args = json.loads(tc["function"]["arguments"])
                            except: print(f"  ⚠️ bad args: {tc['function']['arguments'][:60]}"); args = {}
                            tr = await s.call_tool(tc["function"]["name"], args)
                            print(f"  🔧 {tc['function']['name']}"); msgs.append({"role":"tool","tool_call_id":tc["id"],"content":str(tr.content)})
                await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(run())
