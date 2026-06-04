# sandbox.py — Hybrid Docker & macOS Sandbox Executor
import logging
import subprocess, os
from gnom_hub.core.config import WORKSPACE_DIR
from gnom_hub.infrastructure.process.sandbox_exec import run_sandboxed

def is_docker_running():
    if os.getenv("GNOM_DISABLE_DOCKER") == "1": return False
    try: return subprocess.run(["docker", "ps"], capture_output=True, timeout=2).returncode == 0
    except Exception as e: logging.getLogger(__name__).error('Fehler in Docker-Verfügbarkeitsprüfung: %s', e); return False

def run_in_sandbox(command: str, agent=None, timeout: int = 30):
    from gnom_hub.core.config import Config
    if Config.ENABLE_WORKSPACE_SANDBOX and agent:
        from gnom_hub.core.security.gatekeeper import verify_cmd
        if not verify_cmd(agent, command): raise PermissionError("Befehlsausführung verweigert.")
    from gnom_hub.db.state_repo import SQLiteStateRepository
    proj = SQLiteStateRepository().get_active_project() or "default"
    wd = os.path.abspath(os.path.join(str(WORKSPACE_DIR), proj))
    if not Config.ENABLE_WORKSPACE_SANDBOX:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=wd)
        return r
    if is_docker_running():
        # Mount workspace as read-only; create a writable /tmp dir for agent outputs
        cmd = ["docker", "run", "--rm", "--network=none", "--memory=512m", "--cpus=1",
               "-w", "/workspace",
               "-v", f"{wd}:/workspace:ro",
               "--tmpfs", "/tmp:size=100m",
               "python:3.11-slim", "bash", "-c", command]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return subprocess.CompletedProcess(args=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except Exception as e: logging.getLogger(__name__).error('Fehler in Docker-Sandbox-Ausführung: %s', e)
    return run_sandboxed(command, wd, timeout=timeout)

def run_browser_in_sandbox(code_path: str, net: str, timeout: int = 30):
    from gnom_hub.core.config import Config
    from gnom_hub.db.state_repo import SQLiteStateRepository
    proj = SQLiteStateRepository().get_active_project() or "default"
    wd = os.path.abspath(os.path.join(str(WORKSPACE_DIR), proj))
    if not Config.ENABLE_WORKSPACE_SANDBOX:
        import sys
        py_exec = sys.executable or "python3"
        return subprocess.run([py_exec, code_path], capture_output=True, text=True, timeout=timeout, cwd=wd)
    if is_docker_running():
        cmd = ["docker", "run", "--rm", f"--network={net}", "--memory=512m",
               "-v", f"{wd}:/workspace:ro",
               "--tmpfs", "/tmp:size=100m",
               "-w", "/workspace", "gnom-playwright:latest", "python3", code_path]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    import sys
    py_exec = sys.executable or "python3"
    return run_sandboxed([py_exec, code_path], wd, timeout=timeout)


