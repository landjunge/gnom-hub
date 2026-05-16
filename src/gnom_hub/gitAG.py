import subprocess
from pathlib import Path

def init_if_needed(agent_path: str = "."):
    if not (Path(agent_path) / ".git").exists():
        subprocess.run(["git", "init"], cwd=agent_path, capture_output=True)

def auto_commit(agent_path: str, message: str = "Auto-commit nach Self-Modification"):
    init_if_needed(agent_path)
    if not subprocess.run(["git", "status", "--porcelain"], cwd=agent_path, capture_output=True).stdout: return
    subprocess.run(["git", "add", "."], cwd=agent_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=agent_path, capture_output=True)

def setup_git_hooks():
    """Installiert post-commit Hook, der Checkpointer triggert + alle Agenten committet."""
    hook_dir = Path(".git/hooks")
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hook_dir / "post-commit"
    hook_content = '''#!/bin/sh
export PYTHONPATH="src:$PYTHONPATH"
python -c "
from gnom_hub.db import get_db
from gnom_hub.swarm_checkpoint import save_swarm_checkpoint
save_swarm_checkpoint(get_db('agents'), get_db('memory'))
print('✅ Gnom-Hub Hook: Checkpoint created!')
"
'''
    hook_path.write_text(hook_content)
    hook_path.chmod(0o755)

def git_cmd(agent_path: str, command: str) -> str:
    init_if_needed(agent_path)
    try:
        result = subprocess.run(["git"] + command.split(), cwd=Path(agent_path), capture_output=True, text=True, timeout=10)
        return result.stdout.strip() + (result.stderr and f"\nERR: {result.stderr.strip()}" or "")
    except Exception as e:
        return f"❌ Git-Error: {str(e)}"
