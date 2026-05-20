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
    """Escape unescaped newlines/tabs in JSON strings from LLM output."""
    import re
    try: return json.loads(raw)
    except json.JSONDecodeError: return json.loads(re.sub(r'(?<=": ")(.*?)(?="[,}])', lambda m: m.group().replace("\n", "\\n").replace("\t", "\\t"), raw, flags=re.DOTALL))
def handle_showbox(ans, ms):
    from .securityAG import generate_signature
    for m in ms:
        try:
            d = _sanitize_json(m.group(1).strip()); d.pop("sig", None)
            d["sig"] = generate_signature("Gnom", json.dumps(d, separators=(',', ':'), sort_keys=True))
            ans = ans.replace(m.group(0), f"<SHOWBOX>{json.dumps(d)}</SHOWBOX>")
        except Exception as e: ans = ans.replace(m.group(0), f"[Showbox-Fehler: Ungültiges JSON - {e}]")
    return ans
