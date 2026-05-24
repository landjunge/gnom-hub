import asyncio, os, requests; from .soul_initializer import get_soul; from .router import ask_router
HUB_URL = f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}"
class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        self.n, self.d, self.t, self.sys, self.p, self.model, self.seen = name, desc, trigger, sys_prompt, poll, model, set()
        soul = get_soul(name)
        if not self.sys:
            from .tool_registry import format_tools_prompt
            self.sys = format_tools_prompt(soul, name)
    def post(self, p, j=None):
        try: return requests.post(f"{HUB_URL}{p}", json=j).json()
        except Exception: return {}
    def put(self, p, j=None):
        try: return requests.put(f"{HUB_URL}{p}", json=j).json()
        except Exception: return {}
    def get(self, p):
        try: return requests.get(f"{HUB_URL}{p}").json()
        except Exception: return []
    async def run(self):
        self.post("/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]}); print(f"🚀 {self.n} aktiv")
        while True:
            c = self.get("/api/chat?limit=10")
            if not isinstance(c, list): c = []
            new = [m for m in c if m.get("id") not in self.seen and m.get("metadata",{}).get("sender","") == "user" and (self.t.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in c: self.seen.add(m.get("id"))
            for m in new:
                try:
                    from .zwc_soul import decode_soul
                    traits = {}
                    for msg in self.get("/api/chat?limit=30"):
                        s = decode_soul(msg.get("content", ""))
                        if s and s.get("name") == "user_soul": traits.update({k: v for k, v in s.items() if k not in ("agent", "sig", "name")})
                    sys = self.sys + (f"\n\n[User-Profil] {traits}" if traits else "")
                    r = ask_router(m["content"], sys, agent_name=self.n)
                    self.post("/api/chat", {"content": r, "sender": self.n}) if r and not r.startswith("[ROUTER-FEHLER]") else print(f"[{self.n}] Keine Antwort")
                except Exception as e: print(f"[{self.n}] Error: {e}")
            await asyncio.sleep(self.p)
