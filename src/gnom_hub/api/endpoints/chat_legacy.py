from fastapi import APIRouter; from pydantic import BaseModel
from gnom_hub.db import get_all_agents, get_active_project, add_chat_message, get_chat_history
from gnom_hub.chat.brainstorm.brainstorm import dispatch; from gnom_hub.soul import soul_instance
from gnom_hub.core.security.showbox_validator import sanitize_showboxes; from .chat_helpers import _parse, _handle_sys
from gnom_hub.chat.chat_commands import handle_status, handle_job, handle_free, handle_git, handle_resume, handle_approve_decision, handle_reject_decision, handle_bake, handle_emergency, handle_diagnose, handle_confirmations, handle_spass, handle_blockade, handle_help, handle_allclear
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
    from gnom_hub.db.connection import get_db_connection
    from gnom_hub.chat.chat_commands import _post_chat
    q = q.strip()
    if not q:
        return {"status": "error", "message": "Bitte gib eine Aufgabe an: @@workflow <Aufgabe>"}
    # Capabilities aus der DB laden
    conn = get_db_connection()
    caps = conn.execute('SELECT DISTINCT capability FROM agent_capabilities').fetchall()
    conn.close()
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
CMDS = {"status": lambda q: handle_status(), "job": handle_job, "free": handle_free, "git": handle_git, "project": lambda q: _handle_sys(q, "proj"), "bs": handle_bs, "resume": handle_resume, "approve_decision": handle_approve_decision, "reject_decision": handle_reject_decision, "bake": handle_bake, "emergency": handle_emergency, "notfall": handle_emergency, "diagnose": handle_diagnose, "confirmations": handle_confirmations, "spass": handle_spass, "worker": handle_worker, "workers": handle_worker, "blockade": handle_blockade, "blokade": handle_blockade, "workflow": handle_workflow, "help": handle_help, "hilfe": handle_help, "allclear000": handle_allclear}
@router.post("/api/chat")
def post_chat(msg: ChatMsg):
    if msg.sender == "user":
        from gnom_hub.core.security.injection_validator import validate_input
        is_safe, reason = validate_input(msg.content)
        if not is_safe:
            proj = get_active_project()
            add_chat_message(proj, "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})
            add_chat_message(
                proj,
                "SecurityAG",
                "securityag",
                "chat",
                f"🚨 **Sicherheitswarnung:** Prompt-Injection-Muster erkannt und geblockt ({reason}).",
                {"type": "chat", "sender": "SecurityAG", "security_threat": True}
            )
            return {"status": "blocked", "msg": f"Prompt-Injection blockiert: {reason}", "message": reason}

    if msg.sender == "user" and "@merken" in msg.content.lower():
        import re, uuid
        from gnom_hub.db.soul_repo import save_soul_fact_smart

        add_chat_message(get_active_project(), "user", "war-room", "chat", msg.content, {"type": "chat", "sender": "user"})

        cleaned_content = re.sub(r'(?i)\s*@merken\s*', ' ', msg.content).strip()
        if cleaned_content:
            fact_key = f"user_fact_{uuid.uuid4().hex[:8]}"
            save_soul_fact_smart(fact_key, f"[source:user] {cleaned_content}", agent="SoulAG", priority="high")
            add_chat_message(get_active_project(), "System", "soulag", "chat", f"💾 **Fakt gemerkt (hohe Priorität):** \"{cleaned_content}\"", {"type": "chat", "sender": "System"})
            return {"status": "saved", "message": cleaned_content}
        else:
            add_chat_message(get_active_project(), "System", "soulag", "chat", "⚠️ **@merken:** Bitte gib einen Text ein, den ich mir merken soll.", {"type": "chat", "sender": "System"})
            return {"status": "error", "message": "Empty content"}

    soul_instance.on_message(msg.content, msg.sender)
    
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

    q, tgt, cmd = _parse(msg.content); s_name = msg.sender if msg.sender != "user" else tgt; ags = get_all_agents()
    a = next((x for x in ags if x.get("name", "").lower() == (s_name or "").lower()), None)
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
    if msg.sender != "user":
        sbox_match = _SHOWBOX_RE.search(msg.content) or _SHOWBOX_TOOL_RE.search(msg.content)
        if sbox_match:
            try:
                import json as _json
                from gnom_hub.db import save_showbox_presentation, set_active_showbox
                raw = sbox_match.group(2).strip()
                try:
                    d = _json.loads(raw)
                except Exception:
                    d = {"slides": [raw]}
                slides = d.get("slides", [raw]) if isinstance(d, dict) else [raw]
                pres_name = (sbox_match.group(1) or f"Agent {msg.sender}").strip()

                # Button-Extraktion aus <button action="...">...</button> HTML-Tags
                _BTN_RE = _re.compile(r'<button\s+action=["\']([^"\']+)["\'][^>]*>([^<]*)</button>', _re.I)
                extracted_btns = []
                for bm in _BTN_RE.finditer(raw):
                    action = bm.group(1).strip()
                    label = bm.group(2).strip() or (action.split(':')[0] if ':' in action else 'OK')
                    extracted_btns.append({
                        'id': f'btn-{len(extracted_btns)+1}',
                        'onClick': action,
                        'label': label[:30],
                        'icon': '▶'
                    })
                json_btns = d.get("buttons") if isinstance(d, dict) else None
                if json_btns:
                    final_btns = json_btns[:8]
                elif extracted_btns:
                    final_btns = extracted_btns[:8]
                else:
                    final_btns = None

                save_showbox_presentation(pres_name, slides, sender=msg.sender, buttons=final_btns)
                set_active_showbox(pres_name)
                # Chat-Inhalt ohne SHOWBOX-Tag speichern
                msg.content = _SHOWBOX_RE.sub(f'[→ Showbox: {pres_name}]', msg.content).strip()
                msg.content = _SHOWBOX_TOOL_RE.sub(f'[→ Showbox: {pres_name}]', msg.content).strip()
            except Exception:
                pass
    add_chat_message(get_active_project(), msg.sender, "war-room", cmd or "chat", msg.content, {"type": cmd or "chat", "sender": msg.sender})
    if msg.sender != "user": return {"status": "saved"}
    if cmd in CMDS: return CMDS[cmd](q)
    _SYS = ("soulag", "generalag", "watchdogag")
    if cmd == "research":
        asked = [n for n in [x["name"] for x in ags if x.get("status") == "online" and x["name"].lower() not in _SYS] if dispatch(q, target=n, sender=msg.sender)]
        return {"status": "dispatched", "asked": asked, "target": None, "mode": "research"}
    if not cmd and not tgt:
        # User-Chat ohne @target: geht an GeneralAG (Dirigent).
        # GeneralAG delegiert an Worker. SoulAG ist stiller Beobachter + DB.
        # User-Mandat 2026-06-28 04:33.
        dispatch(msg.content, target="GeneralAG", sender=msg.sender)
        return {"status": "dispatched", "asked": ["GeneralAG"], "target": "GeneralAG", "mode": "chat"}
    return {"status": "dispatched", "asked": dispatch(q, target=tgt, sender=msg.sender), "target": tgt, "mode": "brainstorm" if cmd == "bs" else "chat"}
@router.get("/api/chat")
def get_chat(limit: int = 50):
    rm = get_chat_history(get_active_project(), limit)
    for m in rm:
        if "content" in m: m["content"] = sanitize_showboxes(m["content"])
    return rm
