from fastapi import APIRouter
from pydantic import BaseModel

from gnom_hub.chat.brainstorm.brainstorm import dispatch
from gnom_hub.chat.chat_commands import (
    handle_allclear,
    handle_approve_decision,
    handle_bake,
    handle_blockade,
    handle_confirmations,
    handle_diagnose,
    handle_emergency,
    handle_free,
    handle_git,
    handle_help,
    handle_job,
    handle_queue,
    handle_reject_decision,
    handle_resume,
    handle_spass,
    handle_status,
)
from gnom_hub.core.security.showbox_validator import sanitize_showboxes
from gnom_hub.db import add_chat_message, get_active_project, get_all_agents, get_chat_history
from gnom_hub.soul import soul_instance

from .chat_helpers import _handle_sys, _parse

router = APIRouter()
class ChatMsg(BaseModel): content: str; sender: str = "user"
def handle_bs(q): return {"status": "dispatched", "asked": dispatch(q, target=None, sender="user"), "mode": "brainstorm"}
def handle_worker(q):
    import re
    q_clean = re.sub(r'^[\s→>\-:]+', '', q).strip()
    return {"status": "dispatched", "asked": dispatch(q_clean, target="worker", sender="user"), "mode": "worker"}
def handle_workflow(q):
    """@@workflow <Aufgabe> — Erstellt einen Capability-basierten Workflow."""
    import logging

    from gnom_hub.agents.swarm.workflow_engine import create_workflow, start_workflow
    from gnom_hub.chat.chat_commands import _post_chat
    from gnom_hub.db.connection import get_db_conn
    q = q.strip()
    if not q:
        return {"status": "error", "message": "Bitte gib eine Aufgabe an: @@workflow <Aufgabe>"}
    # Capabilities aus der DB laden
    with get_db_conn() as conn:
        caps = conn.execute('SELECT DISTINCT capability FROM agent_capabilities').fetchall()
    available_caps = [r["capability"] for r in caps]
    if not available_caps:
        return {"status": "error", "message": "Keine Capabilities registriert. Starte den Hub neu."}
    # Workflow-Tasks aus der Aufgabe ableiten
    tasks = []
    task_keywords = {
        "web_research": ["recherche", "suche", "finde", "research", "search"],
        "code_generation": ["code", "schreib", "implementier", "program", "erstell", "bau"],
        "content_creation": ["text", "artikel", "blog", "write", "schreib", "verfass"],
        "editing": ["edit", "korrigier", "überarbeit", "review", "prüf"],
        "summarization": ["zusammenfass", "summary", "überblick"],
        "code_review": ["review", "prüf", "check"],
        "security_audit": ["sicherheit", "security", "audit", "vulnerab"],
    }
    # Einfache Heuristik: Welche Capabilities passen zur Aufgabe?
    q_lower = q.lower()
    matched_caps = []
    for cap in available_caps:
        keywords = task_keywords.get(cap, [cap.replace("_", " ")])
        if any(kw in q_lower for kw in keywords):
            matched_caps.append(cap)
    # Fallback: content_creation wenn nichts passt
    if not matched_caps:
        if "content_creation" in available_caps:
            matched_caps = ["content_creation"]
        else:
            matched_caps = [available_caps[0]]
    # Tasks aufbauen mit Abhängigkeiten
    prev_id = None
    for i, cap in enumerate(matched_caps):
        task_id = f"step_{i+1}_{cap}"
        template = q if prev_id is None else f"{q}\n\nVorheriges Ergebnis: {{{prev_id}}}"
        tasks.append({
            "task_id": task_id,
            "capability": cap,
            "input_template": template,
            "depends_on": [prev_id] if prev_id else [],
        })
        prev_id = task_id
    try:
        workflow_id = create_workflow(f"Chat-Workflow: {q[:50]}", tasks)
        start_workflow(workflow_id)
        cap_names = ", ".join(matched_caps)
        _post_chat("System", f"🔄 **Workflow gestartet** ({len(tasks)} Steps: {cap_names})\nID: `{workflow_id[:8]}...`")
        return {"status": "workflow_started", "workflow_id": workflow_id, "steps": len(tasks), "capabilities": matched_caps}
    except Exception as e:
        logging.getLogger(__name__).error("Workflow-Erstellung fehlgeschlagen: %s", e)
        return {"status": "error", "message": str(e)}
CMDS = {
    "status": lambda q: handle_status(),
    "job": handle_job,
    "free": handle_free,
    "queue": handle_queue,
    "git": handle_git,
    "project": lambda q: _handle_sys(q, "proj"),
    "bs": handle_bs,
    "resume": handle_resume,
    "approve_decision": handle_approve_decision,
    "reject_decision": handle_reject_decision,
    "bake": handle_bake,
    "emergency": handle_emergency,
    "notfall": handle_emergency,
    "diagnose": handle_diagnose,
    "confirmations": handle_confirmations,
    "spass": handle_spass,
    "worker": handle_worker,
    "workers": handle_worker,
    "blockade": handle_blockade,
    "blokade": handle_blockade,
    "workflow": handle_workflow,
    "help": handle_help,
    "hilfe": handle_help,
    "allclear000": handle_allclear,
}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    import logging
    import sqlite3
    _chat_log = logging.getLogger("gnom_hub.api.chat")

    def _db_fail(step: str, err: Exception):
        _chat_log.error("chat blocked at %s: %s", step, err)
        try:
            add_chat_message(
                get_active_project(),
                "System",
                "system",
                "chat",
                f"⚠️ **Chat-Pfad:** DB busy ({step}). Bitte erneut senden.",
                {"type": "chat", "sender": "System", "db_locked": True},
            )
        except Exception:
            pass
        return {
            "status": "error",
            "msg": f"Datenbank ausgelastet ({step}) — bitte in 1–2s erneut senden.",
            "error": str(err)[:120],
        }

    if msg.sender == "user":
        from gnom_hub.core.security.injection_validator import validate_input
        is_safe, reason = validate_input(msg.content)
        if not is_safe:
            proj = get_active_project()
            try:
                add_chat_message(proj, "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
                add_chat_message(
                    proj,
                    "SecurityAG",
                    "securityag",
                    "chat",
                    f"🚨 **Sicherheitswarnung:** Prompt-Injection-Muster erkannt und geblockt ({reason}).",
                    {"type": "chat", "sender": "SecurityAG", "security_threat": True}
                )
            except sqlite3.Error as e:
                return _db_fail("security_block", e)
            return {"status": "blocked", "msg": f"Prompt-Injection blockiert: {reason}", "message": reason}

    if msg.sender == "user" and "@merken" in msg.content.lower():
        import re
        import uuid

        from gnom_hub.db.soul_repo import save_soul_fact_smart

        try:
            add_chat_message(get_active_project(), "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
        except sqlite3.Error as e:
            return _db_fail("merken_save", e)

        cleaned_content = re.sub(r'(?i)\s*@merken\s*', ' ', msg.content).strip()
        if cleaned_content:
            fact_key = f"user_fact_{uuid.uuid4().hex[:8]}"
            try:
                save_soul_fact_smart(fact_key, f"[source:user] {cleaned_content}", agent="SoulAG", priority="high")
                add_chat_message(get_active_project(), "System", "soulag", "chat", f"💾 **Fakt gemerkt (hohe Priorität):** \"{cleaned_content}\"", {"type": "chat", "sender": "System"})
            except sqlite3.Error as e:
                return _db_fail("merken_fact", e)
            return {"status": "saved", "message": cleaned_content}
        else:
            add_chat_message(get_active_project(), "System", "soulag", "chat", "⚠️ **@merken:** Bitte gib einen Text ein, den ich mir merken soll.", {"type": "chat", "sender": "System"})
            return {"status": "error", "message": "Empty content"}

    try:
        soul_instance.on_message(msg.content, msg.sender)
    except Exception as e:
        _chat_log.warning("soul on_message non-fatal: %s", e)
    
    # Intercept simple approvals/rejections of pending decisions
    if msg.sender == "user":
        content_clean = msg.content.strip().lower().strip("!.?,")
        if content_clean in ("ja", "nein", "yes", "no", "allow", "block", "erlauben", "ablehnen"):
            from gnom_hub.db import get_state_value
            pending = get_state_value("pending_decisions", {})
            pending_items = [
                (dec_id, d) for dec_id, d in pending.items() 
                if d.get("status") == "pending"
            ]
            if pending_items:
                pending_items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
                decision_id, dec_info = pending_items[0]
                is_approve = content_clean in ("ja", "yes", "allow", "erlauben")
                if is_approve:
                    r = handle_approve_decision(decision_id)
                else:
                    r = handle_reject_decision(decision_id)
                add_chat_message(get_active_project(), "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
                return r

    q, tgt, cmd = _parse(msg.content); s_name = msg.sender if msg.sender != "user" else tgt
    try:
        ags = get_all_agents()
    except sqlite3.Error as e:
        return _db_fail("get_agents", e)
    next((x for x in ags if x.get("name", "").lower() == (s_name or "").lower()), None)
    # ZWC wird nur bei Datei-Writes und wichtigen Aktionen hinzugefuegt (action_write.py),
    # nicht bei jeder Chat-Nachricht — vermeidet 74% ZWC-Pollution
    # Layer-Enforcement: Agenten dürfen nicht in <SHOWBOX:user> schreiben
    from gnom_hub.core.security.showbox_validator import enforce_agent_layer
    msg.content = enforce_agent_layer(msg.content, msg.sender)
    # ARCHITEKTUR-FILTER: Agenten-Outputs mit <SHOWBOX>...</SHOWBOX> werden aus dem Chat entfernt
    # und als Showbox-Präsentation gespeichert. Chat bleibt sauber.
    import re as _re
    _SHOWBOX_RE = _re.compile(r'<SHOWBOX(?::([a-zA-Z0-9_\-]+))?>([\s\S]*?)<\/SHOWBOX>', _re.I)
    _SHOWBOX_TOOL_RE = _re.compile(r'\[SHOWBOX(?::([a-zA-Z0-9_\-]+))?\]([\s\S]*?)\[\/SHOWBOX\]', _re.I)
    # → Showbox / -> Showbox Format (User-Mandat 2026-06-28 — Worker-Pflicht)
    # Body = {...} JSON-Block OPTIONAL — ASCII-Box-Bodies (häufig ohne {}) müssen
    # trotzdem persistiert werden. Bug 2026-07-04: vorher verlangte die Regex
    # `]{...}` direkt nach `]` ohne Whitespace, ASCII-Boxes haben aber IMMER
    # Newlines nach dem Header → Match schlug fehl, Header blieb im Chat als
    # Plain-Text hängen. Fix: zweites Pattern _ARROW_SHOWBOX_PLAIN_RE für
    # header-only Showbox. Beide Patterns werden in der unten stehenden
    # Such-Reihenfolge durchprobiert. Wird vor <SHOWBOX>/[SHOWBOX] geprüft,
    # weil dieser Stil von allen 8 Agent-Prompts explizit verlangt wird.
    _ARROW_SHOWBOX_RE = _re.compile(
        r'\[\s*(?:→|->)\s*[Ss]howbox:\s*([^\]\n]{1,40})\]\s*\{([\s\S]*?)\}\s*$',
        _re.MULTILINE,
    )
    # Pattern B (Header-only / ASCII-Box): plain text nach Header. re.DOTALL
    # damit mehrzeilige ASCII-Box-Bodies korrekt erfasst werden.
    # Group(1): Name, Group(2): plain content (alles nach `]`)
    _ARROW_SHOWBOX_PLAIN_RE = _re.compile(
        r'\[\s*(?:→|->)\s*[Ss]howbox:\s*([^\]\n]{1,40})\]\s*(.*)',
        _re.DOTALL,
    )
    if msg.sender != "user":
        # Suche in dieser Reihenfolge: <SHOWBOX>, [SHOWBOX], [→ Showbox] (mit Body)
        # Beim ARROW-Format zuerst Body-Variante (mit {}) probieren, sonst
        # Plain-Variante (ASCII-Box oder Plain-Text nach Header).
        sbox_match = (
            _SHOWBOX_RE.search(msg.content)
            or _SHOWBOX_TOOL_RE.search(msg.content)
            or _ARROW_SHOWBOX_RE.search(msg.content)
            or _ARROW_SHOWBOX_PLAIN_RE.search(msg.content)
        )
        if sbox_match:
            try:
                import json as _json

                from gnom_hub.db import save_showbox_presentation, set_active_showbox
                arrow_plain = (sbox_match.re.pattern == _ARROW_SHOWBOX_PLAIN_RE.pattern)
                if arrow_plain:
                    # Pattern B: keine {} — Plain-Text nach Header
                    raw = (sbox_match.group(2) or "").strip()
                    pres_name = (sbox_match.group(1) or f"Agent {msg.sender}").strip()
                    if raw:
                        d = {"slides": [{"title": pres_name, "content": raw}]}
                    else:
                        # Header ohne Inhalt (Edge-Case) — als leere Slide speichern
                        d = {"slides": [{"title": pres_name, "content": "(leer)"}]}
                elif sbox_match.re.pattern == _ARROW_SHOWBOX_RE.pattern:
                    # Pattern A: {} Body direkt nach Header — like before
                    raw_payload = "{" + sbox_match.group(2) + "}"
                    raw = raw_payload
                    pres_name = (sbox_match.group(1) or f"Agent {msg.sender}").strip()
                    try:
                        d = _json.loads(raw)
                    except Exception:
                        d = {"slides": [raw]}
                else:
                    # Format <SHOWBOX> oder [SHOWBOX]
                    raw_payload = sbox_match.group(2).strip()
                    raw = raw_payload
                    pres_name = (sbox_match.group(1) or f"Agent {msg.sender}").strip()
                    try:
                        d = _json.loads(raw)
                    except Exception:
                        d = {"slides": [raw]}
                slides = d.get("slides", [raw]) if isinstance(d, dict) else [raw]

                # Button-Extraktion aus <button action="..." label="...">...</button> HTML-Tags.
                # Nutzt den geteilten Parser — gleiche Logik wie action_exec.py +
                # showbox-module.js, damit nichts driftet.
                from gnom_hub.frontend.showbox_button_parser import parse_inline_buttons
                extracted_btns = parse_inline_buttons(raw)
                json_btns = d.get("buttons") if isinstance(d, dict) else None
                if json_btns:
                    final_btns = json_btns[:8]
                elif extracted_btns:
                    final_btns = extracted_btns[:8]
                else:
                    final_btns = None

                save_showbox_presentation(pres_name, slides, sender=msg.sender, buttons=final_btns)
                set_active_showbox(pres_name)
                # Chat-Inhalt ohne SHOWBOX-Tag speichern — alle Formate ersetzen
                msg.content = _SHOWBOX_RE.sub(f'[→ Showbox: {pres_name}]', msg.content).strip()
                msg.content = _SHOWBOX_TOOL_RE.sub(f'[→ Showbox: {pres_name}]', msg.content).strip()
                msg.content = _ARROW_SHOWBOX_RE.sub(f'[→ Showbox: {pres_name}]', msg.content).strip()
                # Plain-Variante: ersten Header + Body ersetzen durch Showbox-Tag.
                # Plain-Inhalt bleibt im Showbox-Body (nicht im Chat — User sieht Tag + Showbox-Tabelle).
                if arrow_plain:
                    first_match = _ARROW_SHOWBOX_PLAIN_RE.search(msg.content)
                    if first_match:
                        msg.content = (
                            msg.content[:first_match.start()]
                            + f'[→ Showbox: {pres_name}]'
                            + msg.content[first_match.end():]
                        ).strip()
                    else:
                        msg.content = f'[→ Showbox: {pres_name}]'
            except Exception:
                pass
    try:
        add_chat_message(
            get_active_project(), msg.sender, "war-room", cmd or "chat", msg.content,
            {"type": cmd or "chat", "sender": msg.sender},
        )
    except sqlite3.Error as e:
        return _db_fail("save_message", e)

    if msg.sender != "user":
        return {"status": "saved"}
    if cmd in CMDS:
        try:
            return CMDS[cmd](q)
        except sqlite3.OperationalError as e:
            return _db_fail(f"cmd_{cmd}", e)

    def _notify_dispatch_fail(reason: str) -> None:
        """Prio-1: leerer Dispatch darf nicht still bleiben."""
        try:
            add_chat_message(
                get_active_project(),
                "System",
                "system",
                "chat",
                f"⚠️ **Dispatch fehlgeschlagen:** {reason}",
                {"type": "chat", "sender": "System", "dispatch_failed": True},
            )
        except Exception:
            pass

    def _safe_dispatch(*args, **kwargs):
        try:
            return dispatch(*args, **kwargs)
        except sqlite3.OperationalError as e:
            _chat_log.error("dispatch locked: %s", e)
            return None  # signal failure without raising

    _SYS = ("soulag", "generalag", "watchdogag")
    if cmd == "research":
        asked = []
        for n in [x["name"] for x in ags if x.get("status") == "online" and x["name"].lower() not in _SYS]:
            r = _safe_dispatch(q, target=n, sender=msg.sender)
            if r is None:
                return _db_fail("dispatch_research", RuntimeError("database is locked"))
            if r:
                asked.append(n)
        if not asked:
            online = [x["name"] for x in ags if x.get("status") in ("online", "busy", "running")]
            _notify_dispatch_fail(
                "Kein Worker online für Research. "
                f"Online: {', '.join(online) if online else '(keine)'} — Hub/Agents prüfen."
            )
        return {"status": "dispatched" if asked else "error", "asked": asked, "target": None, "mode": "research"}
    if not cmd and not tgt:
        # User-Chat ohne @target: Default-Routing an GeneralAG (Dirigent).
        generalag = next((x for x in ags if x["name"].lower() == "generalag"), None)
        asked: list[str] = []
        if generalag and generalag.get("status") in ("online", "busy", "running"):
            r = _safe_dispatch(msg.content, target="generalag", sender=msg.sender)
            if r is None:
                # Message is already in chat; user can retry dispatch
                return {
                    "status": "saved",
                    "asked": [],
                    "target": "generalag",
                    "mode": "chat",
                    "msg": "Nachricht gespeichert, Dispatch wartet (DB busy) — Agent holt sie ggf. nach Reconnect.",
                }
            if r:
                asked.append("GeneralAG")
        if not asked:
            if generalag is None:
                _notify_dispatch_fail(
                    "GeneralAG fehlt in der Agenten-DB. Hub neu starten oder Agents seeden."
                )
            else:
                st = generalag.get("status") or "unknown"
                _notify_dispatch_fail(
                    f"GeneralAG ist nicht erreichbar (status=`{st}`). "
                    "Agent-Prozess prüfen (`./start_gnom_hub.sh` / Logs unter logs/)."
                )
        return {
            "status": "dispatched" if asked else "error",
            "asked": asked,
            "target": "generalag",
            "mode": "chat",
        }
    asked = _safe_dispatch(q, target=tgt, sender=msg.sender)
    if asked is None:
        return {
            "status": "saved",
            "asked": [],
            "target": tgt,
            "mode": "brainstorm" if cmd == "bs" else "chat",
            "msg": "Nachricht gespeichert, Dispatch wartet (DB busy).",
        }
    if not asked and tgt:
        _notify_dispatch_fail(
            f"@{tgt} ist offline, unbekannt oder Queue voll. "
            "Online-Agents prüfen oder mit `@GeneralAG …` neu versuchen."
        )
    return {
        "status": "dispatched" if asked else "error",
        "asked": asked,
        "target": tgt,
        "mode": "brainstorm" if cmd == "bs" else "chat",
    }
@router.get("/api/chat")
def get_chat(limit: int = 50):
    rm = get_chat_history(get_active_project(), limit)
    for m in rm:
        if "content" in m: m["content"] = sanitize_showboxes(m["content"])
    return rm


@router.get("/api/chat/stream")
def stream_chat(limit: int = 30, after: str = ""):
    """SSE stream of chat updates (Phase-0 prototype).

    Clients may raise poll interval; events fire when the newest message
    id/timestamp changes. Heartbeat every ~15s keeps proxies alive.
    """
    import json
    import time as _time

    from fastapi.responses import StreamingResponse

    def _event_gen():
        last_sig = after or ""
        idle = 0
        while True:
            try:
                msgs = get_chat_history(get_active_project(), limit)
                for m in msgs:
                    if "content" in m:
                        m["content"] = sanitize_showboxes(m["content"])
                # signature: newest first in get_chat_history
                top = msgs[0] if msgs else {}
                sig = f"{top.get('id', '')}|{top.get('timestamp', '')}|{len(msgs)}"
                if sig != last_sig:
                    last_sig = sig
                    idle = 0
                    payload = json.dumps({"messages": msgs, "sig": sig})
                    yield f"event: chat\ndata: {payload}\n\n"
                else:
                    idle += 1
                    if idle >= 5:
                        idle = 0
                        yield f"event: ping\ndata: {_time.time()}\n\n"
            except Exception as ex:
                yield f"event: error\ndata: {json.dumps({'error': str(ex)[:120]})}\n\n"
            _time.sleep(3.0)

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
