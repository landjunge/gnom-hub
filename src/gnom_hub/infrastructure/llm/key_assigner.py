from gnom_hub.infrastructure.database.state_repo import SQLiteStateRepository
from gnom_hub.infrastructure.database.agent_repo import SQLiteAgentRepository

async def auto_assign_keys():
    mappings = {}
    agents = SQLiteAgentRepository().get_all()
    for a in agents:
        role = a.role or "normal"
        name = a.name.lower()
        if role == "coder" or "coder" in name or name in ("watchdogag", "securityag"):
            p, m = "auto", "stage_4"
        else:
            p, m = "auto", "stage_3"
        mappings[a.name.lower()] = {"provider": p, "model": m}
    SQLiteStateRepository().set_value("llm_agents", mappings)
