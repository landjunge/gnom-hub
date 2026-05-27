# action_write.py — [WRITE:] und [READ:] Handler
import os, re
from gnom_hub.security.path_validator import _safe

def _git_commit_file(wd, rel_path, agent_name):
    import subprocess
    from pathlib import Path
    try:
        git_dir = Path(wd) / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=wd, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Gnom-Hub Agents"], cwd=wd, capture_output=True)
            subprocess.run(["git", "config", "user.email", "agents@gnom-hub.local"], cwd=wd, capture_output=True)
        
        subprocess.run(["git", "add", rel_path], cwd=wd, capture_output=True)
        diff_res = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=wd)
        if diff_res.returncode != 0:
            subprocess.run([
                "git", "commit", 
                "-m", f"Agent {agent_name} -> {rel_path}", 
                f"--author={agent_name} <{agent_name.lower()}@gnom-hub.local>"
            ], cwd=wd, capture_output=True)
    except Exception as e:
        print(f"Git auto-commit failed: {e}")

def handle_write(answer, matches, agent, perms, bs_mode, wd):
    from agents.securityAG import seal_content
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
                    from gnom_hub.soul import check_and_wait_breakpoint
                    check_and_wait_breakpoint(agent["name"], "before_write", fname)
                    
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)
                    if os.path.exists(fpath):
                        import shutil; shutil.copy2(fpath, fpath + ".bak")
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    rel_path = os.path.relpath(fpath, wd)
                    _git_commit_file(wd, rel_path, agent["name"])

                    from gnom_hub.soul.zwc_soul import add_agent_metadata
                    r = f"[System: Datei '{fname}' gespeichert.]" + add_agent_metadata(agent["name"], "")

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
