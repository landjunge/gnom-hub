import asyncio, requests; from .soul_initializer import get_soul; from .router import ask_router
HUB_URL = "http://127.0.0.1:3002"
class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        self.n, self.d, self.t, self.sys, self.p, self.model, self.seen = name, desc, trigger, sys_prompt, poll, model, set()
        soul = get_soul(name)
        if not self.sys:
            from .tool_registry import format_tools_prompt
            self.sys = format_tools_prompt(soul, name)
    def post(self, p, j=None):
        try: return requests.post(f"{HUB_URL}{p}", json=j).json()
        except: return {}
    def put(self, p, j=None):
        try: return requests.put(f"{HUB_URL}{p}", json=j).json()
        except: return {}
    def get(self, p):
        try: return requests.get(f"{HUB_URL}{p}").json()
        except: return []
    async def run(self):
        self.post("/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]}); print(f"🚀 {self.n} aktiv")
        while True:
            c = self.get("/api/chat?limit=10")
            if not isinstance(c, list): c = []
            # Only react to user messages with our @trigger (e.g. @watchdog, @backup)
            # NOT our agent name — the Hub's internal dispatch() handles @AgentName routing
            new = [m for m in c if m.get("id") not in self.seen and m.get("metadata",{}).get("sender","") == "user" and (self.t.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in c: self.seen.add(m.get("id"))
            for m in new:
                try:
                    r = ask_router(m["content"], self.sys, agent_name=self.n)
                    self.post("/api/chat", {"content": r, "sender": self.n}) if r and not r.startswith("[ROUTER-FEHLER]") else print(f"[{self.n}] Keine Antwort")
                except Exception as e: print(f"[{self.n}] Error: {e}")
            await asyncio.sleep(self.p)
