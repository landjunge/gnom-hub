import threading
import time

from gnom_hub.chat.brainstorm.brainstorm_helpers import ask_llm
from gnom_hub.soul.zwc_soul import strip_zwc


def _run_phase(ags, q, ctx, bs=False):
    ts = []
    for a in ags:
        t = threading.Thread(target=ask_llm, args=(a, q, ctx, bs), daemon=True)
        t.start()
        ts.append(t)
        if len(ags) > 1:
            time.sleep(1.5)
    [t.join(timeout=200) for t in ts]
def _collect_worker_responses(worker_names):
    from gnom_hub.db import get_chat_history, get_active_project; msgs = get_chat_history(get_active_project(), limit=50)
    out = []
    for n in worker_names:
        resp = next((m for m in msgs if m.get("sender", "").lower() == n.lower()), None)
        if resp: out.append(f"[{n}] {strip_zwc(resp['content'])[:800]}")
    return "\n\n".join(out)
def dispatch(q, target=None, depth=0, sender="GeneralAG", context_id=None):
    from gnom_hub.db import get_all_agents; ao = [a for a in get_all_agents() if a.get("status") in ("online", "busy", "running")]
    if target:
        t_low = target.lower()
        sys_names = {"soulag", "generalag", "securityag", "watchdogag"}
        if t_low == "worker":
            s = [a for a in ao if a["name"].lower() not in sys_names]
        elif t_low == "system":
            s = [a for a in ao if a["name"].lower() in sys_names]
        elif t_low == "all":
            s = ao
        else:
            s = [a for a in ao if a["name"].lower() == t_low]
        from gnom_hub.agents.swarm.swarm_comms import dispatch_mention
        from gnom_hub.core.config import DB_PATH
        from gnom_hub.db import get_active_project
        proj = context_id or get_active_project() or "default"
        # Targeted dispatch: only agents in ``s`` — do NOT expand nested @Worker
        # mentions inside the plan text (SUPERVISOR-R6 fanout bug: user→GeneralAG
        # with @CoderAG/@WriterAG in body was queueing every worker as user→).
        asked: list[str] = []
        for a in s:
            got = dispatch_mention(
                sender,
                f"@{a['name']} {q}",
                proj,
                str(DB_PATH),
                depth,
                only=[a["name"]],
            )
            asked.extend(got)
        return asked
    # @bs Brainstorming: NUR GeneralAG analysiert und delegiert
    g = [a for a in ao if a["name"] == "GeneralAG"]
    if g:
        bs_instruction = (
            f"[BRAINSTORM-AUFTRAG]\n"
            f"Der User hat eine Brainstorming-Anfrage gestellt.\n"
            f"AUFGABE: {q}\n\n"
            f"DEINE ROLLE: Du bist GeneralAG, der alleinige Koordinator.\n"
            f"1. Analysiere die Aufgabe.\n"
            f"2. Zerlege sie in Teilaufgaben und weise sie den passenden Worker-Agenten zu.\n"
            f"   Verwende das Format: @CoderAG -> konkrete Aufgabe (pro Zeile ein Agent).\n"
            f"3. Warte auf die Ergebnisse der Worker.\n"
            f"4. Fasse die Worker-Ergebnisse zusammen und präsentiere sie in <SHOWBOX:1>.\n\n"
            f"WICHTIG: Du selbst erstellst KEINE Slides, Konzepte oder Inhalte. "
            f"Du koordinierst und fasst NUR zusammen. "
            f"Die Worker-Agenten werden erst aktiv, wenn du ihnen eine Aufgabe zuweist."
        )
        _run_phase(g, q, bs_instruction, True)
        return [a["name"] for a in g]
    return []
