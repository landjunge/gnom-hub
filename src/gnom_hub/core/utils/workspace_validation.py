from pathlib import Path

from gnom_hub.core.config import Config
from gnom_hub.core.exceptions import ValidationError


def validate_workspace_path(path: str | Path) -> Path:
    """Zentrale Funktion zur Workspace-Pfadvalidierung."""
    if isinstance(path, str):
        path = Path(path)
    
    if not path.is_absolute():
        path = Config.workspace_dir() / path

    # Sicherheitsprüfung: resolve() ZUERST, dann relative_to() Check
    workspace_root = Config.workspace_dir().resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(workspace_root)
    except ValueError as e:
        raise ValidationError(f"Ungültiger Pfad: {path} liegt außerhalb des Workspace-Verzeichnisses") from e
    
    if not resolved.exists():
        raise ValidationError(f"Pfad existiert nicht: {resolved}")
    
    return resolved
