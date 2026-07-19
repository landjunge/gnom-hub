import asyncio
import logging
import os
import threading

import requests

from gnom_hub.db.connection import get_db_conn
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.soul import get_soul

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
HUB_URL = f"http://127.0.0.1:{os.environ.get('GNOM_HUB_PORT', '3002')}"

# Prio-5: after GeneralAG delegates, warn if workers still idle.
WORKER_WATCH_SECONDS = 90
_WORKER_MENTION_RE = __import__("re").compile(
    r"@(CoderAG|WriterAG|EditorAG|ResearcherAG)\b",
    __import__("re").IGNORECASE,
)


def _schedule_worker_reply_watch(agent_req, content: str, context_id: str) -> None:
    """Daemon: if delegated workers have no done msg within timeout, post System chat."""
    workers = {m.group(1) for m in _WORKER_MENTION_RE.finditer(content or "")}
    if not workers:
        return

    def _watch():
        import time as _time
        _time.sleep(WORKER_WATCH_SECONDS)
        try:
            from gnom_hub.db.connection import get_db_conn
            stuck = []
            with get_db_conn() as conn:
                for w in workers:
                    # Still pending/processing for this context?
                    row = conn.execute(
                        """
                        SELECT COUNT(*) AS c FROM agent_messages
                        WHERE recipient = ?
                          AND status IN ('pending', 'processing')
                          AND (context_id = ? OR context_id IS NULL OR context_id = '')
                          AND created_at > ?
                        """,
                        (w, context_id, _time.time() - WORKER_WATCH_SECONDS - 30),
                    ).fetchone()
                    c = row["c"] if hasattr(row, "keys") else row[0]
                    if c and int(c) > 0:
                        stuck.append(f"{w}({c})")
            if stuck:
                agent_req(
                    "post",
                    "/api/chat",
                    {
                        "content": (
                            f"⏱️ **[GeneralAG Watch]** Nach {WORKER_WATCH_SECONDS}s noch offene "
                            f"Worker-Jobs: {', '.join(stuck)}. "
                            f"Health prüfen: `GET /api/agents/health` oder Hub-Logs."
                        ),
                        "sender": "System",
                    },
                )
        except Exception as e:
            logging.getLogger(__name__).debug("worker reply watch failed: %s", e)

    threading.Thread(target=_watch, name="worker-reply-watch", daemon=True).start()


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

        name_lower = name.lower()
        # GeneralAG: Orchestrator-Prompt hat bereits optionales Thinking + User-Sichtbarkeit.
        # Harte Pflicht-<think> bläht Latenz und führt oft zu "nur Think, kein Output".
        if "general" not in name_lower:
            think_guideline = (
                "\n\n[WICHTIGE GEISTIGE RICHTLINIE]\n"
                "Beginne JEDE Antwort zwingend mit einem ausfuehrlichen Denkprozess in <think>...</think>-Tags.\n"
                "Darin musst du deine logischen Schritte, deine Planung, deine Intentions-Abwaegungen und "
                "deine Gedanken dokumentieren. Erst NACH dem schliessenden </think> folgt deine eigentliche Antwort."
            )
            self.sys += think_guideline

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

    def _req(self, method, p, j=None, timeout=None):
        # Claim may block on hub up to ~2s (+ DB wait). Under lock storms 10s
        # was too tight → SoulAG "Read timed out" on /api/queue/claim.
        if timeout is None:
            timeout = 20 if p and "/queue/claim" in p else 10
        try:
            r = getattr(requests, method)(f"{HUB_URL}{p}", json=j, timeout=timeout)
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
        import functools
        import time

        from gnom_hub.agents.swarm.swarm_comms import ack_message, fetch_next_message, nack_message
        from gnom_hub.core.config import DB_PATH
        from gnom_hub.queue import use_hub_claim

        async def _to_thread(func, *args, **kwargs):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

        def _hub_claim(timeout: float = 0.5):
            """Claim via hub HTTP — only hub process holds SQLite lease locks.

            HTTP client timeout must exceed long-poll wait (PLAN claim HTTP ≥ claim wait).
            """
            http_to = max(float(timeout) + 2.0, 5.0)
            r = self._req(
                "post",
                "/api/queue/claim",
                {"agent": self.n, "timeout": timeout},
                timeout=http_to,
            )
            if not r or r.get("status") != "ok":
                return None
            return r.get("message")

        def _hub_ack(msg_id: int):
            self._req("post", "/api/queue/ack", {"msg_id": msg_id, "agent": self.n})

        def _hub_nack(msg_id: int, reason: str = ""):
            self._req("post", "/api/queue/nack", {
                "msg_id": msg_id, "agent": self.n, "reason": (reason or "")[:300],
            })

        hub_claim = use_hub_claim()
        if hub_claim:
            print(f"📡 {self.n}: Queue-Modus hub-claim (kein SQLite-Write im Agent)")

        # Register: accept soft-OK dict (even on DB contention) so we don't spin-lock the hub
        _reg_backoff = 3
        while True:
            r = self._req("post", "/api/agents/register", {
                "name": self.n, "port": 0, "description": self.d,
                "status": "online", "capabilities": [self.t],
            })
            if r is not None:
                break
            print(f"⚠️ {self.n}: Hub nicht erreichbar. Reconnect in {_reg_backoff}s...")
            await asyncio.sleep(_reg_backoff)
            _reg_backoff = min(_reg_backoff + 2, 20)

        print(f"🚀 {self.n} aktiv (Warteschlange)")

        await _to_thread(self._register_capabilities)

        _last_hb = 0.0
        while True:
            # Heartbeat max 1× / 10s — was every poll (~2/s × 8 agents = DB storm)
            now_ts = time.time()
            if now_ts - _last_hb >= 10.0:
                self._req("post", f"/api/agents/{self.n}/heartbeat")
                _last_hb = now_ts

            # Claim next message: hub API (default) or legacy direct SQLite
            try:
                if hub_claim:
                    msg = await _to_thread(_hub_claim, 0.8)
                else:
                    msg = await _to_thread(fetch_next_message, self.n, str(DB_PATH), 3.0)
            except Exception as fetch_exc:
                logging.getLogger(__name__).warning(
                    "%s fetch/claim: %s", self.n, fetch_exc
                )
                await asyncio.sleep(1.0)
                continue
            if msg is None:
                await asyncio.sleep(0.8 if hub_claim else 1.0)
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
                        from gnom_hub.memory.mermaid_canvas import build_canvas as _build_canvas
                        from gnom_hub.memory.offload import (
                            OffloadConfig as _OffCfg,
                        )
                        from gnom_hub.memory.offload import (
                            get_offloader as _get_offloader,
                        )
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

                # ── Deterministic Routing Supplement (opt-in) ─────────────
                # Wenn ``Config.ROUTING_DETERMINISTIC_MODE`` aktiviert ist,
                # läuft zusätzlich zum LLM-basierten ask_router ein
                # deterministischer Capability-Resolver. Das Ergebnis
                # ersetzt die ask_router-Pfadführung NICHT — es wird nur
                # geloggt + im State-Store abgelegt, damit Operatoren die
                # Routing-Decisions inspizieren können. Modul
                # ``gnom_hub.agents.routing``.
                try:
                    from gnom_hub.core.config import Config as _DetCfg
                    if getattr(_DetCfg, "ROUTING_DETERMINISTIC_MODE", False):
                        from gnom_hub.agents.routing import (
                            resolve_capability as _det_resolve,
                        )
                        # Verfügbare Capabilities aus der DB laden
                        _avail_caps: list[str] = []
                        try:
                            with get_db_conn() as _cap_conn:
                                _rows = _cap_conn.execute(
                                    "SELECT DISTINCT capability FROM agent_capabilities"
                                ).fetchall()
                                _avail_caps = [r["capability"] for r in _rows]
                        except Exception:
                            _avail_caps = []
                        _det_resolved = _det_resolve(text, _avail_caps or None)
                        _det_logger = logging.getLogger(__name__)
                        _log_level = getattr(
                            _DetCfg, "ROUTING_LOG_LEVEL", "info"
                        )
                        _det_log_fn = getattr(
                            _det_logger,
                            _log_level if _log_level in ("debug", "info", "warning") else "info",
                            _det_logger.info,
                        )
                        _det_log_fn(
                            "[det-routing] %s → capability=%r confidence=%.2f source=%s (avail=%d)",
                            self.n, _det_resolved.capability,
                            _det_resolved.confidence, _det_resolved.source,
                            len(_avail_caps),
                        )
                        # In den State-Store schreiben (rotationsbegrenzt)
                        try:
                            from gnom_hub.db.state_repo import SQLiteStateRepository
                            _det_store = SQLiteStateRepository()
                            _det_key = f"routing_resolution_{self.n}"
                            _det_log = _det_store.get_value(_det_key) or []
                            _det_threshold = float(
                                getattr(_DetCfg, "ROUTING_RESOLUTION_LOG_MIN_CONF", 0.3)
                            )
                            if _det_resolved.source != "none" and _det_resolved.confidence >= _det_threshold:
                                _det_log.append({
                                    "ts": time.time(),
                                    "msg_id": msg["msg_id"],
                                    "text": text[:200],
                                    "capability": _det_resolved.capability,
                                    "confidence": _det_resolved.confidence,
                                    "source": _det_resolved.source,
                                })
                                _max = int(
                                    getattr(_DetCfg, "ROUTING_RESOLUTION_LOG_MAX", 50)
                                )
                                if len(_det_log) > _max:
                                    _det_log = _det_log[-_max:]
                                _det_store.set_value(_det_key, _det_log)
                        except Exception as _det_store_exc:
                            _det_logger.debug(
                                "deterministic routing state-store write failed: %s",
                                _det_store_exc,
                            )
                except Exception as _det_exc:
                    logging.getLogger(__name__).debug(
                        "deterministic routing hook failed (non-fatal): %s",
                        _det_exc,
                    )

                # Timeout-Check (600s = 10 Min, war 300s)
                if time.time() - _processing_start > 600:
                    raise TimeoutError(f"Verarbeitung von msg#{msg['msg_id']} dauerte >10 Min (msg_id={msg['msg_id']})")

                processed = ""
                raw_content = (getattr(r, "content", None) or "").strip() if r is not None else ""
                job_ok = True
                import re as _re

                # Wave A anti-spam: chat display cap vs action-processor cap.
                # R5/R4 bug: action_in was raw_content[:6000] → multi-file
                # [WRITE:]...[/WRITE] for v1/v2/v3 HTML was chopped before
                # process_actions, so Coder "wrote" nothing. Chat stays short;
                # action tags use the full model output (bounded).
                MAX_REPLY = 6000
                MAX_ACTION_INPUT = 120_000
                MAX_RAW_ACCEPT = 100_000
                if raw_content and len(raw_content) > MAX_RAW_ACCEPT:
                    # pathological free-model dump — refuse to amplify
                    job_ok = False
                    self._req("post", "/api/chat", {
                        "content": (
                            f"⚠️ **[{self.n}]** Antwort verworfen (Spam/Überlänge "
                            f"{len(raw_content)} Zeichen). Nachricht #{msg['msg_id']} → NACK.\n"
                            f"→ Nochmal senden oder anderes Modell in UI/`config/routing.txt` wählen."
                        ),
                        "sender": "System",
                    })
                    ctx_logger.warning("Spam-length reply msg#%s len=%d", msg["msg_id"], len(raw_content))
                    raw_content = ""

                # ── Prio-1: nie still schlucken ────────────────────────────
                if not raw_content:
                    job_ok = False
                    self._req("post", "/api/chat", {
                        "content": (
                            f"⚠️ **[{self.n}]** Keine Antwort vom LLM (leerer Content). "
                            f"Nachricht #{msg['msg_id']} → NACK.\n"
                            f"→ Nochmal senden · Provider/Key prüfen (UI LLM oder "
                            f"`config/routing.txt`, optional `~/Desktop/api_keys.txt`)."
                        ),
                        "sender": "System",
                    })
                    ctx_logger.warning("Leere LLM-Antwort für msg#%s", msg["msg_id"])
                elif raw_content.startswith("[ROUTER-FEHLER]"):
                    job_ok = False
                    self._req("post", "/api/chat", {
                        "content": (
                            f"⚠️ **[{self.n}]** LLM-Router fehlgeschlagen → NACK.\n"
                            f"{raw_content[:400]}\n"
                            f"→ Keys/Routing prüfen (`config/routing.txt`, UI, Desktop-Keys). "
                            f"Nachricht #{msg['msg_id']} — danach erneut senden."
                        ),
                        "sender": "System",
                    })
                    ctx_logger.error("ROUTER-FEHLER für msg#%s: %s", msg["msg_id"], raw_content[:200])
                else:
                    # Strip think blocks for substance check
                    without_think = _re.sub(
                        r'<think>[\s\S]*?</think>', '', raw_content,
                        flags=_re.IGNORECASE | _re.DOTALL,
                    ).strip()
                    # Also strip zero-width / garbage
                    without_think = _re.sub(r'[\u200b-\u200d\ufeff]+', '', without_think).strip()
                    if len(without_think) < 8 and len(raw_content) > 80:
                        job_ok = False
                        self._req("post", "/api/chat", {
                            "content": (
                                f"⚠️ **[{self.n}]** Nur Think-Spam ohne Nutzinhalt "
                                f"(msg #{msg['msg_id']}) → NACK.\n"
                                f"→ Nochmal senden oder robusteres Modell in UI/`routing.txt`."
                            ),
                            "sender": "System",
                        })
                        ctx_logger.warning("think-only spam msg#%s", msg["msg_id"])
                    else:
                        from gnom_hub.agents.actions.action_handlers import process_actions
                        from gnom_hub.chat.brainstorm.brainstorm_helpers import get_workspace_dir
                        soul = get_soul(self.n) or {"permissions": ["read"]}
                        perms = soul.get("permissions", [])
                        wd = get_workspace_dir()
                        # Full model output for actions (WRITE/SCREENSHOT tags live here)
                        action_in = raw_content[:MAX_ACTION_INPUT]
                        processed = await _to_thread(
                            process_actions, action_in, {"name": self.n}, perms, False, wd
                        )

                        # ── READ-only → WRITE continue (R5 Coder gap) ─────
                        # Single-shot agents often emit only [READ:] then stop.
                        # If the task demanded [WRITE:] and none was produced,
                        # one forced follow-up with the read results.
                        _write_pat = _re.compile(
                            r"\[WRITE:\s*[^\]]+\][\s\S]*?\[/WRITE\]",
                            _re.IGNORECASE,
                        )
                        _task_wants_write = bool(
                            _re.search(r"\[WRITE:", text or "", _re.IGNORECASE)
                        )
                        _had_write = bool(_write_pat.search(raw_content or ""))
                        _had_read = bool(
                            _re.search(r"\[READ:\s*", raw_content or "", _re.IGNORECASE)
                        )
                        _workers = (
                            "coderag", "writerag", "researcherag", "editorag",
                        )
                        if (
                            job_ok
                            and self.n.lower() in _workers
                            and _task_wants_write
                            and not _had_write
                        ):
                            try:
                                read_excerpt = (processed or action_in or "")[:5000]
                                cont = (
                                    "SYSTEM-CONTINUE (einmalig): Du hast die Quelle gelesen "
                                    "oder den Auftrag bestätigt, aber KEIN vollständiges "
                                    "[WRITE: rel/pfad]inhalt[/WRITE] geliefert.\n"
                                    "Original-Auftrag (gekürzt):\n"
                                    f"{(text or '')[:2800]}\n\n"
                                    "Kontext aus deiner vorherigen Antwort (READ/System):\n"
                                    f"{read_excerpt}\n\n"
                                    "JETZT PFLICHT: Schreibe ALLE geforderten Dateien mit "
                                    "vollem Inhalt als [WRITE: pfad]...[/WRITE]. "
                                    "Danach ggf. [SCREENSHOT: ...]. "
                                    "Kein reines ACK, kein erneutes langes READ, kein Showbox-only."
                                )
                                r2 = await _to_thread(
                                    ask_router,
                                    cont,
                                    None,
                                    agent_name=self.n,
                                    depth=msg["depth"],
                                    parent_msg_id=msg["msg_id"],
                                )
                                raw2 = (
                                    (getattr(r2, "content", None) or "").strip()
                                    if r2 is not None
                                    else ""
                                )
                                if raw2 and not raw2.startswith("[ROUTER-FEHLER]"):
                                    if len(raw2) > MAX_RAW_ACCEPT:
                                        ctx_logger.warning(
                                            "WRITE-continue spam len=%d msg#%s",
                                            len(raw2), msg["msg_id"],
                                        )
                                    else:
                                        raw_content = raw_content + "\n\n" + raw2
                                        action_in2 = raw2[:MAX_ACTION_INPUT]
                                        processed2 = await _to_thread(
                                            process_actions,
                                            action_in2,
                                            {"name": self.n},
                                            perms,
                                            False,
                                            wd,
                                        )
                                        processed = (
                                            (processed or "")
                                            + "\n\n"
                                            + (processed2 or action_in2)
                                        )
                                        ctx_logger.info(
                                            "WRITE-continue after READ-only msg#%s "
                                            "agent=%s cont_len=%d",
                                            msg["msg_id"], self.n, len(raw2),
                                        )
                            except Exception as cont_exc:
                                ctx_logger.warning(
                                    "WRITE-continue failed msg#%s: %s",
                                    msg["msg_id"], cont_exc,
                                )

                        raw = processed or action_in
                        think_display = _re.sub(
                            r'<think>([\s\S]*?)</think>',
                            r'\n[💭 \1]\n',
                            raw, flags=_re.IGNORECASE | _re.DOTALL
                        ).strip()
                        # Truncate chat post — never dump 50k tokens into war-room
                        if len(think_display) > MAX_REPLY:
                            think_display = think_display[:MAX_REPLY] + "\n… [gekürzt]"
                        if not think_display.strip():
                            self._req("post", "/api/chat", {
                                "content": (
                                    f"⚠️ **[{self.n}]** Antwort war nach Action-Processing leer "
                                    f"(msg #{msg['msg_id']}). Roh-Länge: {len(raw_content)}."
                                ),
                                "sender": "System",
                            })
                            job_ok = False
                        else:
                            self._req("post", "/api/chat", {"content": think_display, "sender": self.n})
                            # Only GeneralAG may fan-out worker watches; workers never storm
                            if self.n.lower() == "generalag" and job_ok:
                                try:
                                    _schedule_worker_reply_watch(
                                        self._req, think_display, msg.get("context_id") or "default"
                                    )
                                except Exception:
                                    pass

                        # SoulAG observation — only on successful short-enough thoughts
                        think_match = _re.search(
                            r'<think>([\s\S]*?)</think>', raw, flags=_re.IGNORECASE | _re.DOTALL
                        )
                        if job_ok and think_match and think_match.group(1).strip():
                            try:
                                from gnom_hub.soul.zwc_soul import extract_facts_from_text
                                thought = think_match.group(1).strip()[:800]
                                await _to_thread(extract_facts_from_text, thought, self.n)
                            except Exception as e:
                                logging.getLogger(__name__).debug(
                                    "SoulAG-Thought-Extract fehlgeschlagen: %s", e
                                )

                # P0: empty / ROUTER-FEHLER must NACK (retry/backoff), never ACK done.
                if job_ok:
                    if hub_claim:
                        await _to_thread(_hub_ack, msg["msg_id"])
                    else:
                        await _to_thread(ack_message, msg["msg_id"], str(DB_PATH))
                else:
                    reason = raw_content[:200] if raw_content else "empty_llm_response"
                    if hub_claim:
                        await _to_thread(_hub_nack, msg["msg_id"], reason)
                    else:
                        await _to_thread(
                            nack_message, msg["msg_id"], str(DB_PATH), reason
                        )
                    ctx_logger.warning(
                        "msg#%s nack (llm fail): %s", msg["msg_id"], reason[:80]
                    )

                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {
                        "status": "success" if job_ok else "error",
                        "content": processed if job_ok else raw_content[:500],
                    },
                })
                # Job in CoordinationDB + ContextDB aufzeichnen
                try:
                    from gnom_hub.soul.memory_layers import get_context_db, get_coordination_db
                    get_coordination_db().record_job(
                        worker=self.n,
                        task_summary=text[:100],
                        result="success" if job_ok else "failed",
                        duration_s=round(time.time() - _processing_start, 1),
                        context_id=msg.get("context_id"),
                        notes="" if job_ok else (raw_content[:200] or "empty/router error"),
                    )
                    get_context_db().add_event(
                        msg["context_id"],
                        "completed" if job_ok else "failed",
                        self.n,
                        (processed or raw_content)[:100],
                    )
                    if self.n.lower() == "generalag" and job_ok:
                        get_context_db().close_context(msg["context_id"], "completed", processed[:200] if processed else "")
                except Exception:
                    pass

            except Exception as e:
                ctx_logger.error(f"Fehler bei Verarbeitung: {e}", exc_info=True)
                if hub_claim:
                    await _to_thread(_hub_nack, msg["msg_id"], str(e))
                else:
                    await _to_thread(nack_message, msg["msg_id"], str(DB_PATH), str(e))
                self._req("post", "/api/swarm/complete", {
                    "context_id": msg["context_id"],
                    "agent_name": self.n,
                    "result": {"status": "error", "error": str(e)}
                })
                # Job-Fehler in CoordinationDB + ContextDB aufzeichnen
                try:
                    from gnom_hub.soul.memory_layers import get_context_db, get_coordination_db
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

                # Sofort sichtbare Fehler-Zeile (nicht erst bei Dead-Letter)
                try:
                    retry_count = msg.get("retry_count", 0) or 0
                    _task_text = text[:100] if "text" in dir() else "unknown"
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
                    else:
                        self._req("post", "/api/chat", {
                            "content": (
                                f"⚠️ **[{self.n}]** Verarbeitungsfehler "
                                f"(Versuch {retry_count + 1}, wird erneut versucht):\n"
                                f"`{str(e)[:200]}`"
                            ),
                            "sender": "System",
                        })
                except Exception:
                    pass

            finally:
                self._req("put", f"/api/agents/{self.n}/status?status=online")

    def _register_capabilities(self):
        import json as _json
        import sqlite3
        import time as _t
        from gnom_hub.db.connection import get_db_conn
        # Keep agents.capabilities column in sync with definitions (UI showed [] for CoderAG)
        caps_list = [c for c, _conf in getattr(self, "CAPABILITIES", [])]
        try:
            from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
            defn = AGENT_DEFINITIONS.get(self.n.lower(), {})
            for c in defn.get("capabilities") or []:
                if c not in caps_list:
                    caps_list.append(c)
            for p in (defn.get("de") or defn.get("en") or {}).get("permissions") or []:
                if p not in caps_list:
                    caps_list.append(p)
        except Exception:
            pass
        for _attempt in range(4):
            try:
                with get_db_conn() as db:
                    db.execute("DELETE FROM agent_capabilities WHERE agent_name = ?", (self.n,))
                    for capability, confidence in getattr(self, "CAPABILITIES", []):
                        db.execute("""
                            INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence)
                            VALUES (?, ?, ?)
                        """, (self.n, capability, confidence))
                    # Persist visible rights for dashboard /api/agents list
                    if caps_list:
                        db.execute(
                            "UPDATE agents SET capabilities = ? WHERE lower(name) = lower(?)",
                            (_json.dumps(caps_list), self.n),
                        )
                    db.commit()
                return
            except sqlite3.OperationalError as e:
                if "locked" not in str(e).lower() or _attempt == 3:
                    logging.getLogger(__name__).warning(
                        "%s capability register soft-fail: %s", self.n, e
                    )
                    return
                _t.sleep(0.15 * (2 ** _attempt))
