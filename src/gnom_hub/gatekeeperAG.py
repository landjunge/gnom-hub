from .db import get_db
from .chat_commands import _post_chat
from .brainstorm import dispatch
from .provider_switchAG import llm_call

def intercept(msg: str):
    """Route normal chat messages directly to GeneralAG.
    Only use gatekeeper LLM for very short/ambiguous inputs."""
    # Very short or single-word messages → ask for clarification
    words = msg.strip().split()
    if len(words) <= 2 and not any(c in msg for c in '?!.'):
        from .zwc_soul import strip_zwc
        from .db import get_active_project
        mem = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
        ctx = "\n".join([f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])}" for m in mem[-4:]])
        from .db import get_language
        lang = get_language()
        if lang == "en":
            sys = """You are the Gatekeeper. Analyze the user input in context.
If the request is vague or unclear, return ONLY 2-3 numbered questions/options to choose from.
If the request is CLEAR OR the user responded with a number, summarize the final goal concretely and start exactly with: 'CLEAR: <summary>'"""
        else:
            sys = """Du bist der Gatekeeper. Analysiere die Usereingabe im Kontext.
Wenn die Anfrage schwammig oder unklar ist, gib NUR 2-3 nummerierte Fragen/Optionen zur Auswahl zurück.
Wenn die Anfrage KLAR ist ODER der User mit einer Nummer geantwortet hat, fasse das endgültige Ziel konkret zusammen und beginne zwingend mit: 'KLAR: <Zusammenfassung>'"""
        res = llm_call(f"Kontext:\n{ctx}\n\nUser: {msg}", sys, 1500).strip()
        if not (res.startswith("KLAR:") or res.startswith("CLEAR:")):
            _post_chat("Gatekeeper", res)
            return {"status": "intercepted"}
        msg = res.replace("KLAR:", "").replace("CLEAR:", "").strip()
    # Clear message → dispatch directly to GeneralAG
    dispatch(msg, target="GeneralAG")
    return {"status": "dispatched", "asked": ["GeneralAG"], "target": "GeneralAG", "mode": "chat"}
