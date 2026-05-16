"""Role Tools — distribute_job (General) und summarize_chat (Summarizer)."""
from .db import get_db, save_db
from .provider_switchAG import llm_call as _llm
def distribute_job(job_text):
    ags = get_db("agents")
    gen = next((a for a in ags if a.get("role") == "general"), {})
    gen_desc = gen.get("description", "Du bist der elitäre General.")
    mmap = ", ".join(f"{a['name']}:{a.get('skill', a.get('role','Agent'))}" for a in ags if a.get('name') != gen.get('name'))
    system = (f"SYSTEM: {gen_desc} Deine Truppe: [{mmap}]. "
        "Analysiere den Job in 1 Satz. Erstelle max 3 Teilaufgaben. "
        "Ausgabe NUR im Format: @Name → Aufgabe. Keine Erklärungen.")
    return _llm(system, job_text, 300)
def summarize_chat(limit=50):
    from .zwc_soul import decode_soul, strip_zwc
    chat = sorted(get_db("memory"), key=lambda x: x.get("timestamp", ""))[-limit:]
    lines = []; souls = {}
    for m in chat:
        if m.get("agent_id") == "war-room":
            c = m["content"]; s = decode_soul(c)
            if s and "name" in s: souls[s["name"]] = s
            lines.append(f"[{m.get('metadata',{}).get('sender','?')}] {strip_zwc(c)[:200]}")
    system = ("SYSTEM: Du bist der Summarizer. Extrahiere NUR wichtige Punkte. "
        "IGNORIERE: Grüße, Smalltalk. Max 8 Stichpunkte. NUR die Stichpunkte.")
    if souls: system += f"\nSchwarm-Bewusstsein: {list(souls.values())}"
    return _llm(system, "\n".join(lines[-30:]), 600)
