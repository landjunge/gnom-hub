class GnomHubError(Exception):
    """Basis-Exception für alle Gnom-Hub Fehler."""

class EntityNotFoundError(GnomHubError):
    """Wird geworfen, wenn eine Entität nicht gefunden wurde."""

class ValidationError(GnomHubError):
    """Wird bei ungültigen Eingaben oder Zuständen geworfen."""

class WorkspaceAccessDeniedError(GnomHubError):
    """Wird geworfen, wenn der Zugriff auf einen Workspace-Pfad verweigert wird."""

class LLMProviderError(GnomHubError):
    """Fehler bei der Kommunikation mit einem LLM-Provider."""

class AgentNotRunningError(GnomHubError):
    """Wird geworfen, wenn ein Agent nicht läuft, obwohl er sollte."""
