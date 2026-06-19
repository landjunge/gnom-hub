from pathlib import Path
from gnom_hub.core.utils.workspace_rules import validate_path_sandbox
from gnom_hub.core.exceptions import WorkspaceAccessDeniedError


class WorkspacePolicy:
    """Zentrale Policy für Workspace-Zugriffsregeln."""

    def __init__(self, base_workspace_path: Path):
        self.base_workspace_path = base_workspace_path.resolve()

    def validate_path(self, target_path: Path) -> Path:
        """Prüft ob der Pfad erlaubt ist und gibt den absoluten Pfad zurück."""
        validated = validate_path_sandbox(target_path, self.base_workspace_path)
        
        if not validated.is_allowed:
            raise WorkspaceAccessDeniedError(f"Zugriff auf Pfad außerhalb des Workspace verweigert: {target_path}")
        
        return validated.path.resolve()
