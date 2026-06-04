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
        from gnom_hub.agents.swarm.swarm_comms import fetch_next_message, ack_message, nack_message
        from gnom_hub.core.config import DB_PATH
        import time
        import functools

        async def _to_thread(func, *args, **kwargs):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

        while not self._req("post", "/api/agents/register", {"name": self.n, "port": 0, "description": self.d, "status": "online", "capabilities": [self.t]}):
            print(f"⚠️ {self.n}: Hub nicht erreichbar. Reconnect in 5s..."); await asyncio.sleep(5)

        print(f"🚀 {self.n} aktiv (Warteschlange)")

        while True:
            # Heartbeat senden
            self._req("post", f"/api/agents/{self.n}/heartbeat")

            # Hole nächste Nachricht aus der DB-Warteschlange (Timeout 5s)
            msg = await _to_thread(fetch_next_message, self.n, str(DB_PATH), 5.0)
            if msg is None:
                await asyncio.sleep(1)
                continue

            # Status auf beschäftigt setzen
            self._req("put", f"/api/agents/{self.n}/status?status=busy")

            try:
                # Payload parsen
                text = msg["payload"]["text"]

                from gnom_hub.soul import soul_instance
                sys_prompt = soul_instance.inject_context(self.sys, text, agent_name=self.n)

                # Workspace und Dateien-Kontext für den Agenten hinzufügen
                from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
                wd = get_workspace_dir()
                fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
                sys_prompt += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"

                r = await _to_thread(ask_router, text, sys_prompt, agent_name=self.n, depth=msg["depth"])

                processed = ""
                if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
                    from gnom_hub.agents.actions.action_handlers import process_actions
                    soul = get_soul(self.n) or {"permissions": ["read"]}
                    perms = soul.get("permissions", [])
                    processed = await _to_thread(process_actions, r.content, {"name": self.n}, perms, False, wd)

                    import re
                    think_match = re.search(r'(<think>[\s\S]*?</think>)', r.answer)
                    if think_match:
                        think_prefix = think_match.group(1) + "\n\n"
                    else:
                        steps_str = "\n".join(f"- {step}" for step in r.reasoning_chain)
                        think_prefix = f"<think>\n🧠 [Denkprozess & Logik für {self.n}]\n{steps_str}\n</think>\n\n"

                    self._req("post", "/api/chat", {"content": think_prefix + processed, "sender": self.n})

                # Acknowledge in the queue
                await _to_thread(ack_message, msg["msg_id"], str(DB_PATH))

                # Signal completion to coordinator (cross-process HTTP)
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "success", "content": processed}
                })

            except Exception as e:
                print(f"[{self.n}] Fehler bei Verarbeitung: {e}")
                await _to_thread(nack_message, msg["msg_id"], str(DB_PATH), str(e))
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "error", "error": str(e)}
                })

            finally:
                self._req("put", f"/api/agents/{self.n}/status?status=online")
