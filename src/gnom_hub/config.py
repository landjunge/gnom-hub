import os
from pathlib import Path

GNOM_HUB_HOME = Path(os.environ.get("GNOM_HUB_HOME", Path.home() / ".gnom-hub"))
DATA_DIR = GNOM_HUB_HOME / "data"
RUN_DIR = GNOM_HUB_HOME / "run"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(parents=True, exist_ok=True)
