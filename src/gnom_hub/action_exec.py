import json, subprocess
def handle_shell(ans, ms, ag, perms, bs, wd):
    for m in ms:
        c, o = m.group(1).strip(), m.group(0)
        if bs: ans = ans.replace(o, "[System: SHELL blockiert im Brainstorm-Modus.]")
        elif "run" not in perms and "godmode" not in perms: ans = ans.replace(o, f"[System: {ag['name']} hat keine SHELL-Berechtigung.]")
        else:
            try: r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30, cwd=wd); ans = ans.replace(o, f"[Shell ({c}):\n{(r.stdout+r.stderr)[:1500]}]")
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
def handle_showbox(ans, ms):
    from .securityAG import generate_signature
    import re as _re
    for m in ms:
        try:
            raw = m.group(1).strip()
            # LLMs produce unescaped newlines/tabs — escape them INSIDE strings only
            # Strategy: replace all newlines, then let json.loads handle it
            # First try parsing as-is (works for clean JSON)
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                # Escape control chars inside JSON string values
                # Replace newlines that are inside quotes (between matched quotes)
                def _fix(s):
                    out, in_str, esc = [], False, False
                    for c in s:
                        if esc:
                            out.append(c); esc = False; continue
                        if c == "\\":
                            out.append(c); esc = True; continue
                        if c == '"':
                            in_str = not in_str; out.append(c); continue
                        if in_str and c == "\n":
                            out.append("\\n"); continue
                        if in_str and c == "\r":
                            continue
                        if in_str and c == "\t":
                            out.append("\\t"); continue
                        out.append(c)
                    return "".join(out)
                d = json.loads(_fix(raw))
            d.pop("sig", None)
            d["sig"] = generate_signature("Gnom", json.dumps(d, separators=(',', ':'), sort_keys=True))
            ans = ans.replace(m.group(0), f"<SHOWBOX>{json.dumps(d)}</SHOWBOX>")
        except Exception as e: ans = ans.replace(m.group(0), f"[Showbox-Fehler: Ungültiges JSON - {e}]")
    return ans
