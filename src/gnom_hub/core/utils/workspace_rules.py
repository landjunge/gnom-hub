from pathlib import Path
from .entities import WorkspacePath

def is_path_allowed(base_path: Path, target_path: Path) -> bool:
    """Prüft, ob ein Pfad innerhalb des erlaubten Workspace liegt."""
    try:
        target_path.resolve().relative_to(base_path.resolve())
        return True
    except ValueError:
        return False


def validate_path_sandbox(path: Path, allowed_base: Path) -> WorkspacePath:
    """Erstellt ein WorkspacePath-Objekt mit Validierung."""
    is_allowed = is_path_allowed(allowed_base, path)
    return WorkspacePath(path=path, is_allowed=is_allowed)
