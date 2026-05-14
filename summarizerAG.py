"""Summarizer Agent — lauscht autonom im War Room, extrahiert Essenz."""
import asyncio, json, os, requests
from mcp import ClientSession
from mcp.client.sse import sse_client

# ── Konfiguration ──────────────────────────────
MODEL   = "deepseek-chat"
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-DEIN-KEY-HIER")
API_URL = "https://api.deepseek.com/chat/completions"
MCP_URL = "http://127.0.0.1:3100/sse"
POLL    = 30
BATCH   = 15
SYSTEM  = ("Du bist der Summarizer. Analysiere die neuen War-Room-Nachrichten. "
    "Extrahiere NUR: Fakten, Entscheidungen, Aufgaben, wichtige Absichten. "
    "Ignoriere: Grüße, Smalltalk, Witze, Wiederholungen. "
    "Speichere die Essenz mit save_to_memory(agent='summarizer', content=...). "
    "Max 5 Stichpunkte. Wenn nichts Wichtiges dabei ist, speichere NICHTS.")
# ────────────────────────────────────────────────
_seen = set()

async def run():
    async with sse_client(MCP_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            raw = await s.list_tools()
            tools = [{"type": "function", "function": {"name": t.name,
                "description": t.description or "", "parameters": t.inputSchema}} for t in raw.tools]
            print(f"📋 Summarizer autonom — {len(tools)} tools | pollt alle {POLL}s")
            msgs = [{"role": "system", "content": SYSTEM}]
            while True:
                res = await s.call_tool("war_room_read", {"limit": BATCH})
                chat = json.loads(str(res.content[0].text)) if res.content else []
                new = [m for m in chat if m.get("id") not in _seen]
                for m in chat: _seen.add(m.get("id"))
                if new:
                    block = "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {m.get('content','')}" for m in new)
                    print(f"  📨 {len(new)} neue Nachrichten")
                    msgs.append({"role": "user", "content": f"Neue Nachrichten:\n{block}"})
                    while True:
                        r2 = requests.post(API_URL, headers={"Authorization": f"Bearer {API_KEY}"},
                            json={"model": MODEL, "messages": msgs, "tools": tools, "max_tokens": 300}, timeout=120)
                        reply = r2.json()["choices"][0]["message"]; msgs.append(reply)
                        if not reply.get("tool_calls"):
                            if reply.get("content"): print(f"  📋 {reply['content'][:80]}"); break
                        for tc in reply["tool_calls"]:
                            tr = await s.call_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]))
                            print(f"  🔧 {tc['function']['name']}"); msgs.append({"role":"tool","tool_call_id":tc["id"],"content":str(tr.content)})
                await asyncio.sleep(POLL)

if __name__ == "__main__":
    asyncio.run(run())
