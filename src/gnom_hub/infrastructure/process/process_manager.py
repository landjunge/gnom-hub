import logging
import os
import subprocess
import sys

import psutil

from gnom_hub.agents.agent_definitions import AGENT_DEFINITIONS
from gnom_hub.core.config import PROJECT_ROOT, RUN_DIR
from gnom_hub.core.constants import PROCESS_KILL_SLEEP, PROCESS_TERMINATE_TIMEOUT

AGENTS = ["generalAG", "soulAG", "researcherAG", "writerAG", "editorAG", "coderAG", "watchdogAG", "securityAG"]
AGENT_DEFINITIONS_KEYS = list(AGENT_DEFINITIONS.keys())

def _reap_zombies() -> None:
    """Reap child zombies so they don't pin PID files and thrash health checks."""
    try:
        while True:
            pid, _ = os.waitpid(-1, os.WNOHANG)
            if pid <= 0:
                break
    except ChildProcessError:
        pass
    except OSError:
        pass


def _cmdline_is_agent(cmdline: list, matched: str) -> bool:
    """Match both launch styles: agents.run_agent --name X  and  agents.XAG."""
    if not cmdline:
        return False
    needle = matched.lower()
    joined = " ".join(cmdline).lower()
    # Style A: python -m agents.run_agent --name generalag
    if "agents.run_agent" in joined and needle in joined:
        return True
    # Style B: python -m agents.generalAG
    if f"agents.{needle}" in joined:
        return True
    return False


def _get_proc(name: str):
    matched = next((a for a in AGENTS if a.lower() == name.lower()), name)
    _reap_zombies()
    try:
        pid = int((RUN_DIR / f"{matched}.pid").read_text().strip())
        p = psutil.Process(pid)
        # Zombie / dead: clear pid file quietly (was spamming logs every health poll)
        if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
            (RUN_DIR / f"{matched}.pid").unlink(missing_ok=True)
            return None
        if _cmdline_is_agent(p.cmdline() or [], matched):
            return p
        # Stale pid file for unrelated process
        (RUN_DIR / f"{matched}.pid").unlink(missing_ok=True)
    except (ValueError, OSError, psutil.Error):
        pass
    # Fallback: scan process table (pid file missing / overwritten by double-start)
    try:
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                if _cmdline_is_agent(p.info.get("cmdline") or [], matched):
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
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
    for p in psutil.process_iter(["pid", "cmdline"]):
        if p.info["pid"] in already_killed:
            continue
        try:
            cmdline = p.info.get("cmdline") or []
            if not _cmdline_is_agent(cmdline, agent_name):
                continue
            p.terminate()
            try:
                p.wait(timeout=PROCESS_TERMINATE_TIMEOUT)
            except psutil.Error:
                try:
                    p.kill()
                except OSError:
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def start_background_agents() -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    _kill_all_agents_by_pid_files()
    for a in AGENTS:
        _kill_proc(a)
    import time; time.sleep(PROCESS_KILL_SLEEP)

    # 2. Alle Agenten in DB auf online zurücksetzen.
    # Queue: processing → pending requeue (Agents gestorben mitten im Job).
    # pending bleibt pending — KEIN massenhaftes status='done' mehr
    # (Prio-2 Fix: Restart darf User-Jobs nicht still verwerfen).
    try:
        from gnom_hub.db.connection import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "UPDATE agents SET status='online', circuit_state='CLOSED', consecutive_failures=0"
        )
        # Count before requeue for logging / user feedback
        pending_n = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE status='pending'"
        ).fetchone()[0]
        processing_n = conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE status='processing'"
        ).fetchone()[0]
        if processing_n:
            conn.execute(
                """
                UPDATE agent_messages
                SET status='pending', processing_since=NULL, deliver_after=0
                WHERE status='processing'
                """
            )
        conn.commit()
        conn.close()
        log = logging.getLogger(__name__)
        if processing_n or pending_n:
            log.warning(
                "Agent-Start Queue: %d processing→pending requeued, %d pending preserved",
                processing_n, pending_n,
            )
        if processing_n:
            try:
                from gnom_hub.db import add_chat_message, get_active_project
                add_chat_message(
                    get_active_project() or "default",
                    "System",
                    "system",
                    "chat",
                    (
                        f"♻️ **Hub-Restart:** {processing_n} hängende Job(s) wieder in die Queue "
                        f"gestellt ({pending_n} waren bereits pending)."
                    ),
                    {"type": "chat", "sender": "System", "queue_requeue": True},
                )
            except Exception as chat_exc:
                log.debug("Queue-requeue Chat-Hinweis fehlgeschlagen: %s", chat_exc)
    except Exception as e:
        logging.getLogger(__name__).warning("DB cleanup bei Agent-Start fehlgeschlagen: %s", e)

    # 3. Frische Agenten starten
    for a in AGENTS:
        log_file = log_dir / f"logs_{a}.txt"
        # Rotation: bestehende Datei zu .1, .2, .3 wenn > 10MB
        if log_file.exists() and log_file.stat().st_size > 10 * 1024 * 1024:
            for i in range(3, 0, -1):
                log_file.with_suffix(f".txt.{i-1}" if i > 1 else ".txt.1")
                log_file.with_name(f"{log_file.name}.{i-1}" if i > 1 else f"{log_file.name}.1")
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
            # CRITICAL: start_new_session=True setzt eine eigene Process-Group
            # für jedes Subprocess. Sonst werden die Agents beim Hub-Tod zu
            # Waisen (PPID=1) und laufen ewig weiter. Mit eigener PG kann man
            # via os.killpg(os.getpgid(pid), SIGTERM) ALLE auf einmal killen.
            start_new_session=True,
        )
        (RUN_DIR / f"{a}.pid").write_text(str(p.pid))

def kill_background_agents() -> None:
    for a in AGENTS: _kill_proc(a)

def process_status() -> str:
    return "\n".join(f"{a}: {'RUNNING' if _get_proc(a) else 'STOPPED'}" for a in AGENTS)

def restart_hub() -> None:
    import signal
    os.environ["GNOM_HUB_RESTART"] = "true"
    os.kill(os.getpid(), signal.SIGINT)

def restart_single_agent(name: str) -> None:
    matched = next((a for a in AGENTS if a.lower() == name.lower()), None)
    if not matched:
        logging.getLogger(__name__).warning("Restart abgelehnt: Agent '%s' unbekannt.", name)
        return
    # Kill all instances of this agent (both launch styles) before respawn
    _kill_proc(matched)
    _kill_orphans_by_cmdline(matched, set())
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    agent_name = next((k for k in AGENT_DEFINITIONS_KEYS if k.lower() == matched.lower()), matched)
    log_file = log_dir / f"logs_{matched}.txt"
    # Match start_background_agents: pass an open file object and do not close it
    # in a `with` block around Popen (avoids stdout races on watchdog restart).
    p = subprocess.Popen(
        [sys.executable, "-u", "-m", "agents.run_agent", "--name", agent_name],
        stdout=open(log_file, "a"),  # noqa: SIM115 — same intentional pattern as bulk start
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        start_new_session=True,
    )
    (RUN_DIR / f"{matched}.pid").write_text(str(p.pid))
    logging.getLogger(__name__).info("Watchdog hat Agent '%s' (PID %d) neu gestartet.", matched, p.pid)


