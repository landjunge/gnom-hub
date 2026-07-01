"""Role Tools — distribute_job (General)."""
from gnom_hub.db import get_all_agents


def _llm(sys_prompt, user_prompt, max_tokens=None):
    from gnom_hub.infrastructure.router.router import ask_router
    return str(ask_router(user_prompt, sys_prompt))
def distribute_job(job_text):
    ags = get_all_agents()
    gen = next((a for a in ags if a.get("role") == "general"), None)
    if not gen: gen = next((a for a in ags if a.get("name","").lower() == "generalag"), None)
    if not gen: return "Kein GeneralAG gefunden."
    from gnom_hub.soul import get_soul
    soul = get_soul(gen.get("name", "GeneralAG"))
    mmap = ", ".join(f"{a['name']}:{a.get('skill', a.get('role','Agent'))}" for a in ags if a.get('name').lower() not in {"soulag", "generalag", "securityag", "watchdogag"})
    system = (f"SYSTEM: Du bist {gen.get('name', 'GeneralAG')}. {soul.get('directive')}\nDeine Truppe: [{mmap}]. "
        "Analysiere die Aufgabe kurz, warne falls nötig vor Regelverstößen, "
        "erinnere an Git-Commits und weise Teilaufgaben im Format '@AgentName -> Aufgabe' zu (jede auf neuer Zeile).")
    return _llm(system, job_text, 500)
