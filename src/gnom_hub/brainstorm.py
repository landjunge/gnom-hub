"""Brainstorm Dispatcher — Hub fragt LLM im Namen der Agenten."""
import os, re, requests, threading, uuid
from datetime import datetime
from dotenv import load_dotenv
from .db import get_db, save_db
from .router import ask_router
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
BASE_WORKSPACE = "/Users/landjunge/Documents/AG-Flega/gnom_workspace"

def get_workspace_dir():
    from .db import get_active_project
    d = os.path.join(BASE_WORKSPACE, get_active_project())
    os.makedirs(d, exist_ok=True)
    return d

def _post(sender, content):
    from .db import get_active_project
    entry = {"id": str(uuid.uuid4()), "agent_id": "war-room", "project": get_active_project(), "content": content,
             "metadata": {"type": "brainstorm", "status": "open", "sender": sender},
             "timestamp": datetime.utcnow().isoformat() + "Z"}
    save_db("memory", get_db("memory") + [entry])

def _ask_llm(agent, question, context, bs_mode=False):
    desc = agent.get("description", "")
    role_mem = [m for m in get_db("memory") if m.get("agent_id") == agent.get("id") and m.get("type") == "role"]
    sys_prompt = role_mem[-1]["content"].replace("[SYSTEM-ROLLE] ", "") if role_mem else f"Du bist {agent['name']} ({desc}), ein KI-Agent im Gnom-Hub."
    
    wd = get_workspace_dir()
    files_str = ""
    if os.path.exists(wd): files_str = ", ".join(os.listdir(wd))
    
    sys_prompt += f"\n\n[WORKSPACE: {wd} | Vorhandene Dateien: {files_str}]"
    from .zwc_soul import decode_soul
    from .tool_registry import format_tools_prompt
    from .soul_initializer import get_soul
    role_text = role_mem[-1]["content"] if role_mem else ""
    soul = get_soul(agent["name"]) or decode_soul(role_text) or {"role": desc, "permissions": ["read"]}
    sys_prompt += f"\n{format_tools_prompt(soul, agent['name'])}"
    if bs_mode:
        sys_prompt += "\n[MODUS: BRAINSTORM — Nur diskutieren! KEIN [WRITE:] erlaubt. Dateien werden nur auf Einzelauftrag (@AgentName) geschrieben.]"
    
    user_msg = question
    if context: user_msg += f"\n\nBisherige Diskussion:\n{context}"
    try:
        answer = ask_router(user_msg, sys_prompt, agent_name=agent.get("name", ""))
        if not answer or not isinstance(answer, str):
            _post(agent["name"], f"[Fehler: Keine Antwort vom LLM für {agent['name']}]")
            return
        perms = soul.get("permissions", [])
        from .action_handlers import process_actions
        answer = process_actions(answer, agent, perms, bs_mode, wd)
        _post(agent["name"], answer)
    except Exception as e: _post(agent["name"], f"[Fehler: {str(e)[:80]}]")

def _get_ctx():
    """Holt die letzten 8 Chat-Nachrichten als Kontext."""
    from .db import get_active_project
    from .zwc_soul import strip_zwc
    chat = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
    return "\n".join(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])[:1000]}"
                    for m in sorted(chat, key=lambda x: x.get("timestamp",""))[-8:])

def _run_phase(agents, question, ctx, bs_mode=False):
    """Feuert Agenten parallel und wartet bis alle fertig sind."""
    threads = []
    for a in agents:
        t = threading.Thread(target=_ask_llm, args=(a, question, ctx, bs_mode), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=200)

def dispatch(question, target=None):
    """3-Phasen-Pipeline: Worker diskutieren → Summarizer fasst zusammen → General entscheidet."""
    exclude = ["BackupAG"]
    all_online = [a for a in get_db("agents") if a.get("status") == "online" and a.get("name") not in exclude]

    # Einzelauftrag: Direkt feuern, keine Pipeline, WRITE erlaubt (mit Backup)
    if target:
        single = [a for a in get_db("agents") if a.get("status") == "online" and a["name"].lower() == target.lower()]
        ctx = _get_ctx()
        for a in single:
            threading.Thread(target=_ask_llm, args=(a, question, ctx, False), daemon=True).start()
        return [a["name"] for a in single]

    # @bs Pipeline in 3 Phasen (WRITE blockiert!)
    workers = [a for a in all_online if a["name"] not in ("SummarizerAG", "GeneralAG")]
    summarizer = [a for a in all_online if a["name"] == "SummarizerAG"]
    general = [a for a in all_online if a["name"] == "GeneralAG"]

    # Phase 1: Worker diskutieren parallel
    print(f"[BS] Phase 1: Worker ({[a['name'] for a in workers]})")
    _run_phase(workers, question, _get_ctx(), bs_mode=True)

    # Phase 2: Summarizer liest Diskussion, fasst zusammen
    if summarizer:
        print(f"[BS] Phase 2: Summarizer")
        _run_phase(summarizer, question, _get_ctx(), bs_mode=True)

    # Phase 3: General liest alles (inkl. Summary), verteilt Jobs
    if general:
        print(f"[BS] Phase 3: General entscheidet")
        _run_phase(general, question, _get_ctx(), bs_mode=True)

    return [a["name"] for a in workers + summarizer + general]
