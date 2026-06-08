import asyncio, os, logging, threading, requests; from gnom_hub.soul import get_soul; from gnom_hub.infrastructure.router.router import ask_router
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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

        # Map agent name to capabilities
        name_lower = name.lower()
        if "coder" in name_lower:
            self.CAPABILITIES = [("code_generation", 1.0), ("code_review", 0.9), ("debugging", 0.8)]
        elif "security" in name_lower:
            self.CAPABILITIES = [("security_audit", 1.0), ("vulnerability_scan", 0.9)]
        elif "writer" in name_lower:
            self.CAPABILITIES = [("content_creation", 1.0), ("summarization", 0.9), ("editing", 0.8)]
        elif "researcher" in name_lower:
            self.CAPABILITIES = [("web_research", 1.0), ("fact_checking", 0.9), ("summarization", 0.7)]
        elif "editor" in name_lower:
            self.CAPABILITIES = [("editing", 1.0), ("summarization", 0.8)]
        elif "soul" in name_lower:
            self.CAPABILITIES = [("profile_management", 1.0)]
        elif "general" in name_lower:
            self.CAPABILITIES = [("coordination", 1.0)]
        elif "watchdog" in name_lower:
            self.CAPABILITIES = [("monitoring", 1.0)]
        else:
            self.CAPABILITIES = []

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

        await _to_thread(self._register_capabilities)

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

            logger = logging.getLogger(__name__)
            ctx_logger = logging.LoggerAdapter(logger, {
                "context_id": msg["context_id"],
                "agent_name": self.n,
                "msg_id": msg["msg_id"],
            })
            ctx_logger.info(f"Agent {self.n} verarbeitet Nachricht {msg['msg_id']}")

            try:
                # Timeout für einzelne Nachrichtenverarbeitung (max 5 Minuten)
                _processing_start = time.time()

                # Payload parsen
                text = msg["payload"]["text"]

                from gnom_hub.soul import soul_instance
                sys_prompt = soul_instance.inject_context(self.sys, text, agent_name=self.n)

                # Workspace und Dateien-Kontext für den Agenten hinzufügen
                from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
                wd = get_workspace_dir()
                fs = ", ".join(os.listdir(wd)) if os.path.exists(wd) else ""
                sys_prompt += f"\n\n[WORKSPACE: {wd} | Dateien: {fs}]"

                r = await _to_thread(ask_router, text, sys_prompt, agent_name=self.n, depth=msg["depth"], parent_msg_id=msg["msg_id"])

                # Timeout-Check nach LLM-Call
                if time.time() - _processing_start > 300:
                    raise TimeoutError(f"Verarbeitung von msg#{msg['msg_id']} dauerte >5 Min (msg_id={msg['msg_id']})")

                processed = ""
                if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
                    from gnom_hub.agents.actions.action_handlers import process_actions
                    soul = get_soul(self.n) or {"permissions": ["read"]}
                    perms = soul.get("permissions", [])
                    processed = await _to_thread(process_actions, r.content, {"name": self.n}, perms, False, wd)

                    import re as _re
                    raw = processed or r.content
                    # Think-Block formatieren statt löschen: in Chat sichtbar machen
                    think_display = _re.sub(
                        r'<think>([\s\S]*?)</think>',
                        r'\n[💭 \1]\n',
                        raw, flags=_re.IGNORECASE | _re.DOTALL
                    ).strip()
                    self._req("post", "/api/chat", {"content": think_display, "sender": self.n})

                # Acknowledge in the queue
                await _to_thread(ack_message, msg["msg_id"], str(DB_PATH))

                # Signal completion to coordinator (cross-process HTTP)
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "success", "content": processed}
                })

            except Exception as e:
                ctx_logger.error(f"Fehler bei Verarbeitung: {e}", exc_info=True)
                await _to_thread(nack_message, msg["msg_id"], str(DB_PATH), str(e))
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "error", "error": str(e)}
                })

            finally:
                self._req("put", f"/api/agents/{self.n}/status?status=online")

    def _register_capabilities(self):
        from gnom_hub.db.connection import get_db_conn
        with get_db_conn() as db:
            db.execute("DELETE FROM agent_capabilities WHERE agent_name = ?", (self.n,))
            for capability, confidence in getattr(self, "CAPABILITIES", []):
                db.execute("""
                    INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence)
                    VALUES (?, ?, ?)
                """, (self.n, capability, confidence))
            db.commit()
