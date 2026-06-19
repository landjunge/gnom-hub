import logging
import os, sys, subprocess, psutil
from gnom_hub.core.config import RUN_DIR, PROJECT_ROOT
from gnom_hub.core.constants import PROCESS_TERMINATE_TIMEOUT, PROCESS_KILL_SLEEP
from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
AGENTS = ["generalAG", "soulAG", "researcherAG", "writerAG", "editorAG", "coderAG", "watchdogAG", "securityAG"]
AGENT_DEFINITIONS_KEYS = list(AGENT_DEFINITIONS.keys())

def _get_proc(name: str):
    matched = next((a for a in AGENTS if a.lower() == name.lower()), name)
    try:
        pid = int((RUN_DIR / f"{matched}.pid").read_text().strip())
        p = psutil.Process(pid)
        if any("run_agent" in arg and matched.lower() in arg.lower() for arg in p.cmdline()): return p
        if any(f"agents.{matched}" in arg for arg in p.cmdline()): return p
    except (ValueError, OSError, psutil.Error) as e:
        logging.getLogger(__name__).warning('PID-Datei fehlt oder Prozess nicht erreichbar (erwartet nach Cleanup): %s', e)
    return None

def _kill_proc(name: str) -> None:
    matched = next((a for a in AGENTS if a.lower() == name.lower()), name)
    p = _get_proc(matched)
    if p:
        try:
            p.terminate()
            p.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
        except psutil.Error:
            try: p.kill()
            except OSError as e:
                logging.getLogger(__name__).error('Fehler in Prozess-Beendigung: %s', e)
    (RUN_DIR / f"{matched}.pid").unlink(missing_ok=True)

def _kill_all_agents_by_pid_files() -> None:
    killed = set()
    for pid_file in RUN_DIR.glob("*.pid"):
        try:
            pid = int(pid_file.read_text().strip())
            try:
                p = psutil.Process(pid)
                p.terminate()
                p.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
                killed.add(pid)
            except (psutil.NoSuchProcess, psutil.Error):
                pass
        except (ValueError, OSError):
            pass
        pid_file.unlink(missing_ok=True)
    for a in AGENTS:
        _kill_orphans_by_cmdline(a, killed)


def _kill_orphans_by_cmdline(agent_name: str, already_killed: set) -> None:
    """Fängt Waisen-Prozesse ab, deren PID-Datei verloren ging
    (z.B. nach Crash oder überschriebener PID-Datei)."""
    needle = f"agents.{agent_name}"
    for p in psutil.process_iter(["pid", "cmdline"]):
        if p.info["pid"] in already_killed:
            continue
        try:
            cmdline = p.info.get("cmdline") or []
            if any(needle in arg for arg in cmdline):
                p.terminate()
                try:
                    p.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
                except psutil.Error:
                    try: p.kill()
                    except OSError: pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def start_background_agents() -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    _kill_all_agents_by_pid_files()
    for a in AGENTS:
        _kill_proc(a)
    import time; time.sleep(PROCESS_KILL_SLEEP)

    # 2. Alle Agenten in DB auf online zurücksetzen
    try:
        from gnom_hub.db.connection import get_db_connection
        conn = get_db_connection()
        conn.execute("UPDATE agents SET status='online', circuit_state='CLOSED', consecutive_failures=0")
        conn.execute("UPDATE agent_messages SET status='done', completed_at=? WHERE status IN ('processing','pending')", (time.time(),))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.getLogger(__name__).warning("DB cleanup bei Agent-Start fehlgeschlagen: %s", e)

    # 3. Frische Agenten starten
    for a in AGENTS:
        log_file = log_dir / f"logs_{a}.txt"
        # Rotation: bestehende Datei zu .1, .2, .3 wenn > 10MB
        if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:
            for i in range(3, 0, -1):
                old = log_file.with_suffix(f".txt.{i-1}" if i > 1 else ".txt.1")
                old_bk = log_file.with_name(f"{log_file.name}.{i-1}" if i > 1 else f"{log_file.name}.1")
                if log_file.with_name(f"{log_file.name}.{i-1}").exists():
                    log_file.with_name(f"{log_file.name}.{i}").write_bytes(log_file.with_name(f"{log_file.name}.{i-1}").read_bytes())
            if log_file.with_name(f"{log_file.name}.1").exists():
                log_file.with_name(f"{log_file.name}.1").unlink()
            log_file.rename(log_file.with_name(f"{log_file.name}.1"))
        agent_name = next((k for k in AGENT_DEFINITIONS_KEYS if k.lower() == a.lower()), a)
        p = subprocess.Popen(
            [sys.executable, "-u", "-m", "agents.run_agent", "--name", agent_name],
            stdout=open(log_file, "w"), stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
            env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        )
        (RUN_DIR / f"{a}.pid").write_text(str(p.pid))

def kill_background_agents() -> None:
    for a in AGENTS: _kill_proc(a)

def process_status() -> str:
    return "\n".join(f"{a}: {'RUNNING' if _get_proc(a) else 'STOPPED'}" for a in AGENTS)

def restart_hub() -> None:
    import os, signal
    os.environ["GNOM_HUB_RESTART"] = "true"
    os.kill(os.getpid(), signal.SIGINT)

def restart_single_agent(name: str) -> None:
    matched = next((a for a in AGENTS if a.lower() == name.lower()), None)
    if not matched:
        logging.getLogger(__name__).warning("Restart abgelehnt: Agent '%s' unbekannt.", name)
        return
    _kill_proc(matched)
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"logs_{matched}.txt", "a") as f:
        p = subprocess.Popen([sys.executable, "-u", "-m", f"agents.{matched}"], stdout=f, stderr=subprocess.STDOUT, cwd=str(PROJECT_ROOT))
        (RUN_DIR / f"{matched}.pid").write_text(str(p.pid))
    logging.getLogger(__name__).info("Watchdog hat Agent '%s' (PID %d) neu gestartet.", matched, p.pid)


