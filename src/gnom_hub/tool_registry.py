def get_tools_for_agent(soul: dict):
    if soul.get("role") == "general":
        return {}
    p, tm = soul.get("permissions", []), {
        "read_file": "Read files (also outside workspace with godmode)",
        "write_file": "Write files",
        "run_command": "Execute terminal commands (including pip install, brew, etc.)",
        "war_room_chat": "Chat", "create_agent": "Create agents",
        "screenshot": "Screenshot", "desktop_action": "Mouse & Keyboard",
        "evolve": "Improve code", "generate_image": "Generate image",
        "crawl_url": "Crawl URL", "browser": "Real browser control (Playwright)",
        "sys_cmd": "System commands (install programs, change settings)"
    }
    a = ["read_file"]
    if "@job" in p: a += ["war_room_chat", "create_agent"]
    if "write" in p: a += ["write_file", "generate_image"]
    if "godmode" in p or "run" in p: a += ["run_command", "sys_cmd"]
    if "godmode" in p: a += ["browser"]
    if "crawl" in p: a += ["crawl_url"]
    if "desktop" in p: a += ["screenshot", "desktop_action", "browser"]
    if "evolve" in p: a += ["evolve"]
    return {t: tm.get(t, t) for t in dict.fromkeys(a)}

def format_tools_prompt(soul: dict, name: str):
    t = get_tools_for_agent(soul)
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand Syntax:"
    if "read_file" in t: syn += "\n  [READ: filename] — Read file (godmode: any absolute path)"
    if "write_file" in t: syn += "\n  [WRITE: filename]content[/WRITE] — Write file"
    if "run_command" in t: syn += "\n  [SHELL: command] — Terminal (pip install, brew, system commands)"
    if "generate_image" in t: syn += "\n  [IMAGE: prompt] — Generate image"
    if "browser" in t: syn += '\n  [BROWSER: {"action": "goto|click|type|read|screenshot", "target": "...", "value": "..."}]'
    syn += '\n  <SHOWBOX:lamp_index>["Slide 1 HTML", "Slide 2 HTML"]</SHOWBOX> — Showbox update.'
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"You are {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"): intro += f"\n[PERSONALITY] {soul['directive']}"
    return intro + "\nAvailable Tools:\n" + "\n".join(lines) + syn
