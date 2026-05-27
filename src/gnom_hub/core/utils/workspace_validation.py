from pathlib import Path
from ...core.config import Config
from ...common.exceptions import ValidationError
from ...domain.workspace.entities import WorkspacePath


def validate_workspace_path(path: str | Path) -> Path:
    """Zentrale Funktion zur Workspace-Pfadvalidierung."""
    if isinstance(path, str):
        path = Path(path)
    
    if not path.is_absolute():
        path = Config.WORKSPACE_DIR / path
    
    if not path.exists():
        raise ValidationError(f"Pfad existiert nicht: {path}")
    
    # Grundlegende Sicherheitsprüfung
    if ".." in str(path):
        raise ValidationError("Ungültiger Pfad: Verwendung von '..' nicht erlaubt")
    
    return path.resolve()
