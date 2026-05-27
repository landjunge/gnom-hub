from dataclasses import dataclass
from pathlib import Path

@dataclass
class WorkspacePath:
    path: Path
    is_allowed: bool
