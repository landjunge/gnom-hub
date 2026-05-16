from .db import get_db
from .chat_commands import _post_chat
from .brainstorm import dispatch
from .provider_switchAG import llm_call

def intercept(msg: str):
    from .zwc_soul import strip_zwc
    from .db import get_active_project
    mem = [m for m in get_db("memory") if m.get("agent_id") == "war-room" and m.get("project", "default") == get_active_project()]
    ctx = "\n".join([f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(m['content'])}" for m in mem[-4:]])
    sys = """Du bist der Gatekeeper. Analysiere die Usereingabe im Kontext.
Wenn die Anfrage schwammig oder unklar ist, gib NUR 2-3 nummerierte Fragen/Optionen zur Auswahl zurück.
Wenn die Anfrage KLAR ist ODER der User mit einer Nummer geantwortet hat, fasse das endgültige Ziel konkret zusammen und beginne zwingend mit: 'KLAR: <Zusammenfassung>'"""
    res = llm_call(f"Kontext:\n{ctx}\n\nUser: {msg}", sys, 1500).strip()
    if res.startswith("KLAR:"):
        q = res.replace("KLAR:", "").strip()
        _post_chat("System", f"Aufgabe verstanden: {q}\nLeite an Schwarm weiter...")
        dispatch(q, target=None)
    else:
        _post_chat("Gatekeeper", res)
    return {"status": "intercepted"}
