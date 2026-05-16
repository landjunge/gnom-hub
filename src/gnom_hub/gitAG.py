import subprocess
from pathlib import Path

def init_if_needed(agent_path: str = "."):
    """Initialisiert Git-Repo falls noch keins da ist."""
    if not (Path(agent_path) / ".git").exists():
        subprocess.run(["git", "init"], cwd=agent_path, capture_output=True)

def auto_commit(agent_path: str, message: str = "Auto-commit nach Self-Modification"):
    """Nach jedem Write/Self-Mod: commit."""
    init_if_needed(agent_path)
    subprocess.run(["git", "add", "."], cwd=agent_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=agent_path, capture_output=True)

def git_cmd(agent_path: str, command: str) -> str:
    """Führt beliebigen git-Befehl aus und gibt Output zurück."""
    init_if_needed(agent_path)
    try:
        result = subprocess.run(
            ["git"] + command.split(),
            cwd=Path(agent_path),
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip() + (result.stderr and f"\nERR: {result.stderr.strip()}" or "")
    except Exception as e:
        return f"❌ Git-Error: {str(e)}"
