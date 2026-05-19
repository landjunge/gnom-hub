def get_tools_for_agent(soul: dict):
    p, tm = soul.get("permissions", []), {"read_file": "Dateien lesen", "write_file": "Dateien schreiben", "run_command": "Terminal-Befehle ausführen", "war_room_chat": "Chat", "create_agent": "Agenten erstellen", "screenshot": "Screenshot", "desktop_action": "Maus & Tastatur", "evolve": "Code verbessern", "generate_image": "Bild generieren", "crawl_url": "URL crawlen"}
    a = ["read_file"]
    if "@job" in p or "general" in p: a += ["war_room_chat", "create_agent"]
    if "write" in p: a += ["write_file", "generate_image"]
    if "godmode" in p or "run" in p: a += ["run_command"]
    if "crawl" in p: a += ["crawl_url"]
    if "desktop" in p: a += ["screenshot", "desktop_action"]
    if "evolve" in p: a += ["evolve"]
    return {t: tm.get(t, t) for t in a}
def format_tools_prompt(soul: dict, name: str):
    t = get_tools_for_agent(soul)
    if not t: return f"Du bist {name}. Keine Tools – nur Diskussion."
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand-Syntax:\n  [READ: dateiname] — Datei lesen"
    if "write_file" in t: syn += "\n  [WRITE: dateiname]inhalt[/WRITE] — Datei schreiben"
    if "run_command" in t: syn += "\n  [SHELL: befehl] — Terminal ausführen"
    if "generate_image" in t: syn += "\n  [IMAGE: prompt] — Bild generieren"
    syn += "\n  [SHOWBOX: {\"title\": \"Titel\", \"content\": \"HTML\"}] — Showbox anzeigen"
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"Du bist {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSÖNLICHKEIT] {soul['directive']}"
    return intro + "\nVerfügbare Tools:\n" + "\n".join(lines) + syn
