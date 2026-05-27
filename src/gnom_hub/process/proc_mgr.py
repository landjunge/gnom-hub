"""
Prozess-Manager für GNOM-HUB.
Verwaltet den Lebenszyklus der Hintergrund-Agenten mittels PID-Dateien und psutil.
"""

import os
import sys
import subprocess
from pathlib import Path
import psutil

AGENTS = ["generalAG", "soulAG", "researcherAG", "writerAG", "editorAG", "coderAG", "watchdogAG"]
RUN_DIR = Path.home() / ".gnom-hub" / "run"
RUN_DIR.mkdir(parents=True, exist_ok=True)

def _get_proc(name):
    try:
        pid = int((RUN_DIR / f"{name}.pid").read_text().strip())
        p = psutil.Process(pid)
        if any(f"agents.{name}" in arg for arg in p.cmdline()):
            return p
    except (ValueError, OSError, psutil.Error):
        pass
    return None

def _kill_process(name):
    p = _get_proc(name)
    if p:
        try:
            p.terminate()
            p.wait(timeout=2)
        except psutil.Error:
            try: p.kill()
            except OSError: pass
    try:
        (RUN_DIR / f"{name}.pid").unlink(missing_ok=True)
    except OSError:
        pass

def start_background_agents():
    os.makedirs("logs", exist_ok=True)
    for a in AGENTS:
        _kill_process(a)
        with open(f"logs/logs_{a}.txt", "w") as f:
            p = subprocess.Popen([sys.executable, "-u", "-m", f"agents.{a}"], stdout=f, stderr=subprocess.STDOUT)
            (RUN_DIR / f"{a}.pid").write_text(str(p.pid))

def kill_background_agents():
    for a in AGENTS:
        _kill_process(a)

def process_status():
    return "\n".join(f"{a}: {'RUNNING' if _get_proc(a) else 'STOPPED'}" for a in AGENTS)

def restart_hub():
    os._exit(42)
