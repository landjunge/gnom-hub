"""Role Prompt Implanter — speichert System-Prompt in der state-Tabelle."""
from gnom_hub.db import set_state_value, get_state_value


def implant(agent_name, prompt):
    """Speichert den System-Prompt direkt in der state-Tabelle (keine .md-Dateien mehr)."""
    key = f"agent_role_prompt_{agent_name.lower()}"
    existing = get_state_value(key, "")
    set_state_value(key, prompt)
    return f"db:{key}"
