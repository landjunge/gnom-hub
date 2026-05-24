import os
from pathlib import Path
GNOM_HUB_HOME = Path(os.environ.get("GNOM_HUB_HOME", Path.home() / ".gnom-hub"))
DATA_DIR = GNOM_HUB_HOME / "data"
RUN_DIR = GNOM_HUB_HOME / "run"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(parents=True, exist_ok=True)

# Project root: two levels up from this file (src/gnom_hub/config.py → project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = PROJECT_ROOT / "gnom_workspace"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CONFIG_DIR = PROJECT_ROOT / "config"
TOKENS_FILE = CONFIG_DIR / ".gnom-hub-tokens.json"
