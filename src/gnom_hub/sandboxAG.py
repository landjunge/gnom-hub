import subprocess
import time
from pathlib import Path

ALLOWED_CMDS = {"ls", "cat", "echo", "python", "pip", "git", "grep", "find"}  # erweiterbar
ALLOWED_DIRS = {Path("."), Path("/tmp/gnom_sandbox")}
TIMEOUT_SEC = 30

def safe_run_command(cmd: str, agent_id: str) -> str:
    """Führt Command aus – nur erlaubt, nur in Sandbox, mit Timeout."""
    parts = cmd.strip().split()
    if not parts or parts[0] not in ALLOWED_CMDS:
        return f"🚫 Sandbox blocked: {parts[0]} nicht erlaubt!"

    # Nur in erlaubten Verzeichnissen
    cwd = Path.cwd()
    if not any(cwd.resolve().is_relative_to(d.resolve()) for d in ALLOWED_DIRS):
        return "🚫 Sandbox blocked: Falsches Verzeichnis!"

    try:
        result = subprocess.run(
            cmd,
            shell=False,  # kein Shell-Injection
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
            cwd=cwd
        )
        log = f"[{agent_id}] {cmd} → {result.returncode}"
        Path(".backups/sandbox.log").open("a").write(f"{time.time()} | {log}\n")
        return result.stdout.strip() + (result.stderr.strip() and f"\nERR: {result.stderr}")
    except subprocess.TimeoutExpired:
        return "⏰ Sandbox timeout – Command zu langsam!"
    except Exception as e:
        return f"❌ Sandbox error: {str(e)}"
