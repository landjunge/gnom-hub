from pathlib import Path
from gnom_hub.core.config import Config
from .policy import WorkspacePolicy
from gnom_hub.core.exceptions import ValidationError


class FileVerifier:
    """Verantwortlich für die Überprüfung von Dateien und Pfaden."""

    def __init__(self):
        self.policy = WorkspacePolicy(Config.workspace_dir())

    def verify_path(self, path: str | Path) -> Path:
        """Überprüft einen Pfad auf Sicherheit und gibt den bereinigten Path zurück."""
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            path = Config.workspace_dir() / path

        return self.policy.validate_path(path)

    def verify_file_exists(self, path: str | Path) -> Path:
        """Prüft ob eine Datei existiert und gibt den validierten Pfad zurück."""
        validated_path = self.verify_path(path)
        
        if not validated_path.exists():
            raise ValidationError(f"Datei nicht gefunden: {validated_path}")
            
        if not validated_path.is_file():
            raise ValidationError(f"Pfad ist keine Datei: {validated_path}")
            
        return validated_path
