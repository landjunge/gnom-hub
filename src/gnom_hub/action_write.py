# action_write.py — [WRITE:] und [READ:] Handler
import os, re
from .path_validator import _safe

def handle_write(answer, matches, agent, perms, bs_mode, wd):
    from agents.securityAG import seal_content; from .ftp_deploy import get_deploy; from .ftp_sync import sync_index
    for m in matches:
        fname, content = m.group(1).strip(), m.group(2).strip()
        content = re.sub(r"^```\w*\n", "", re.sub(r"\n```$", "", content).strip())
        if bs_mode: r = "[System: WRITE blockiert im Brainstorm-Modus.]"
        elif "write" not in perms: r = f"[System: {agent['name']} hat keine WRITE-Berechtigung.]"
        else:
            fpath = _safe(wd, fname, perms)
            if not fpath: r = f"[System: Pfad '{fname}' blockiert — außerhalb des Workspace.]"
            else:
                try:
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)
                    if os.path.exists(fpath):
                        import shutil; shutil.copy2(fpath, fpath + ".bak")
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(seal_content(agent["name"], content, fname))
                    r = f"[System: Datei '{fname}' gespeichert.]"
                    if get_deploy() and fname.endswith((".html", ".md", ".css")): sync_index(wd)
                except Exception as e: r = f"[System-Fehler: {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer

def handle_read(answer, matches, wd, perms=None):
    for m in matches:
        fname = m.group(1).strip(); p = _safe(wd, fname, perms or [])
        if not p: r = f"[System: Pfad '{fname}' blockiert.]"
        elif os.path.isdir(p): r = f"[Fehler: '{fname}' ist ein Verzeichnis]"
        elif not os.path.isfile(p): r = f"[Fehler: Datei {fname} nicht gefunden]"
        else:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    r = f"[Hat {fname} gelesen:\n{f.read()[:2000]}\n...]"
            except Exception as e: r = f"[Fehler beim Lesen von {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer
