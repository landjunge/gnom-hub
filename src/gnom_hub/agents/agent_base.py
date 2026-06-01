import asyncio, os, logging, threading, requests; from gnom_hub.soul import get_soul; from gnom_hub.infrastructure.router.router import ask_router
HUB_URL = f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}"
class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        from collections import OrderedDict
        self.n, self.d, self.t, self.sys, self.p = name, desc, trigger, sys_prompt, poll
        self._seen_ids = OrderedDict()  # Bounded LRU set (replaces deque+set)
        self._seen_max = 1000
        self._seen_lock = threading.Lock()
        from gnom_hub.agents.tool_registry import format_tools_prompt
        t_p = format_tools_prompt(get_soul(name), name)
        self.sys = (self.sys + "\n\n" + t_p) if self.sys else t_p
        
        # Injektion der geistigen Denkprozess-Richtlinie fuer die Showbox-Anzeige
        think_guideline = (
            "\n\n[WICHTIGE GEISTIGE RICHTLINIE]\n"
            "Beginne JEDE Antwort zwingend mit einem ausfuehrlichen Denkprozess in <think>...</think>-Tags.\n"
            "Darin musst du deine logischen Schritte, deine Planung, deine Intentions-Abwaegungen und "
            "deine Gedanken dokumentieren. Erst NACH dem schliessenden </think> folgt deine eigentliche Antwort."
        )
        self.sys += think_guideline
    def _req(self, method, p, j=None):
        try:
            r = getattr(requests, method)(f"{HUB_URL}{p}", json=j, timeout=10)
            if r.status_code == 200: return r.json()
        except Exception as e: logging.getLogger(__name__).error('Fehler in _req (%s %s): %s', method, p, e)
        return None
    def _mark_seen(self, msg_id):
        with self._seen_lock:
            if msg_id in self._seen_ids:
                self._seen_ids.move_to_end(msg_id)
                return
            self._seen_ids[msg_id] = True
            while len(self._seen_ids) > self._seen_max:
                self._seen_ids.popitem(last=False)
    async def run(self):
        while not self._req("post", "/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]}):
            print(f"⚠️ {self.n}: Hub nicht erreichbar. Reconnect in 5s..."); await asyncio.sleep(5)
        for m in (self._req("get", "/api/chat?limit=10") or []): self._mark_seen(m.get("id"))
        print(f"🚀 {self.n} aktiv")
        while True:
            c = self._req("get", "/api/chat?limit=10")
            if c is None: print(f"⚠️ {self.n}: Hub offline. Versuche Reconnect..."); await asyncio.sleep(5); continue
            self._req("post", f"/api/agents/{self.n}/heartbeat")
            with self._seen_lock:
                _seen_copy = set(self._seen_ids.keys())
            new = [m for m in c if m.get("id") not in _seen_copy and m.get("metadata",{}).get("sender","") in ("user", "GeneralAG") and (self.t.lower() in m.get("content", "").lower() or "@all" in m.get("content", "").lower())]
            for m in c: self._mark_seen(m.get("id"))
            if new:
                self._req("put", f"/api/agents/{self.n}/status?status=busy")
                try:
                    for m in new:
                        try:
                            from gnom_hub.soul import soul_instance
                            sys = soul_instance.inject_context(self.sys, m["content"], agent_name=self.n)
                            r = await asyncio.to_thread(ask_router, m["content"], sys, agent_name=self.n)
                            if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
                                from gnom_hub.agents.actions.action_handlers import process_actions
                                from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
                                wd = get_workspace_dir()
                                soul = get_soul(self.n) or {"permissions": ["read"]}
                                perms = soul.get("permissions", [])
                                processed = await asyncio.to_thread(process_actions, r.content, {"name": self.n}, perms, False, wd)
                                import re
                                think_match = re.search(r'(<think>[\s\S]*?</think>)', r.answer)
                                if think_match:
                                    think_prefix = think_match.group(1) + "\n\n"
                                else:
                                    # Fallback-Denkprozess aus der reasoning_chain generieren
                                    steps_str = "\n".join(f"- {step}" for step in r.reasoning_chain)
                                    think_prefix = f"<think>\n🧠 [Denkprozess & Logik fuer {self.n}]\n{steps_str}\n</think>\n\n"
                                self._req("post", "/api/chat", {"content": think_prefix + processed, "sender": self.n})
                        except Exception as e: print(f"[{self.n}] Error: {e}")
                finally:
                    self._req("put", f"/api/agents/{self.n}/status?status=online")
            await asyncio.sleep(self.p)
