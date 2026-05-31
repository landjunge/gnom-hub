import logging
import os, sys, subprocess, psutil
from gnom_hub.core.config import RUN_DIR, PROJECT_ROOT
AGENTS = ["generalAG", "soulAG", "researcherAG", "writerAG", "editorAG", "coderAG", "watchdogAG", "securityAG"]

def _get_proc(name: str):
    try:
        pid = int((RUN_DIR / f"{name}.pid").read_text().strip())
        p = psutil.Process(pid)
        if any(f"agents.{name}" in arg for arg in p.cmdline()): return p
    except (ValueError, OSError, psutil.Error) as e:
        logging.getLogger(__name__).error('Fehler in Prozess-Abfrage: %s', e)
    return None

def _kill_proc(name: str) -> None:
    p = _get_proc(name)
    if p:
        try:
            p.terminate()
            p.wait(timeout=2)
        except psutil.Error:
            try: p.kill()
            except OSError as e:
                logging.getLogger(__name__).error('Fehler in Prozess-Beendigung: %s', e)
    (RUN_DIR / f"{name}.pid").unlink(missing_ok=True)

def start_background_agents() -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for a in AGENTS:
        _kill_proc(a)
        with open(log_dir / f"logs_{a}.txt", "w") as f:
            p = subprocess.Popen([sys.executable, "-u", "-m", f"agents.{a}"], stdout=f, stderr=subprocess.STDOUT, cwd=str(PROJECT_ROOT))
            (RUN_DIR / f"{a}.pid").write_text(str(p.pid))

def kill_background_agents() -> None:
    for a in AGENTS: _kill_proc(a)

def process_status() -> str:
    return "\n".join(f"{a}: {'RUNNING' if _get_proc(a) else 'STOPPED'}" for a in AGENTS)

def restart_hub() -> None:
    sys.exit(42)
