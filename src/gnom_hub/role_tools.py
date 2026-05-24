"""Role Tools — distribute_job (General)."""
from .db import get_db, save_db
def _llm(sys_prompt, user_prompt, max_tokens=None):
    from .router import ask_router
    return ask_router(user_prompt, sys_prompt)
def distribute_job(job_text):
    ags = get_db("agents")
    gen = next((a for a in ags if a.get("role") == "general"), None)
    if not gen: gen = next((a for a in ags if a.get("name","").lower() == "generalag"), None)
    from .soul_initializer import get_soul
    soul = get_soul(gen.get("name", "GeneralAG"))
    mmap = ", ".join(f"{a['name']}:{a.get('skill', a.get('role','Agent'))}" for a in ags if a.get('name') != gen.get('name'))
    system = (f"SYSTEM: Du bist {gen.get('name', 'GeneralAG')}. {soul.get('directive')}\nDeine Truppe: [{mmap}]. "
        "Analysiere die Aufgabe kurz, warne falls nötig vor Regelverstößen (40-Zeilen-Limit, Komplexität), "
        "erinnere an Git-Commits und weise Teilaufgaben im Format '@AgentName -> Aufgabe' zu (jede auf neuer Zeile).")
    return _llm(system, job_text, 500)
