import asyncio, json, os, requests
from .soul_initializer import get_soul

HUB_URL = "http://127.0.0.1:3002"
KEY = os.environ.get("DEEPSEEK_API_KEY")

class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        self.n, self.d, self.t, self.sys, self.p, self.model = name, desc, trigger, sys_prompt, poll, model
        self.seen = set()
        soul = get_soul(name)
        if not self.sys:
            from .tool_registry import format_tools_prompt
            self.sys = format_tools_prompt(soul, name)
            if "role" in soul: self.sys += f"\nRolle: {soul['role']}"

    def post(self, path, json=None):
        try: return requests.post(f"{HUB_URL}{path}", json=json).json()
        except: return {}

    def get(self, path):
        try: return requests.get(f"{HUB_URL}{path}").json()
        except: return []

    async def run(self):
        self.post("/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]})
        print(f"🚀 {self.n} aktiv")
        while True:
            chat = self.get("/api/chat?limit=10")
            if not isinstance(chat, list): chat = []
            
            new = [m for m in chat if m.get("id") not in self.seen and (self.n.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in chat: self.seen.add(m.get("id"))
            
            for m in new:
                self.post(f"/api/agents/{self.n}/status", {"status": "busy"})
                msgs = [{"role": "system", "content": self.sys}, {"role": "user", "content": m["content"]}]
                try:
                    r2 = requests.post("https://api.deepseek.com/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, json={"model": self.model, "messages": msgs}).json()
                    reply = r2["choices"][0]["message"]["content"]
                    self.post("/api/chat", {"content": reply, "sender": self.n})
                except Exception as e:
                    print(f"[{self.n}] Error: {e}")
                self.post(f"/api/agents/{self.n}/status", {"status": "online"})
            await asyncio.sleep(self.p)
