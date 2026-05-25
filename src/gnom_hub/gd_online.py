# gd_online.py
from gnom_hub.monitoring import get_agent_metrics

def is_online(mgr, agent: str) -> bool:
    clean_name = agent.split("(")[0].strip().lower()
    if clean_name in mgr.simulated_failures:
        return False
    metrics = get_agent_metrics()
    agent_data = metrics.get(clean_name)
    if agent_data:
        return agent_data.get("status") == "online"
    return clean_name in ["generalag", "soulag"]
