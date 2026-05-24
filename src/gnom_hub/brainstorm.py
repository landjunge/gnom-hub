import threading; from .db import get_db; from .brainstorm_helpers import ask_llm, get_ctx
from .zwc_soul import strip_zwc
def _run_phase(ags, q, ctx, bs=False):
    ts = []
    for a in ags:
        t = threading.Thread(target=ask_llm, args=(a, q, ctx, bs), daemon=True); t.start(); ts.append(t)
    for t in ts: t.join(timeout=200)
def _collect_worker_responses(worker_names):
    msgs = sorted([m for m in get_db("memory") if m.get("agent_id") == "war-room"], key=lambda x: x.get("timestamp", ""))
    out = []
    for n in worker_names:
        resp = next((m for m in reversed(msgs) if m.get("metadata", {}).get("sender", "").lower() == n.lower()), None)
        if resp: out.append(f"[{n}] {strip_zwc(resp['content'])[:800]}")
    return "\n\n".join(out)
def dispatch(q, target=None):
    ao = [a for a in get_db("agents") if a.get("status") == "online"]
    if target:
        s = [a for a in ao if a["name"].lower() == target.lower()]
        for a in s: threading.Thread(target=ask_llm, args=(a, q, get_ctx(), False), daemon=True).start()
        return [a["name"] for a in s]
    w = [a for a in ao if a["name"].lower() not in ("soulag", "generalag", "securityag", "watchdogag")]
    g = [a for a in ao if a["name"] == "GeneralAG"]
    wn = [a["name"] for a in w]
    print(f"[BS] Phase 1: Worker ({wn})"); _run_phase(w, q, get_ctx(), True)
    if g:
        synthesis_ctx = f"FRAGE: {q}\n\nWORKER-ANTWORTEN:\n{_collect_worker_responses(wn)}"
        print(f"[BS] Phase 2: Synthese"); _run_phase(g, q, synthesis_ctx, True)
    return [a["name"] for a in w + g]

