from .soul import soul_instance

SOULS = {
    k: {
        "role": v["role"],
        "permissions": v["de"]["permissions"],
        "character": v["de"]["character"],
        "directive": v["de"]["directive"]
    }
    for k, v in soul_instance.get_definitions().items()
}

def get_soul(agent_name: str) -> dict:
    return SOULS.get(agent_name.lower(), {"role": "default", "permissions": ["read"], "directive": "Hilf dem Schwarm."})
