def get_tools_for_agent(soul: dict):
    # GeneralAG: schlankes Orchestrator-Set (Prio-5) — KEIN leeres Toolset mehr.
    # Vorher: role==general → {} → LLM ohne Tool-Syntax → oft stille/leere Antworten.
    if soul.get("role") == "general":
        return {
            "read_file": "Read workspace files for context before delegating. [READ: path]",
            "offload_recall": "Recall offloaded tool output. [OFFLOAD_RECALL:<node_id>]",
            "showbox": "Status/Ergebnis-Slides. [→ Showbox: name]{...} oder <SHOWBOX:system>…",
            "delegate": "Worker anstoßen via @Mention (siehe DELEGATION-Syntax).",
        }
    p, tm = soul.get("permissions", []), {
        "read_file": "Read files (also outside workspace with godmode)",
        "write_file": "Write files",
        "run_command": "Execute terminal commands (including pip install, brew, etc.)",
        "war_room_chat": "Chat", "create_agent": "Create agents",
        "screenshot": "Screenshot", "desktop_action": "Mouse & Keyboard",
        "evolve": "Improve code", "generate_image": "Generate image",
        "crawl_url": "Crawl URL (fetch a webpage and extract text). [CRAWL: https://example.com]",
        "web_search": "Search the web (Brave Search API). [WEBSEARCH: query]. ALLE Agenten dürfen das IMMER — Dauerhaft freigeschaltet.",
        "browser": "Real browser automation via Playwright. Write a Python script that uses the Playwright sync API. The script runs in a sandboxed subprocess (cwd=workspace, no shell, no host network by default). Output is captured and returned to you. Use this for: opening pages, clicking elements, filling forms, scraping, taking screenshots, running JS in-page. NOT for: bulk file ops, system commands, anything outside a browser context.",
        "sys_cmd": "System commands (install programs, change settings)",
        # ── Video-Tools (macOS screencapture + ffmpeg fallback) ──
        "screen_record": "Record the screen with optional TTS audio (macOS screencapture + say). [VIDEO:SCREEN:filename=out.mov|duration=20|tts=Spoken text via say]",
        "video_merge": "Merge/concatenate multiple video files. [VIDEO:MERGE:input1.mov,input2.mp4|output=final.mp4]",
        "video_edit": "Cut, trim, or scale a video. [VIDEO:EDIT:input.mov|output=cut.mp4|start=00:00:05|end=00:00:15]",
        # ── Context-Offload-Tool (TencentDB-Port) ─────────────────────
        # Erlaubt Agenten einen ausgelagerten Tool-Output per node_id
        # zurück in den Kontext zu holen. Verfügbar für ALLE Agenten —
        # ein Agent soll jederzeit nachschlagen können, was ein
        # vergangenes Tool-Output war.
        "offload_recall": "Recall an offloaded tool output by node_id. [OFFLOAD_RECALL:<8-hex-chars>]. Use this when the OFFLOAD-CANVAS in the system prompt shows a node you want to expand.",
        # ── TTS (plattformunabhängig) ──
        "speak":        "Speak text using the agent's assigned TTS voice (macOS say / Linux espeak / Windows SAPI). [SPEAK: text here]. SoulAG nutzt das für direkte Sprachausgabe an User.",
        "set_voice":    "Change the agent's default TTS voice. [SET_VOICE: Anna|rate=180]. Available voices depend on platform.",
        "list_voices":  "List all available TTS voices on this system. [LIST_VOICES]",
    }
    # ── DAUERHAFT FREIGESCHALTET für ALLE Agenten ──
    a = ["read_file", "web_search", "crawl_url", "offload_recall"]
    if "@job" in p: a += ["war_room_chat", "create_agent"]
    if "write" in p: a += ["write_file", "generate_image"]
    if "godmode" in p or "run" in p: a += ["run_command", "sys_cmd", "screen_record", "video_merge", "video_edit"]
    if "godmode" in p: a += ["browser"]
    # Standalone 'browser'-Token gewährt Playwright-Browser ohne godmode/desktop.
    # Vorher gab es diesen Token als Permission-Eintrag, aber tool_registry hat
    # ihn nie anerkannt → Inkonsistenz. ResearcherAG profitiert davon.
    if "browser" in p: a += ["browser"]
    if "desktop" in p: a += ["screenshot", "desktop_action", "browser", "screen_record"]
    if "evolve" in p: a += ["evolve"]  
    return {t: tm.get(t, t) for t in dict.fromkeys(a)}


def _generalag_tools_prompt(soul: dict, name: str) -> str:
    """Orchestrator-Prompt: Tools + harte User-Sichtbarkeit (Prio-5)."""
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"You are {name} ({soul.get('role', 'general')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSONALITY] {soul['directive']}"
    tools = get_tools_for_agent(soul)
    lines = [f"- {n}: {d}" for n, d in tools.items()]
    body = (
        intro
        + "\nAvailable Tools:\n"
        + "\n".join(lines)
        + "\n\n[DELEGATION — EXAKTE SYNTAX]"
        "\n  Eine Zeile pro Worker (bevorzugt):"
        "\n    @CoderAG -> implementiere X in pfad/y.py"
        "\n    @WriterAG -> schreibe kurze Doku zu X"
        "\n    @ResearcherAG -> recherchiere Y mit Quellen"
        "\n    @EditorAG -> review Datei Z"
        "\n  Auch erlaubt: `@CoderAG implementiere X` (ohne Pfeil)."
        "\n  NUR diese 4 Worker. NIEMALS @SoulAG/@SecurityAG/@WatchdogAG/@GeneralAG."
        "\n  Mehrere Worker: eine Zeile je Agent (Sequenzen warten aufeinander)."
        "\n\n[USER-SICHTBARKEIT — PFLICHT]"
        "\n  Du bist der Default-Chat-Empfänger. Der User muss IMMER etwas sehen:"
        "\n  1. Kurze Chat-Antwort (1–5 Sätze) NACH </think> — Status, Plan oder Antwort."
        "\n  2. Bei Delegation: im Chat nennen, WEN du beauftragst und WARUM."
        "\n  3. Einfache Fragen (Erklärung, Ja/Nein, Status): SELBST antworten, ohne Worker."
        "\n  4. Showbox optional für strukturierte Deliverables:"
        "\n     [→ Showbox: plan]{\"slides\":[{\"title\":\"…\",\"content\":\"…\",\"buttons\":[{\"label\":\"OK\",\"action\":\"close\"}]}]}"
        "\n  5. Nie nur <think>…</think> und dann nichts. Nie leere Showbox ohne Chat-Text."
        "\n\n[Command Syntax]"
        "\n  [READ: path] — Kontext lesen"
        "\n  [OFFLOAD_RECALL:node_id] — Offload-Detail"
        "\n  [→ Showbox: name]{json} — Präsentation"
        "\n  <SHOWBOX:system>…</SHOWBOX> — System-Layer"
        "\n\n[USER AUTHORITY]"
        "\n  User-Anweisungen haben absolute Priorität. Wenn du etwas nicht kannst: ehrlich im Chat sagen."
        "\n\n[THINKING]"
        "\n  Optional <think>…</think> für Planung, aber die sichtbare Antwort danach ist Pflicht."
    )
    return body


def format_tools_prompt(soul: dict, name: str):
    if soul.get("role") == "general" or (name or "").lower() in ("generalag", "general"):
        return _generalag_tools_prompt(soul, name)

    t = get_tools_for_agent(soul)
    lines = [f"- {n}: {d}" for n, d in t.items()]
    syn = "\nCommand Syntax:"
    if "read_file" in t: syn += "\n  [READ: filename] — Read file (godmode: any absolute path)"
    if "write_file" in t: syn += "\n  [WRITE: filename]content[/WRITE] — Write file"
    if "run_command" in t: syn += "\n  [SHELL: command] — Terminal (pip install, brew, system commands)"
    if "generate_image" in t: syn += "\n  [IMAGE: prompt] — Generate image"
    if "browser" in t: syn += (
        '\n  [BROWSER: <python_code>] — Playwright sync-API script. Runs in subprocess, captured stdout/stderr returned.'
        '\n    Body MUST be a self-contained Python script. Use `print()` to emit results. Screenshots write to the workspace cwd.'
        '\n    Minimal example:'
        '\n      [BROWSER:]'
        '\n      from playwright.sync_api import sync_playwright'
        '\n      with sync_playwright() as p:'
        '\n          b = p.chromium.launch(headless=True)'
        '\n          page = b.new_page()'
        '\n          page.goto("https://example.com")'
        '\n          print("title:", page.title())'
        '\n          b.close()'
        '\n      [/BROWSER]'
        '\n    Common patterns: page.goto(url) | page.click(selector) | page.fill(selector, text) | page.locator(sel).text_content() | page.screenshot(path="x.png") | page.evaluate("() => ...").'
        '\n    Sandbox limits: no os.system/subprocess/eval/exec; only playwright + stdlib. 120s timeout.'
    )
    if "web_search" in t: syn += "\n  [WEBSEARCH: query] — Web search (Brave API). DAUERHAFT für alle Agenten freigeschaltet."
    if "crawl_url" in t: syn += "\n  [CRAWL: https://example.com] — Fetch and extract text from URL. DAUERHAFT."
    if "screen_record" in t: syn += "\n  [VIDEO:SCREEN:filename=out.mov|duration=20|audio=on] — Record screen (macOS screencapture, ffmpeg fallback)"
    if "video_merge" in t: syn += "\n  [VIDEO:MERGE:input1.mov,input2.mp4|output=final.mp4] — Concatenate videos (ffmpeg)"
    if "video_edit" in t: syn += "\n  [VIDEO:EDIT:input.mov|output=cut.mp4|start=00:00:05|end=00:00:15|scale=1280x720] — Cut/trim/scale (ffmpeg)"
    if "offload_recall" in t: syn += "\n  [OFFLOAD_RECALL:<8-hex-chars>] — Volltext eines ausgelagerten Tool-Outputs zurückholen (node_id aus OFFLOAD-CANVAS)."
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
    )
    return sys_prompt

