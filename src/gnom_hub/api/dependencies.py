from gnom_hub.infrastructure.admin.service import AdminService as AS

# AdminService is the only DI dependency actually used at runtime.
# The old OOP layer (AgentCommands, AgentQueries, ChatService, SendMessageUseCase,
# BrainstormUseCase, LLMOrchestrator, ProcessManager) was never wired up properly
# and has been removed.

def get_admin_service(): return AS()


def get_agent_commands():
    """Dependency stub for agent commands."""
    return None


def get_agent_queries():
    """Dependency stub for agent queries."""
    return None
