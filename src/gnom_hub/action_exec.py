import json, subprocess, re as _re
SHELL_BLOCK = _re.compile(r"rm\s+-rf\s+/|curl.*\|\s*sh|wget.*\|\s*sh|dd\s+if=|mkfs|>\s*/etc/|:(){ :|:& };:", _re.I)
def handle_shell(ans, ms, ag, perms, bs, wd):
    for m in ms:
        c, o = m.group(1).strip(), m.group(0)
        if bs: ans = ans.replace(o, "[System: SHELL blockiert im Brainstorm-Modus.]")
        elif "run" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine SHELL-Berechtigung.]")
        elif SHELL_BLOCK.search(c): ans = ans.replace(o, f"[System: BLOCKIERT — gefährlicher Befehl: {c[:60]}]")
        else:
            try:
                from gnom_hub.soul import check_and_wait_breakpoint
                check_and_wait_breakpoint(ag["name"], "before_shell", c)
                
                from gnom_hub.process.sandbox import run_in_sandbox
                r = run_in_sandbox(c, agent=ag, timeout=30)
                ans = ans.replace(o, f"[Shell ({c}):\n{(r.stdout+r.stderr)[:1500]}]")
            except Exception as e: ans = ans.replace(o, f"[Shell-Fehler: {str(e)[:80]}]")
    return ans
def handle_crawl(ans, ms, ag, perms):
    for m in ms:
        u, o = m.group(1).strip(), m.group(0)
        if "@job" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine CRAWL-Berechtigung.]"); continue
        try:
            from .crawler_engine import crawl_smart, crawl_data
            t = crawl_data(u) if "data" in ag["name"].lower() else crawl_smart(u)
            ans = ans.replace(o, f"[Crawl-Ergebnis ({u[:60]}):\n{t[:3000]}]")
        except Exception as e: ans = ans.replace(o, f"[Crawl-Fehler: {str(e)[:80]}]")
    return ans
def handle_showbox(ans, ms):
    from gnom_hub.core.json_sanitizer import _sanitize_json
    from agents.securityAG import generate_signature
    from .db import save_showbox_presentation, set_active_showbox
    for full, idx, raw in ms:
        try:
            d = _sanitize_json(raw.strip())
            if isinstance(d, list):
                slides = d
                d = {"slides": d}
            else:
                d.pop("sig", None)
                slides = d.get("slides", [])

            # Prevent style bleeding by scoping global elements to .sb-layer-body
            cleaned_slides = []
            for sld in slides:
                if isinstance(sld, str):
                    sld = _re.sub(r'\bbody\b', '.sb-layer-body', sld, flags=_re.I)
                    sld = _re.sub(r'\bhtml\b', '.sb-layer-body', sld, flags=_re.I)
                    sld = _re.sub(r'(?<!\w)\*(?!\w)', '.sb-layer-body *', sld)
                cleaned_slides.append(sld)
            slides = cleaned_slides
            d["slides"] = slides
            
            d["sig"] = generate_signature("Gnom", json.dumps(d, separators=(',', ':'), sort_keys=True))
            
            # Map index/name
            presentation_name = idx.strip() if idx else ""
            if presentation_name.isdigit() and 1 <= int(presentation_name) <= 7:
                presentation_name = f"Showbox {presentation_name}"
            elif not presentation_name:
                presentation_name = "Latest Update"
                
            # Save to SQLite database
            save_showbox_presentation(presentation_name, slides, sender="Agent")
            set_active_showbox(presentation_name)
            
            ans = ans.replace(full, f"<SHOWBOX{':'+idx if idx else ''}>{json.dumps(d)}</SHOWBOX>")
        except Exception as e: ans = ans.replace(full, f"[Showbox-Fehler: {e}]")
    return ans

