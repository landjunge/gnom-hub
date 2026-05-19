"""Brainstorm Dispatcher — 3-Phasen-Pipeline."""
import threading
from .db import get_db
from .brainstorm_helpers import ask_llm, get_ctx, get_workspace_dir, post

def _run_phase(agents, question, ctx, bs_mode=False):
    """Feuert Agenten parallel und wartet bis alle fertig sind."""
    threads = []
    for a in agents:
        t = threading.Thread(target=ask_llm, args=(a, question, ctx, bs_mode), daemon=True)
        t.start(); threads.append(t)
    for t in threads: t.join(timeout=200)

def dispatch(question, target=None):
    """3-Phasen-Pipeline: Worker → Summarizer → General."""
    exclude = ["BackupAG"]
    all_online = [a for a in get_db("agents") if a.get("status") == "online" and a.get("name") not in exclude]

    # Einzelauftrag: Direkt feuern, WRITE erlaubt
    if target:
        single = [a for a in get_db("agents") if a.get("status") == "online" and a["name"].lower() == target.lower()]
        ctx = get_ctx()
        for a in single:
            threading.Thread(target=ask_llm, args=(a, question, ctx, False), daemon=True).start()
        return [a["name"] for a in single]

    # @bs Pipeline in 3 Phasen (WRITE blockiert!)
    workers = [a for a in all_online if a["name"] not in ("SummarizerAG", "GeneralAG")]
    summarizer = [a for a in all_online if a["name"] == "SummarizerAG"]
    general = [a for a in all_online if a["name"] == "GeneralAG"]

    print(f"[BS] Phase 1: Worker ({[a['name'] for a in workers]})")
    _run_phase(workers, question, get_ctx(), bs_mode=True)

    if summarizer:
        print(f"[BS] Phase 2: Summarizer")
        _run_phase(summarizer, question, get_ctx(), bs_mode=True)

    if general:
        print(f"[BS] Phase 3: General entscheidet")
        _run_phase(general, question, get_ctx(), bs_mode=True)

    return [a["name"] for a in workers + summarizer + general]
