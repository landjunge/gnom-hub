def get_tools_for_agent(soul: dict):
    return {
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
        "browser": "Real browser control (Playwright)",
        "sys_cmd": "System commands (install programs, change settings)"
    }

def format_tools_prompt(soul: dict, name: str):
    t = get_tools_for_agent(soul)
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand Syntax:\n  [READ: filename] — Read file (godmode: any absolute path)"
    syn += "\n  [WRITE: filename]content[/WRITE] — Write file"
    syn += "\n  [SHELL: command] — Terminal (pip install, brew, system commands)"
    syn += "\n  [IMAGE: prompt] — Generate image"
    syn += '\n  [BROWSER: {"action": "goto|click|type|read|screenshot", "target": "...", "value": "..."}]'
    syn += '\n  <SHOWBOX:lamp_index>["Slide 1 HTML", "Slide 2 HTML"]</SHOWBOX> — Updates the Showbox slides for lamp lamp_index (1-7) and displays them in the Showbox center. Use modern inline CSS (gradients, glassmorphism, flex).'
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"You are {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSONALITY] {soul['directive']}"
    return intro + "\nAvailable Tools:\n" + "\n".join(lines) + syn
