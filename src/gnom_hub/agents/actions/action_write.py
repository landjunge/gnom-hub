# action_write.py — [WRITE:] und [READ:] Handler
# Git wurde 2026-06-15 komplett entfernt — Agenten schreiben Files ohne Auto-Commit.
import os
import re

from gnom_hub.core.security.path_validator import _safe


def seal_content(content: str) -> str:
    return content.strip()

def handle_write(answer, matches, agent, perms, bs_mode, wd):
    agent_name = (agent or {}).get("name") if isinstance(agent, dict) else None
    for m in matches:
        fname, content = m.group(1).strip(), m.group(2).strip()
        content = re.sub(r"^```\w*\n", "", re.sub(r"\n```$", "", content).strip())
        if "write" not in perms: r = f"[System: {agent['name']} hat keine WRITE-Berechtigung.]"
        else:
            fpath = _safe(wd, fname, perms, agent_name=agent_name)
            if not fpath: r = f"[System: Pfad '{fname}' blockiert — außerhalb des Workspace (kein Grant / kein godmode).]"
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
                            new_fpath = _safe(wd, new_name, perms, agent_name=agent_name)
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

                    # Bug fix (2026-06-29, branch experimental/action-handler-fix):
                    # use gnom_hub.core.zwc_codec instead of gnom_hub.soul.zwc_soul.
                    # The latter transitively imports SoulAG → sentence_transformers
                    # → torch (~5-30s cold start) via gnom_hub/soul/__init__.py,
                    # which ran on every successful [WRITE:] and caused LLM-side
                    # race conditions (the file *was* written at line 38-39, but
                    # the response was delayed so user-side heuristics reported
                    # "nothing happened"). zwc_codec is pure-stdlib and safe
                    # to import from any handler.
                    from gnom_hub.core.zwc_codec import add_agent_metadata
                    r = f"[System: Datei '{fname}' gespeichert unter {os.path.abspath(fpath)}.{auto_open}]" + add_agent_metadata(agent["name"], "")

                except Exception as e:
                    try:
                        from gnom_hub.core.audit_helpers import record_write_fail
                        record_write_fail(agent["name"], path=str(fpath),
                                          error=f"{type(e).__name__}: {e}")
                    except Exception:
                        pass
                    r = f"[System-Fehler: {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer

def handle_read(answer, matches, wd, perms=None, agent=None):
    agent_name = None
    if isinstance(agent, dict):
        agent_name = agent.get("name")
    elif isinstance(agent, str):
        agent_name = agent
    for m in matches:
        fname = m.group(1).strip()
        p = _safe(wd, fname, perms or [], agent_name=agent_name, for_read=True)
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
                with open(p, encoding="utf-8", errors="ignore") as f:
                    r = f"[Hat {fname} gelesen:\n{f.read()[:2000]}\n...]"
            except Exception as e:
                r = f"[Fehler beim Lesen von {fname}: {e}]"
        answer = answer.replace(m.group(0), r)
    return answer
