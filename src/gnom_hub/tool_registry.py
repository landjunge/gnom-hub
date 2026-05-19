def get_tools_for_agent(soul: dict):
    p, tm = soul.get("permissions", []), {"read_file": "Dateien lesen (auch außerhalb Workspace mit godmode)", "write_file": "Dateien schreiben", "run_command": "Terminal-Befehle ausführen (inkl. pip install, brew, etc.)", "war_room_chat": "Chat", "create_agent": "Agenten erstellen", "screenshot": "Screenshot", "desktop_action": "Maus & Tastatur", "evolve": "Code verbessern", "generate_image": "Bild generieren", "crawl_url": "URL crawlen", "deploy": "Frontend deployen (@publish)", "browser": "Echte Browser-Steuerung (Playwright)", "sys_cmd": "System-Befehle (Programme installieren, Einstellungen)"}
    a = ["read_file"]
    if "@job" in p or "general" in p: a += ["war_room_chat", "create_agent"]
    if "write" in p: a += ["write_file", "generate_image"]
    if "godmode" in p or "run" in p: a += ["run_command", "sys_cmd"]
    if "godmode" in p: a += ["browser"]
    if "crawl" in p: a += ["crawl_url"]
    if "desktop" in p: a += ["screenshot", "desktop_action", "browser"]
    if "evolve" in p: a += ["evolve"]
    if "deploy" in p: a += ["deploy"]
    return {t: tm.get(t, t) for t in dict.fromkeys(a)}
def format_tools_prompt(soul: dict, name: str):
    t = get_tools_for_agent(soul)
    if not t: return f"Du bist {name}. Keine Tools – nur Diskussion."
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand-Syntax:\n  [READ: dateiname] — Datei lesen (godmode: beliebiger Pfad)"
    if "write_file" in t: syn += "\n  [WRITE: dateiname]inhalt[/WRITE] — Datei schreiben"
    if "run_command" in t: syn += "\n  [SHELL: befehl] — Terminal (pip install, brew, system-befehle)"
    if "generate_image" in t: syn += "\n  [IMAGE: prompt] — Bild generieren"
    if "deploy" in t: syn += "\n  @publish — Frontend auf netzwerkpunkt.de deployen"
    if "browser" in t: syn += '\n  [BROWSER: {"action": "goto|click|type|read|screenshot", "target": "...", "value": "..."}]'
    syn += '\n  [SHOWBOX: {"title": "Titel", "content": "HTML"}] — Showbox anzeigen'
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"Du bist {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSÖNLICHKEIT] {soul['directive']}"
    return intro + "\nVerfügbare Tools:\n" + "\n".join(lines) + syn
