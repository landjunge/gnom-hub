"""Role Tools — distribute_job (General) und summarize_chat (Summarizer)."""
import os, requests
from .db import get_db

DS_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_URL = "https://api.deepseek.com/chat/completions"

def _llm(system, user, tokens=500):
    if not DS_KEY: return "[Kein DEEPSEEK_API_KEY]"
    try:
        r = requests.post(DS_URL, headers={"Authorization": f"Bearer {DS_KEY}"},
            json={"model": "deepseek-chat", "messages": [{"role": "system", "content": system},
                  {"role": "user", "content": user}], "max_tokens": tokens}, timeout=60)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e: return f"[Fehler: {str(e)[:80]}]"

def distribute_job(job_text):
    agents = [a["name"] for a in get_db("agents")]
    system = (f"SYSTEM: Du bist der General. Existierende Agenten: {', '.join(agents)}. "
        "Analysiere den Job in 1 Satz. Erstelle max 3 Teilaufgaben. "
        "Ausgabe NUR im Format: @Name → Aufgabe. NICHTS ANDERES. Keine Erklärungen.")
    return _llm(system, job_text, 300)

def summarize_chat(limit=50):
    chat = sorted(get_db("memory"), key=lambda x: x.get("timestamp", ""))[-limit:]
    lines = [f"[{m.get('metadata',{}).get('sender','?')}] {m['content'][:200]}" for m in chat
             if m.get("agent_id") == "war-room"]
    system = ("SYSTEM: Du bist der Summarizer. Extrahiere NUR wichtige Punkte, Entscheidungen, Ideen. "
        "IGNORIERE: Grüße, Witze, Smalltalk, Wiederholungen. Max 8 Stichpunkte, 1 Satz pro Punkt. "
        "Keine Einleitung, kein Fazit. NUR die Stichpunkte.")
    return _llm(system, "\n".join(lines[-30:]), 600)
