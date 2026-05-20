import json, subprocess, re as _re
SHELL_BLOCK = _re.compile(r"rm\s+-rf\s+/|curl.*\|\s*sh|wget.*\|\s*sh|dd\s+if=|mkfs|>\s*/etc/|:(){ :|:& };:", _re.I)
def handle_shell(ans, ms, ag, perms, bs, wd):
    for m in ms:
        c, o = m.group(1).strip(), m.group(0)
        if bs: ans = ans.replace(o, "[System: SHELL blockiert im Brainstorm-Modus.]")
        elif "run" not in perms and "godmode" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine SHELL-Berechtigung.]")
        elif "godmode" not in perms and SHELL_BLOCK.search(c): ans = ans.replace(o, f"[System: BLOCKIERT — gefährlicher Befehl: {c[:60]}]")
        else:
            try:
                from .sandbox_exec import run_sandboxed
                r = run_sandboxed(c, wd, timeout=30)
                ans = ans.replace(o, f"[Shell ({c}):\n{(r.stdout+r.stderr)[:1500]}]")
            except Exception as e: ans = ans.replace(o, f"[Shell-Fehler: {str(e)[:80]}]")
    return ans
def handle_crawl(ans, ms, ag, perms):
    for m in ms:
        u, o = m.group(1).strip(), m.group(0)
        if "@job" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine CRAWL-Berechtigung.]"); continue
        try:
            from .smart_crawlerAG import smart_request; from .data_crawlerAG import data_crawl as _dc
            t = _dc(u) if "data_crawler" in ag["name"].lower() else smart_request(u)
            ans = ans.replace(o, f"[Crawl-Ergebnis ({u[:60]}):\n{t[:3000]}]")
        except Exception as e: ans = ans.replace(o, f"[Crawl-Fehler: {str(e)[:80]}]")
    return ans
def _sanitize_json(raw):
    """Robust JSON parser for LLM-generated Showbox content."""
    raw = raw.strip()
    try: return json.loads(raw)
    except Exception: pass
    match = _re.search(r'\[\s*(.*)\s*\]', raw, _re.DOTALL)
    if not match: raise ValueError("Could not find JSON array")
    parts = _re.split(r'(?<!\\)"\s*,\s*(?=\s*(?:"|\[|\{))', match.group(1).strip())
    slides = []
    for p in parts:
        p = p.strip()
        if p.startswith('"'): p = p[1:]
        if p.endswith('"') and not p.endswith('\\"'): p = p[:-1]
        escaped = []
        i = 0
        while i < len(p):
            if p[i] == '"':
                bs = 0
                j = i - 1
                while j >= 0 and p[j] == '\\': bs += 1; j -= 1
                escaped.append('\\"' if bs % 2 == 0 else '"')
            elif p[i] == '\n': escaped.append('\\n')
            elif p[i] == '\t': escaped.append('\\t')
            else: escaped.append(p[i])
            i += 1
        slides.append(json.loads('"' + "".join(escaped) + '"'))
    return {"slides": slides}
def handle_showbox(ans, ms):
    from .securityAG import generate_signature
    for full, idx, raw in ms:
        try:
            d = _sanitize_json(raw.strip())
            if isinstance(d, list): d = {"slides": d}
            else: d.pop("sig", None)
            d["sig"] = generate_signature("Gnom", json.dumps(d, separators=(',', ':'), sort_keys=True))
            ans = ans.replace(full, f"<SHOWBOX{':'+idx if idx else ''}>{json.dumps(d)}</SHOWBOX>")
        except Exception as e: ans = ans.replace(full, f"[Showbox-Fehler: {e}]")
    return ans
