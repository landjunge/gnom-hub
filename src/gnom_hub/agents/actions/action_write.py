# action_write.py — [WRITE:] und [READ:] Handler
# Git wurde 2026-06-15 komplett entfernt — Agenten schreiben Files ohne Auto-Commit.
import os, re
from gnom_hub.core.security.path_validator import _safe

def seal_content(content: str) -> str:
    return content.strip()

def handle_write(answer, matches, agent, perms, bs_mode, wd):
    for m in matches:
        fname, content = m.group(1).strip(), m.group(2).strip()
        content = re.sub(r"^```\w*\n", "", re.sub(r"\n```$", "", content).strip())
        if "write" not in perms: r = f"[System: {agent['name']} hat keine WRITE-Berechtigung.]"
        else:
            fpath = _safe(wd, fname, perms)
            if not fpath: r = f"[System: Pfad '{fname}' blockiert — außerhalb des Workspace.]"
            else:
                try:
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)

                    base = os.path.basename(fname).lower()
                    if base == "index.html" and os.path.exists(fpath):
                        base_name = os.path.splitext(fname)[0]
                        ext = os.path.splitext(fname)[1]
                        counter = 1
                        while True:
                            new_name = f"{base_name}{counter}{ext}"
                            new_fpath = _safe(wd, new_name, perms)
                            if new_fpath and not os.path.exists(new_fpath):
                                fpath = new_fpath
                                fname = os.path.basename(fpath)
                                break
                            counter += 1
                    elif os.path.exists(fpath):
                        import shutil; shutil.copy2(fpath, fpath + ".bak")

                    sealed_content = seal_content(content)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(sealed_content)

                    auto_open = ""
                    if base.startswith("index") and "run" in perms:
                        try:
                            import subprocess
                            subprocess.Popen(["open", fpath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            auto_open = " [Browser geöffnet]"
                        except (FileNotFoundError, OSError):
                            pass

                    from gnom_hub.soul.zwc_soul import add_agent_metadata
                    r = f"[System: Datei '{fname}' gespeichert unter {os.path.abspath(fpath)}.{auto_open}]" + add_agent_metadata(agent["name"], "")

                except Exception as e: r = f"[System-Fehler: {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer

def handle_read(answer, matches, wd, perms=None):
    for m in matches:
        fname = m.group(1).strip(); p = _safe(wd, fname, perms or [])
        if not p:
            r = f"[System: Pfad '{fname}' blockiert.]"
        elif os.path.isdir(p):
            # Verzeichnis → listing statt Fehler
            try:
                entries = sorted(os.listdir(p))[:50]
                listing = "\n".join(f"  {('📁' if os.path.isdir(os.path.join(p,e)) else '📄')} {e}" for e in entries)
                more = f"\n  … und {len(entries)} weitere" if len(entries) >= 50 else ""
                r = f"[Verzeichnis {fname}/\n{listing}{more}\n]"
            except Exception as e:
                r = f"[Fehler beim Lesen von Verzeichnis {fname}: {e}]"
        elif not os.path.isfile(p):
            r = f"[Fehler: Datei {fname} nicht gefunden]"
        else:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    r = f"[Hat {fname} gelesen:\n{f.read()[:2000]}\n...]"
            except Exception as e:
                r = f"[Fehler beim Lesen von {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer
