import asyncio, json, os, requests
from .soul_initializer import get_soul
from .router import ask_router

HUB_URL = "http://127.0.0.1:3002"

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
            
            sender = lambda m: m.get("metadata",{}).get("sender","")
            new = [m for m in chat if m.get("id") not in self.seen and sender(m) == "user" and (self.n.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in chat: self.seen.add(m.get("id"))
            
            for m in new:
                try:
                    reply = ask_router(m["content"], self.sys, agent_name=self.n)
                    if reply and not reply.startswith("[ROUTER-FEHLER]"):
                        self.post("/api/chat", {"content": reply, "sender": self.n})
                    else:
                        print(f"[{self.n}] Keine Antwort vom LLM")
                except Exception as e:
                    print(f"[{self.n}] Error: {e}")
            await asyncio.sleep(self.p)
