# action_handlers.py — Verarbeitet [WRITE:], [READ:], [SHELL:], [IMAGE:], [CRAWL:] Tags
import os, re, requests

def handle_write(answer, matches, agent, perms, bs_mode, wd):
    for m in matches:
        fname, content = m.group(1).strip(), m.group(2).strip()
        if bs_mode:
            answer = answer.replace(m.group(0), f"[System: WRITE blockiert im Brainstorm-Modus. Nutze @{agent['name']} für Einzelauftrag.]")
        elif "write" not in perms:
            answer = answer.replace(m.group(0), f"[System: {agent['name']} hat keine WRITE-Berechtigung.]")
        else:
            try:
                fpath = os.path.join(wd, fname)
                if os.path.exists(fpath):
                    import shutil; shutil.copy2(fpath, fpath + ".bak")
                with open(fpath, "w") as f: f.write(content)
                answer = answer.replace(m.group(0), f"[System: Datei '{fname}' wurde erfolgreich im Workspace gespeichert.]")
            except Exception as e:
                answer = answer.replace(m.group(0), f"[System-Fehler beim Speichern von {fname}: {e}]")
    return answer

def handle_read(answer, matches, wd):
    for m in matches:
        fname = m.group(1).strip()
        p = os.path.join(wd, fname)
        if os.path.exists(p):
            c = open(p, "r").read()[:2000]
            answer = answer.replace(m.group(0), f"[Hat {fname} gelesen:\n{c}\n...]")
        else:
            answer = answer.replace(m.group(0), f"[Fehler: Datei {fname} nicht gefunden]")
    return answer

def handle_shell(answer, matches, agent, perms, bs_mode, wd):
    import subprocess
    for m in matches:
        cmd = m.group(1).strip()
        if bs_mode:
            answer = answer.replace(m.group(0), "[System: SHELL blockiert im Brainstorm-Modus.]")
        elif "run" not in perms and "godmode" not in perms:
            answer = answer.replace(m.group(0), f"[System: {agent['name']} hat keine SHELL-Berechtigung.]")
        else:
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=wd)
                answer = answer.replace(m.group(0), f"[Shell-Ausgabe ({cmd}):\n{(r.stdout+r.stderr)[:1500]}]")
            except Exception as e:
                answer = answer.replace(m.group(0), f"[Shell-Fehler: {str(e)[:80]}]")
    return answer

def handle_crawl(answer, matches, agent, perms):
    for m in matches:
        url = m.group(1).strip()
        if "@job" not in perms:
            answer = answer.replace(m.group(0), f"[System: {agent['name']} hat keine CRAWL-Berechtigung.]"); continue
        try:
            from .smart_crawlerAG import smart_request
            from .data_crawlerAG import data_crawl as _dc
            aname = agent["name"].lower()
            text = _dc(url) if "data_crawler" in aname else smart_request(url)
            answer = answer.replace(m.group(0), f"[Crawl-Ergebnis ({url[:60]}):\n{text[:3000]}]")
        except Exception as e:
            answer = answer.replace(m.group(0), f"[Crawl-Fehler: {str(e)[:80]}]")
    return answer

def process_actions(answer, agent, perms, bs_mode, wd):
    """Verarbeitet alle Action-Tags in einer LLM-Antwort."""
    answer = handle_write(answer, list(re.finditer(r"\[WRITE:\s*(.*?)\](.*?)\[/WRITE\]", answer, re.DOTALL)), agent, perms, bs_mode, wd)
    answer = handle_read(answer, list(re.finditer(r"\[READ:\s*(.*?)\]", answer)), wd)
    answer = handle_shell(answer, list(re.finditer(r"\[SHELL:\s*(.*?)\]", answer)), agent, perms, bs_mode, wd)
    answer = handle_crawl(answer, list(re.finditer(r"\[CRAWL:\s*(.*?)\]", answer)), agent, perms)
    return answer
