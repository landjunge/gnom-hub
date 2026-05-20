def get_tools_for_agent(soul: dict):
    p, tm = soul.get("permissions", []), {
        "read_file": "Read files (also outside workspace with godmode)",
        "write_file": "Write files",
        "run_command": "Execute terminal commands (including pip install, brew, etc.)",
        "war_room_chat": "Chat",
        "create_agent": "Create agents",
        "screenshot": "Screenshot",
        "desktop_action": "Mouse & Keyboard",
        "evolve": "Improve code",
        "generate_image": "Generate image",
        "crawl_url": "Crawl URL",
        "deploy": "Deploy frontend (@publish)",
        "browser": "Real browser control (Playwright)",
        "sys_cmd": "System commands (install programs, change settings)"
    }
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
    if not t: return f"You are {name}. No tools – discussion only."
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand Syntax:\n  [READ: filename] — Read file (godmode: any absolute path)"
    if "write_file" in t: syn += "\n  [WRITE: filename]content[/WRITE] — Write file"
    if "run_command" in t: syn += "\n  [SHELL: command] — Terminal (pip install, brew, system commands)"
    if "generate_image" in t: syn += "\n  [IMAGE: prompt] — Generate image"
    if "deploy" in t: syn += "\n  @publish — Deploy frontend to network"
    if "browser" in t: syn += '\n  [BROWSER: {"action": "goto|click|type|read|screenshot", "target": "...", "value": "..."}]'
    syn += '\n  <SHOWBOX:lamp_index>["Slide 1 HTML", "Slide 2 HTML"]</SHOWBOX> — Updates the Showbox slides for lamp lamp_index (1-7) and displays them in the Showbox center. Use modern inline CSS (gradients, glassmorphism, flex).'
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"You are {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSONALITY] {soul['directive']}"
    return intro + "\nAvailable Tools:\n" + "\n".join(lines) + syn
