import os
agents = {
    "cronjobAG.py": {"name": "CronjobAG", "desc": "Plant zeitgesteuerte Aufgaben", "trigger": "@cronjob"},
    "skillsAG.py": {"name": "SkillsAG", "desc": "Baut und verwaltet Agent-Skills", "trigger": "@skill"},
    "soulAG.py": {"name": "SoulAG", "desc": "Verwaltet Persönlichkeit via .md", "trigger": "@soul"},
    "tinyAG.py": {"name": "TinyAG", "desc": "Tiny MCP Agent", "trigger": "@tiny"},
    "watchdogAG.py": {"name": "WatchdogAG", "desc": "Überwacht laufende Prozesse", "trigger": "@watchdog"}
}
loop_template = """            await s.call_tool("register_agent", {{"name": "{name}", "port": 0, "desc": "{desc}"}})
            await s.call_tool("set_agent_status", {{"a": "{name}", "s": "online"}})
            _seen = set()
            while True:
                res = await s.call_tool("war_room_read", {{"limit": 10}})
                chat = json.loads(str(res.content[0].text)) if res.content else []
                new = [m for m in chat if m.get("id") not in _seen and ("{trigger}" in m.get("content","").lower() or "@all" in m.get("content","").lower())]
                for m in chat: _seen.add(m.get("id"))
                for m in new:
                    await s.call_tool("set_agent_status", {{"a": "{name}", "s": "busy"}})
                    msgs.append({{"role": "user", "content": m["content"]}})
                    while True:
                        resp = requests.post(API_URL, headers={{"Authorization": f"Bearer {{API_KEY}}"}},
                            json={{"model": MODEL, "messages": msgs, "tools": tools}}, timeout=120)
                        reply = resp.json()["choices"][0]["message"]
                        msgs.append(reply)
                        if not reply.get("tool_calls"): break
                        for tc in reply["tool_calls"]:
                            r2 = await s.call_tool(tc["function"]["name"], json.loads(tc["function"]["arguments"]))
                            msgs.append({{"role": "tool", "tool_call_id": tc["id"], "content": str(r2.content)}})
                    await s.call_tool("set_agent_status", {{"a": "{name}", "s": "online"}})
                await asyncio.sleep(10)
if __name__ == "__main__":
    asyncio.run(run())
"""
for filename, config in agents.items():
    if not os.path.exists(filename): continue
    with open(filename, "r") as f:
        content = f.read()
    split_marker = 'msgs = [{"role": "system", "content": SYSTEM}]'
    if split_marker in content:
        top_half = content.split(split_marker)[0] + split_marker + "\n"
        new_content = top_half + loop_template.format(**config)
        with open(filename, "w") as f:
            f.write(new_content)
