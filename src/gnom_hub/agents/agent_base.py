import asyncio, os, requests; from gnom_hub.soul import get_soul; from gnom_hub.router import ask_router
HUB_URL = f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}"
class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        self.n, self.d, self.t, self.sys, self.p, self.seen = name, desc, trigger, sys_prompt, poll, set()
        from gnom_hub.agents.tool_registry import format_tools_prompt
        t_p = format_tools_prompt(get_soul(name), name)
        self.sys = (self.sys + "\n\n" + t_p) if self.sys else t_p
    def _req(self, method, p, j=None):
        try:
            r = getattr(requests, method)(f"{HUB_URL}{p}", json=j, timeout=10)
            if r.status_code == 200: return r.json()
        except Exception: pass
        return None
    async def run(self):
        while not self._req("post", "/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]}):
            print(f"⚠️ {self.n}: Hub nicht erreichbar. Reconnect in 5s..."); await asyncio.sleep(5)
        for m in (self._req("get", "/api/chat?limit=10") or []): self.seen.add(m.get("id"))
        print(f"🚀 {self.n} aktiv")
        while True:
            c = self._req("get", "/api/chat?limit=10")
            if c is None: print(f"⚠️ {self.n}: Hub offline. Versuche Reconnect..."); await asyncio.sleep(5); continue
            new = [m for m in c if m.get("id") not in self.seen and m.get("metadata",{}).get("sender","") in ("user", "GeneralAG") and (self.t.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in c: self.seen.add(m.get("id"))
            if new:
                self._req("put", f"/api/agents/{self.n}/status?status=busy")
                try:
                    for m in new:
                        try:
                            from gnom_hub.soul import soul_instance
                            sys = soul_instance.inject_context(self.sys, m["content"], agent_name=self.n)
                            r = ask_router(m["content"], sys, agent_name=self.n)
                            if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
                                from gnom_hub.action_handlers import process_actions
                                from gnom_hub.brainstorm_helpers import get_workspace_dir
                                wd = get_workspace_dir()
                                soul = get_soul(self.n) or {"permissions": ["read"]}
                                perms = soul.get("permissions", [])
                                processed = process_actions(r.content, {"name": self.n}, perms, False, wd)
                                import re
                                think_match = re.search(r'(<think>[\s\S]*?</think>)', r.answer)
                                think_prefix = think_match.group(1) + "\n\n" if think_match else ""
                                self._req("post", "/api/chat", {"content": think_prefix + processed, "sender": self.n})
                        except Exception as e: print(f"[{self.n}] Error: {e}")
                finally:
                    self._req("put", f"/api/agents/{self.n}/status?status=online")
            await asyncio.sleep(self.p)
