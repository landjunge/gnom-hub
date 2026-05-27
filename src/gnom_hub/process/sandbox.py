# sandbox.py — Hybrid Docker & macOS Sandbox Executor
import subprocess, os
from gnom_hub.core.config import WORKSPACE_DIR
from gnom_hub.process.sandbox_exec import run_sandboxed

def is_docker_running():
    try: return subprocess.run(["docker", "ps"], capture_output=True, timeout=2).returncode == 0
    except: return False

def run_in_sandbox(command: str, agent=None, timeout: int = 30):
    if agent:
        from gnom_hub.gatekeeper import verify_cmd
        if not verify_cmd(agent, command): raise PermissionError("Befehlsausführung verweigert.")
    wd = os.path.abspath(str(WORKSPACE_DIR))
    if is_docker_running():
        cmd = ["docker", "run", "--rm", "--network=none", "--memory=512m", "--cpus=1", "-w", "/workspace", "-v", f"{wd}:/workspace:rw", "python:3.11-slim", "bash", "-c", command]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return subprocess.CompletedProcess(args=cmd, returncode=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except Exception: pass
    return run_sandboxed(command, wd, timeout=timeout)

def run_browser_in_sandbox(code_path: str, net: str, timeout: int = 45):
    wd = os.path.abspath(str(WORKSPACE_DIR))
    cmd = ["docker", "run", "--rm", f"--network={net}", "--memory=512m", "-v", f"{wd}:/workspace:rw", "-w", "/workspace", "mcr.microsoft.com/playwright/python:v1.43.0-jammy", "python3", code_path]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

