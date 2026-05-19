# action_write.py — [WRITE:] und [READ:] mit godmode-Bypass + Path-Schutz
import os
def _safe(wd, f, perms):
    """godmode darf überall, normale Agents nur im Workspace."""
    if "godmode" in perms: return os.path.realpath(os.path.join(wd, f)) if not os.path.isabs(f) else os.path.realpath(f)
    p = os.path.realpath(os.path.join(wd, f))
    return p if p.startswith(os.path.realpath(wd)) else None
def handle_write(answer, matches, agent, perms, bs_mode, wd):
    from .securityAG import seal_content
    for m in matches:
        fname, content = m.group(1).strip(), m.group(2).strip()
        if bs_mode:
            answer = answer.replace(m.group(0), "[System: WRITE blockiert im Brainstorm-Modus.]")
        elif "write" not in perms:
            answer = answer.replace(m.group(0), f"[System: {agent['name']} hat keine WRITE-Berechtigung.]")
        else:
            fpath = _safe(wd, fname, perms)
            if not fpath:
                answer = answer.replace(m.group(0), f"[System: Pfad '{fname}' blockiert — Path Traversal.]"); continue
            try:
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                if os.path.exists(fpath):
                    import shutil; shutil.copy2(fpath, fpath + ".bak")
                with open(fpath, "w") as f: f.write(seal_content(agent["name"], content))
                answer = answer.replace(m.group(0), f"[System: Datei '{fname}' gespeichert.]")
            except Exception as e:
                answer = answer.replace(m.group(0), f"[System-Fehler: {fname}: {e}]")
    return answer
def handle_read(answer, matches, wd, perms=None):
    perms = perms or []
    for m in matches:
        fname = m.group(1).strip(); p = _safe(wd, fname, perms)
        if not p: answer = answer.replace(m.group(0), f"[System: Pfad '{fname}' blockiert.]")
        elif os.path.exists(p):
            answer = answer.replace(m.group(0), f"[Hat {fname} gelesen:\n{open(p).read()[:2000]}\n...]")
        else: answer = answer.replace(m.group(0), f"[Fehler: Datei {fname} nicht gefunden]")
    return answer
