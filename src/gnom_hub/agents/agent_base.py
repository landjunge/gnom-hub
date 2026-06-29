import asyncio, os, logging, threading, requests; from gnom_hub.soul import get_soul; from gnom_hub.infrastructure.router.router import ask_router
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
HUB_URL = f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}"
class BaseAgent:
    def __init__(self, name, desc, trigger, sys_prompt=None, poll=5, model="deepseek-chat"):
        from collections import OrderedDict
        self.n, self.d, self.t, self.sys, self.p = name, desc, trigger, sys_prompt, poll
        self._seen_ids = OrderedDict()
        self._seen_max = 1000
        self._seen_lock = threading.Lock()
        from gnom_hub.agents.tool_registry import format_tools_prompt
        t_p = format_tools_prompt(get_soul(name), name)
        self.sys = (self.sys + "\n\n" + t_p) if self.sys else t_p

        think_guideline = (
            "\n\n[WICHTIGE GEISTIGE RICHTLINIE]\n"
            "Beginne JEDE Antwort zwingend mit einem ausfuehrlichen Denkprozess in <think>...</think>-Tags.\n"
            "Darin musst du deine logischen Schritte, deine Planung, deine Intentions-Abwaegungen und "
            "deine Gedanken dokumentieren. Erst NACH dem schliessenden </think> folgt deine eigentliche Antwort."
        )
        self.sys += think_guideline

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
            self._req("post", f"/api/agents/{self.n}/heartbeat")

            # Hole nächste Nachricht (Timeout 3s, war 5s)
            msg = await _to_thread(fetch_next_message, self.n, str(DB_PATH), 3.0)
            if msg is None:
                await asyncio.sleep(0.5)  # (war 1.0)
                continue

            self._req("put", f"/api/agents/{self.n}/status?status=busy")

            logger = logging.getLogger(__name__)
            ctx_logger = logging.LoggerAdapter(logger, {
                "context_id": msg["context_id"],
                "agent_name": self.n,
                "msg_id": msg["msg_id"],
            })
            ctx_logger.info(f"Agent {self.n} verarbeitet Nachricht {msg['msg_id']}")

            try:
                _processing_start = time.time()

                text = msg["payload"]["text"]

                # Context in ContextDB öffnen
                try:
                    from gnom_hub.soul.memory_layers import get_context_db
                    get_context_db().open_context(msg["context_id"], text[:200], created_by=msg.get("sender","user"))
                    get_context_db().add_event(msg["context_id"], "started", self.n)
                except Exception:
                    pass

                from gnom_hub.soul import soul_instance

                # ── Context-Offload: Mermaid-Canvas injizieren ────────────
                # Wenn offload aktiv ist, wird die Mermaid-Task-Canvas aus
                # den bisherigen Offload-Einträgen dieser Session ans
                # System-Prompt angehängt. So behält der Agent eine
                # kompakte Sicht auf vergangene Tool-Outputs, ohne dass
                # der volle Text im Context sitzt. Drill-down erfolgt über
                # das Agent-Tool ``[OFFLOAD_RECALL:node_id]``.
                # Recovert aus experimental/tencentdb-agent-memory (d0f8e95).
                try:
                    from gnom_hub.core.config import Config as _Cfg
                    if getattr(_Cfg, "OFFLOAD_ENABLED", False):
                        from gnom_hub.memory.offload import (
                            get_offloader as _get_offloader,
                            OffloadConfig as _OffCfg,
                        )
                        from gnom_hub.memory.mermaid_canvas import build_canvas as _build_canvas
                        _session_id = str(msg.get("context_id") or self.n)
                        _ocfg = _OffCfg(
                            enabled=True,
                            mild_offload_ratio=_Cfg.OFFLOAD_MILD_RATIO,
                            aggressive_compress_ratio=_Cfg.OFFLOAD_AGGRESSIVE_RATIO,
                            data_dir=_Cfg.OFFLOAD_DATA_DIR,
                            max_tokens=_Cfg.OFFLOAD_MAX_TOKENS,
                        )
                        _off = _get_offloader(_session_id, _ocfg)
                        _threshold = _off.get_threshold_state()
                        _canvas_mode = "aggressive" if _threshold["aggressive"] else "normal"
                        _canvas = _build_canvas(_off.entries, mode=_canvas_mode)
                        if _canvas:
                            sys_prompt = locals().get("sys_prompt", "") + (
                                "\n\n=== OFFLOAD-CANVAS (vergangene Tool-Outputs) ===\n"
                                "Tool-Outputs sind nach Disk ausgelagert. Mit "
                                "[OFFLOAD_RECALL:<node_id>] kannst du den vollen "
                                "Text zurückholen.\n"
                                + _canvas
                            )
                except Exception:
                    # Offload-Canvas ist best-effort; ignorieren bei Fehler
                    pass

                r = await _to_thread(ask_router, text, None, agent_name=self.n, depth=msg["depth"], parent_msg_id=msg["msg_id"])

                # Timeout-Check (600s = 10 Min, war 300s)
                if time.time() - _processing_start > 600:
                    raise TimeoutError(f"Verarbeitung von msg#{msg['msg_id']} dauerte >10 Min (msg_id={msg['msg_id']})")

                processed = ""
                if r.content and not r.content.startswith("[ROUTER-FEHLER]"):
                    from gnom_hub.agents.actions.action_handlers import process_actions
                    from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
                    soul = get_soul(self.n) or {"permissions": ["read"]}
                    perms = soul.get("permissions", [])
                    wd = get_workspace_dir()  # Phase-2-Bugfix: wd war im alten Injections-Block definiert
                    processed = await _to_thread(process_actions, r.content, {"name": self.n}, perms, False, wd)

                    import re as _re
                    raw = processed or r.content
                    think_display = _re.sub(
                        r'<think>([\s\S]*?)</think>',
                        r'\n[💭 \1]\n',
                        raw, flags=_re.IGNORECASE | _re.DOTALL
                    ).strip()
                    self._req("post", "/api/chat", {"content": think_display, "sender": self.n})

                    # ── SoulAG sieht Denkprozesse ────────────────────────
                    # Nach jeder Agent-Antwort den Denkprozess extrahieren
                    # und an SoulAG zur Fakten-Extraktion weiterleiten.
                    # So entstehen langfristig Muster über Strategien,
                    # Erkenntnisse und wiederkehrende Themen.
                    think_match = _re.search(r'<think>([\s\S]*?)</think>', raw, flags=_re.IGNORECASE | _re.DOTALL)
                    if think_match and think_match.group(1).strip():
                        try:
                            from gnom_hub.soul.zwc_soul import extract_facts_from_text
                            thought = think_match.group(1).strip()[:1500]
                            facts = await _to_thread(extract_facts_from_text, thought, self.n)
                            if facts:
                                logging.getLogger(__name__).info(
                                    "SoulAG extrahierte %d Fakt(en) aus Denkprozess von %s",
                                    len(facts), self.n,
                                )
                        except Exception as e:
                            logging.getLogger(__name__).debug("SoulAG-Thought-Extract fehlgeschlagen: %s", e)

                        # ── SoulAG Behavior-Analyst ─────────────────────
                        # Analysiert Denkprozess auf Auffälligkeiten
                        # (Injection, Tool-Mismatch, Failure-Loop, Stuck)
                        # und benachrichtigt GeneralAG wenn nötig.
                        try:
                            from gnom_hub.soul.soul_observer import analyze_agent_thought, notify_generalag
                            analysis = await _to_thread(analyze_agent_thought, self.n, thought)
                            if analysis.get("alerts"):
                                await _to_thread(notify_generalag, analysis)
                                logging.getLogger(__name__).info(
                                    "SoulAG-Observation für %s: %d Alerts",
                                    self.n, len(analysis["alerts"]),
                                )
                        except Exception as e:
                            logging.getLogger(__name__).debug("SoulAG-Observer fehlgeschlagen: %s", e)

                await _to_thread(ack_message, msg["msg_id"], str(DB_PATH))

                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "success", "content": processed}
                })
                # Job-Erfolg in CoordinationDB + ContextDB aufzeichnen
                try:
                    from gnom_hub.soul.memory_layers import get_coordination_db, get_context_db
                    get_coordination_db().record_job(
                        worker=self.n,
                        task_summary=text[:100],
                        result="success",
                        duration_s=round(time.time() - _processing_start, 1),
                        context_id=msg.get("context_id")
                    )
                    get_context_db().add_event(msg["context_id"], "completed", self.n, processed[:100] if processed else "")
                    if self.n.lower() == "generalag":
                        get_context_db().close_context(msg["context_id"], "completed", processed[:200] if processed else "")
                except Exception:
                    pass

            except Exception as e:
                ctx_logger.error(f"Fehler bei Verarbeitung: {e}", exc_info=True)
                await _to_thread(nack_message, msg["msg_id"], str(DB_PATH), str(e))
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "error", "error": str(e)}
                })
                # Job-Fehler in CoordinationDB + ContextDB aufzeichnen
                try:
                    from gnom_hub.soul.memory_layers import get_coordination_db, get_context_db
                    _task_text = text[:100] if "text" in dir() else "unknown"
                    get_coordination_db().record_job(
                        worker=self.n,
                        task_summary=_task_text,
                        result="failed",
                        duration_s=round(time.time() - _processing_start, 1),
                        context_id=msg.get("context_id"),
                        notes=str(e)[:200]
                    )
                    get_context_db().add_event(msg["context_id"], "failed", self.n, str(e)[:200])
                except Exception:
                    pass

                # Dead-Letter Benachrichtigung im Chat wenn retry_count >= 3
                try:
                    retry_count = msg.get("retry_count", 0) or 0
                    if retry_count >= 2:
                        self._req("post", "/api/chat", {
                            "content": (
                                f"💀 **[Dead-Letter]** Nachricht #{msg['msg_id']} von **{msg.get('sender','?')}** "
                                f"an **{self.n}** ist nach {retry_count+1} Versuchen fehlgeschlagen.\n"
                                f"Aufgabe: `{(_task_text)[:80]}`\n"
                                f"Fehler: `{str(e)[:120]}`\n"
                                f"→ Admin: `/api/admin/dead-letters` für Details + Retry."
                            ),
                            "sender": "System"
                        })
                except Exception:
                    pass

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
