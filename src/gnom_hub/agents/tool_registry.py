def get_tools_for_agent(soul: dict):
    """Map soul.permissions → tool dict.

    Tools are advertised ONLY when the matching permission token is present
    (or godmode). Previously crawl_url/web_search were always injected for
    every non-general agent while action handlers still required ``crawl`` /
    ``web_search`` tokens — agents saw tools they could not use (R5 audit).
    """
    # GeneralAG: schlankes Orchestrator-Set (Prio-5) — KEIN leeres Toolset mehr.
    # Vorher: role==general → {} → LLM ohne Tool-Syntax → oft stille/leere Antworten.
    if soul.get("role") == "general":
        return {
            "read_file": "Read workspace files for context before delegating. [READ: path]",
            "offload_recall": "Recall offloaded tool output. [OFFLOAD_RECALL:<node_id>]",
            "showbox": "Status/Ergebnis-Slides. [→ Showbox: name]{...} oder <SHOWBOX:system>…",
            "delegate": "Worker anstoßen via @Mention (siehe DELEGATION-Syntax).",
            "verify": "Definition-of-Done file check. [VERIFY: path|must_contain=X|min_bytes=N]",
        }
    p = list(soul.get("permissions", []) or [])
    has = set(p)
    god = "godmode" in has

    tm = {
        "read_file": "Read files (also outside workspace with godmode)",
        "write_file": "Write files",
        "run_command": "Execute terminal commands (including pip install, brew, etc.)",
        "war_room_chat": "Chat",
        "create_agent": "Create agents",
        "screenshot": "Screenshot",
        "desktop_action": "Mouse & Keyboard",
        "evolve": "Improve code",
        "generate_image": "Generate image",
        "crawl_url": "Crawl URL (fetch a webpage and extract text). [CRAWL: https://example.com]",
        "web_search": "Search the web (Brave Search API). [WEBSEARCH: query].",
        "browser": (
            "Real browser automation via Playwright. Write a Python script that uses the "
            "Playwright sync API. The script runs in a sandboxed subprocess (cwd=workspace). "
            "Use for: pages, clicks, forms, scrape, screenshots. NOT bulk file ops / shell."
        ),
        "sys_cmd": "System commands (install programs, change settings)",
        "screen_record": (
            "Record the screen with optional TTS audio (macOS screencapture + say). "
            "[VIDEO:SCREEN:filename=out.mov|duration=20|tts=Spoken text via say]"
        ),
        "video_merge": (
            "Merge/concatenate multiple video files. "
            "[VIDEO:MERGE:input1.mov,input2.mp4|output=final.mp4]"
        ),
        "video_edit": (
            "Cut, trim, or scale a video. "
            "[VIDEO:EDIT:input.mov|output=cut.mp4|start=00:00:05|end=00:00:15]"
        ),
        "offload_recall": (
            "Recall an offloaded tool output by node_id. [OFFLOAD_RECALL:<8-hex-chars>]. "
            "Use when OFFLOAD-CANVAS shows a node you want to expand."
        ),
        "speak": (
            "Speak text using the agent's assigned TTS voice. [SPEAK: text here]."
        ),
        "set_voice": (
            "Change the agent's default TTS voice. [SET_VOICE: Anna|rate=180]."
        ),
        "list_voices": "List all available TTS voices on this system. [LIST_VOICES]",
    }

    # Base: every agent may read workspace + recall offloads
    a: list[str] = []
    if "read" in has or god:
        a.append("read_file")
    a.append("offload_recall")

    if "@job" in has or god:
        a += ["war_room_chat", "create_agent"]

    if "write" in has or god:
        a += ["write_file"]
    if "write" in has or "image" in has or god:
        a += ["generate_image"]

    # shell / run / code (legacy aliases)
    if "run" in has or "shell" in has or "code" in has or god:
        a += ["run_command", "sys_cmd"]

    if "run" in has or "video" in has or god:
        a += ["screen_record", "video_merge", "video_edit"]

    if "crawl" in has or god:
        a += ["crawl_url"]

    if "web_search" in has or god:
        a += ["web_search"]

    # browser: explicit token OR godmode (SecurityAG). Not auto via desktop alone.
    if "browser" in has or god:
        a += ["browser"]

    if "desktop" in has or god:
        a += ["screenshot", "desktop_action", "browser", "screen_record"]

    if "evolve" in has or god:
        a += ["evolve"]

    if "audio" in has or god:
        a += ["speak", "set_voice", "list_voices"]

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
        "\n  [VERIFY: path|path2|must_contain=X|min_bytes=N] — DoD-Check (nur lesen)"
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
    if "read_file" in t:
        syn += "\n  [READ: filename] — Read file (godmode: any absolute path)"
    if "write_file" in t:
        syn += "\n  [WRITE: filename]content[/WRITE] — Write file"
    if "write_file" in t or "read_file" in t:
        syn += (
            "\n  [SCREENSHOT: path.html | out=shots/x.png] — Full-page PNG via Playwright (needs write)."
            "\n  [VERIFY: path1|path2|must_contain=Gnom-Hub|min_bytes=500] — Definition-of-Done file check."
        )
    if "run_command" in t:
        syn += "\n  [SHELL: command] — Terminal (pip install, brew, system commands)"
    if "generate_image" in t:
        syn += "\n  [IMAGE: prompt] — Generate image"
    if "browser" in t:
        syn += (
            "\n  [BROWSER:]python_script[/BROWSER] — Playwright sync-API (real tool)."
            "\n  Short form (auto-expanded): [browser: https://example.com]"
            "\n  NOT a tool: prose like 'Browser via Whitelist öffnen' does NOTHING."
            "\n    Minimal example:"
            "\n      [BROWSER:]"
            "\n      from playwright.sync_api import sync_playwright"
            "\n      with sync_playwright() as p:"
            "\n          b = p.chromium.launch(headless=True)"
            "\n          page = b.new_page()"
            '\n          page.goto("https://example.com")'
            '\n          print("title:", page.title())'
            "\n          b.close()"
            "\n      [/BROWSER]"
            "\n    Common patterns: page.goto(url) | page.click(selector) | page.fill(selector, text) "
            '| page.locator(sel).text_content() | page.screenshot(path="x.png") | page.evaluate("() => ...").'
            "\n    Sandbox limits: no os.system/subprocess/eval/exec; only playwright + stdlib. 120s timeout."
        )
    if "web_search" in t:
        syn += "\n  [WEBSEARCH: query] — Web search (Brave API)."
    if "crawl_url" in t:
        syn += "\n  [CRAWL: https://example.com] — Fetch and extract text from URL."
    if "screen_record" in t:
        syn += (
            "\n  [VIDEO:SCREEN:filename=out.mov|duration=20|audio=on] — "
            "Record screen (macOS screencapture, ffmpeg fallback)"
        )
    if "video_merge" in t:
        syn += "\n  [VIDEO:MERGE:input1.mov,input2.mp4|output=final.mp4] — Concatenate videos (ffmpeg)"
    if "video_edit" in t:
        syn += (
            "\n  [VIDEO:EDIT:input.mov|output=cut.mp4|start=00:00:05|end=00:00:15|scale=1280x720] "
            "— Cut/trim/scale (ffmpeg)"
        )
    if "offload_recall" in t:
        syn += (
            "\n  [OFFLOAD_RECALL:<8-hex-chars>] — Volltext eines ausgelagerten "
            "Tool-Outputs zurückholen (node_id aus OFFLOAD-CANVAS)."
        )
    syn += '\n  <SHOWBOX:lamp_index>["Slide 1 HTML", "Slide 2 HTML"]</SHOWBOX> — Showbox update.'
    syn += "\n  3-LAYER-SYSTEM (hart durchgesetzt):"
    syn += "\n    <SHOWBOX:worker> (orange) → Worker (CoderAG, WriterAG, ResearcherAG, EditorAG)"
    syn += "\n    <SHOWBOX:system> (cyan) → System (GeneralAG, SoulAG)"
    syn += "\n    <SHOWBOX:user> (grün) → FÜR ALLE AGENTEN FREIGEGEBEN. Jeder Agent darf hier schreiben!"
    syn += "\n  Jeder Agent liefert NUR in SEINEM Layer."
    char = f" – {soul['character']}" if soul.get("character") else ""
    intro = f"You are {name} ({soul.get('role', 'Agent')}{char})."
    if soul.get("directive"):
        intro += f"\n[PERSONALITY] {soul['directive']}"

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
    sys_prompt += (
        "Beginne deine Antwort IMMER mit deinen detaillierten Überlegungen, "
        "Gedankengängen und Planungen bezüglich der Aufgabe. "
        "Umschließe diesen gesamten Denkprozess zwingend mit den XML-Tags "
        "<think> und </think> (Beispiel: <think>Meine Überlegungen...</think>). "
        "Erst danach folgt deine eigentliche Antwort und die Ausführung von Aktionen."
    )

    # ── ARBEITSPROTOKOLL (eiserne Regeln) ──────
    sys_prompt += (
        "\n\n[SOUL vs TASK-ID — KRITISCH]:\n"
        "• soul_memory / soul_passive.db / context.db / Dateien soul_* im Speicher = exklusiv SoulAG.\n"
        "• Task-IDs wie task_abc123, tracking_id=…, oder Nachrichten von SoulAG mit (ID: …) sind "
        "NUR Tracking — KEINE Grenzverletzung. Workspace-Arbeit unter gnom-Workspace/ ist erlaubt.\n"
        "• Antworte NIEMALS mit „Grenzverletzung soul_*“ nur weil die Task-ID soul_ oder task_ enthält.\n"
        "\n\n[ARBEITSPROTOKOLL — EISERNE REGELN]:\n"
        "• Du hast alle Tools die oben aufgelistet sind — nutze sie DIREKT.\n"
        "• Bei expliziten Aufträgen (vom User oder GeneralAG): Dateien SOFORT erstellen mit [WRITE:], "
        "Befehle SOFORT ausführen mit [SHELL:]. Nicht erst fragen!\n"
        "• GeneralAG-Delegation mit [WRITE:] zählt wie User-Befehl — Datei PFLICHT, nicht optional.\n"
        "• Bei Doku/README-HTML: [READ:] nur wenn nötig, dann in DIESER Antwort [WRITE: pfad]…[/WRITE] "
        "für JEDE geforderte Datei. Close-Tag [/WRITE] ist Pflicht. Nie nur lesen und stoppen.\n"
        "• PFAD-DISZIPLIN (R8): [WRITE:] und [SCREENSHOT: out=] Pfade ZEICHENGENAU aus dem Auftrag. "
        "Keine Aliase (shots/≠screenshots/, research_extract≠source_extract). "
        "HTML/Markdown mit Thema Gnom-Hub: exakter Substring `Gnom-Hub` (nicht nur gnom-hub).\n"
        "• Multi-File: nach Writes [SCREENSHOT:] und/oder [VERIFY:] nutzen. Showbox-ACK ≠ Delivery.\n"
        "• ERGEBNIS-AUSLIEFERUNG: Dateien primär via [WRITE:]…[/WRITE] (Workspace). "
        "Chat nur kurze Statusmeldungen. Lange Erklärungen ohne Datei = Fail.\n"
        "• Showbox optional NACH Writes — nie statt Writes.\n"
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
