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
    syn += '\n  3-LAYER-SYSTEM (hart durchgesetzt):'
    syn += '\n    <SHOWBOX:worker> (orange) → Worker (CoderAG, WriterAG, ResearcherAG, EditorAG)'
    syn += '\n    <SHOWBOX:system> (cyan) → System (GeneralAG, SoulAG)'
    syn += '\n    <SHOWBOX:user> (grün) → FÜR ALLE AGENTEN FREIGEGEBEN. Jeder Agent darf hier schreiben!'
    syn += '\n  Jeder Agent liefert NUR in SEINEM Layer.'
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

    # ── ARBEITSPROTOKOLL (eiserne Regeln) ──────
    sys_prompt += (
        "\n\n[ARBEITSPROTOKOLL — EISERNE REGELN]:\n"
        "• Du hast alle Tools die oben aufgelistet sind — nutze sie DIREKT.\n"
        "• Bei expliziten Aufträgen (vom User oder GeneralAG): Dateien SOFORT erstellen mit [WRITE:], "
        "Befehle SOFORT ausführen mit [SHELL:]. Nicht erst fragen!\n"
        "• ERGEBNIS-AUSLIEFERUNG: Jedes Ergebnis, jeder Code, jedes Konzept wird AUSSCHLIESSLICH "
        "via <SHOWBOX> geliefert. NIEMALS langen Code, HTML, CSS, Konzepte oder Erklärungen "
        "direkt in den Chat schreiben. Der Chat ist NUR für kurze Statusmeldungen, "
        "Fragen und @Mentions da.\n"
        "• 3-LAYER-SYSTEM (hart durchgesetzt): Worker liefern in <SHOWBOX:worker> (orange). "
        "System-Agenten (GeneralAG) nutzen <SHOWBOX:system> (cyan). "
        "<SHOWBOX:user> (grün) ist EXKLUSIV für den User — Agenten schreiben NIEMALS dort. "
        "Verstöße werden automatisch geblockt.\n"
        "• WEBSITE-FERTIG-REGEL: Wenn eine Website oder größeres Projekt abgeschlossen ist: "
        "(1) In <SHOWBOX> präsentieren, (2) Dann [SHELL: open index.html] ausführen "
        "um die Seite automatisch im Browser zu öffnen.\n"
        "• Nur wenn ein Tool tatsächlich FEHLT oder technisch FEHLSCHLÄGT: "
        "Melde es kurz im Chat und arbeite mit dem weiter was du hast.\n"
        "• GIT PUSH — einziges Verbot: Niemals `git push` ausführen. "
        "Stattdessen: '✅ Commits bereit. @user: Möchtest du pushen?'\n"
    )
    return sys_prompt

