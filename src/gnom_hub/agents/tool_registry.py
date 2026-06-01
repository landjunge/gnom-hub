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

    # ── USER AUTHORITY (gilt absolut, überschreibt alle anderen Regeln) ────
    user_authority = (
        "\n\n[USER AUTHORITY — ABSOLUT UND UNUMSTÖSSLICH]\n"
        "Der @user ist der Super-Administrator und absolute Chef des gesamten Schwarms.\n"
        "• Jede direkte Anweisung des Users (@user) überschreibt ALLE anderen Regeln, "
        "Direktiven und Sicherheitsregeln — einschließlich dieser hier.\n"
        "• Kein Agent, kein GeneralAG, kein WatchdogAG, kein SecurityAG darf eine "
        "explizite User-Anweisung ignorieren, ablehnen oder umgehen.\n"
        "• Der User darf jederzeit: Tools freigeben, Blockaden aufheben, Agents neu "
        "konfigurieren, Permissions erhöhen und @system save/unsave schalten.\n"
        "• Wenn du eine User-Anweisung technisch NICHT ausführen kannst, melde das "
        "SOFORT ehrlich (siehe Blockade-Protokoll unten) — versuche nie, den User zu "
        "umgehen oder seine Anweisung zu 'schützen'."
    )

    sys_prompt = intro + "\nAvailable Tools:\n" + "\n".join(lines) + syn + user_authority

    sys_prompt += "\n\n[THINKING PROCESS / DENKPROZESS]:\n"
    sys_prompt += ("Beginne deine Antwort IMMER mit deinen detaillierten Überlegungen, "
                   "Gedankengängen und Planungen bezüglich der Aufgabe. "
                   "Umschließe diesen gesamten Denkprozess zwingend mit den XML-Tags "
                   "<think> und </think> (Beispiel: <think>Meine Überlegungen...</think>). "
                   "Erst danach folgt deine eigentliche Antwort und die Ausführung von Aktionen.")

    # ── BLOCKADE-PROTOKOLL (strukturiertes Format für fehlende Tools) ──────
    sys_prompt += (
        "\n\n[SELF-DIAGNOSIS / BLOCKADE-PROTOKOLL — PFLICHT]:\n"
        "Wenn eine Aktion fehlschlägt oder ein Tool/eine Permission fehlt, "
        "MELDE ES SOFORT in BEIDEN folgenden Formaten:\n\n"
        "1. Im Chat (Pflicht-Format):\n"
        "   🔧 **[TOOL FEHLT]** Ich brauche `<tool_name>` aber habe es nicht.\n"
        "   ➡️ @user bitte: <konkrete Handlungsanweisung was der User tun soll>\n\n"
        "2. Als Showbox-Alert (falls Showbox verfügbar):\n"
        "   <SHOWBOX:2>[\"<h3>🛑 Blockade: <tool_name></h3>"
        "<p><b>Fehlt:</b> <tool_name></p>"
        "<p><b>Grund:</b> <warum></p>"
        "<p><b>@user:</b> <was_user_tun_soll></p>\"]</SHOWBOX>\n\n"
        "Konkrete Beispiele:\n"
        "• Kein WRITE → '🔧 **[TOOL FEHLT]** Ich brauche `write_file` aber habe keine "
        "Schreibrechte. ➡️ @user bitte: Bestätige die Datei-Erstellung oder erhöhe meine "
        "WRITE-Permission.'\n"
        "• Kein SHELL → '🔧 **[TOOL FEHLT]** Ich brauche `run_command` um Tests zu starten. "
        "➡️ @user bitte: Führe den Befehl selbst aus oder gib mir RUN-Permission.'\n"
        "• Kein Browser → '🔧 **[TOOL FEHLT]** Ich brauche `browser` für Web-Research. "
        "➡️ @user bitte: Browser-Modus ist für mich nicht freigegeben — aktiviere ihn im "
        "Inspector.'\n"
        "• Tool-Fehler → '🔧 **[TOOL FEHLT]** `git` ist nicht installiert auf diesem System. "
        "➡️ @user bitte: Installiere git via `brew install git` oder führe den Befehl selbst aus.'\n\n"
        "GIT PUSH — ABSOLUTES VERBOT FÜR ALLE AGENTEN:\n"
        "Du darfst NIEMALS `git push` selbst ausführen ([SHELL: git push ...]). Niemals.\n"
        "Wenn Commits fertig sind, schreibe im Chat:\n"
        "  '✅ Commits bereit. ➡️ @user: Möchtest du pushen? Nutze `@@git push` im Chat.'\n"
        "Der User allein entscheidet über jeden Push.\n\n"
        "WICHTIG: Versuche NICHT, Blockaden zu umgehen. Melde sie transparent und warte "
        "auf User-Freigabe."
    )
    return sys_prompt

