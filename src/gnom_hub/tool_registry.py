"""Tool-Registry: Soul-basierte Tool-Zuweisung mit Beschreibungen."""

def get_tools_for_agent(soul: dict):
    """Vergibt Tools + kurze Beschreibungen basierend auf der Soul."""
    permissions = soul.get("permissions", [])
    tool_map = {
        "read_file": "Dateien lesen",
        "write_file": "Dateien schreiben oder ändern",
        "run_command": "Terminal-Befehle ausführen",
        "war_room_chat": "Mit anderen Agents im War Room sprechen",
        "create_agent": "Neue Agents erstellen",
        "screenshot": "Bildschirmfoto machen",
        "desktop_action": "Maus & Tastatur steuern",
        "evolve": "Eigenen Code verbessern",
        "generate_image": "Bild generieren mit [IMAGE: prompt]",
        "crawl_url": "URL-Inhalte extrahieren"
    }
    available = ["read_file"]
    if "@job" in permissions or "general" in permissions:
        available += ["war_room_chat", "create_agent"]
    if "write" in permissions:
        available += ["write_file", "generate_image"]
    if "godmode" in permissions or "run" in permissions:
        available += ["run_command"]
    if "crawl" in permissions:
        available += ["crawl_url"]
    if "desktop" in permissions:
        available += ["screenshot", "desktop_action"]
    if "evolve" in permissions:
        available += ["evolve"]
    return {t: tool_map.get(t, t) for t in available}

def format_tools_prompt(soul: dict, agent_name: str):
    """Baut den Tool-Block für den System-Prompt."""
    tools = get_tools_for_agent(soul)
    if not tools:
        return f"Du bist {agent_name}. Keine Tools – nur Diskussion."
    lines = [f"- {name}: {desc}" for name, desc in tools.items()]
    role = soul.get("role", "Agent")
    syntax = "\nCommand-Syntax:"
    syntax += "\n  [READ: dateiname] — Datei lesen"
    if "write_file" in tools:
        syntax += "\n  [WRITE: dateiname]inhalt[/WRITE] — Datei schreiben"
    if "run_command" in tools:
        syntax += "\n  [SHELL: befehl] — Terminal-Befehl ausführen"
    if "generate_image" in tools:
        syntax += "\n  [IMAGE: bildprompt] — Bild generieren"
    return f"Du bist {agent_name} ({role}).\nVerfügbare Tools:\n" + "\n".join(lines) + syntax
