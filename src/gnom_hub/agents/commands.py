from uuid import UUID
from gnom_hub.agents.entities import Agent
from gnom_hub.db.agent_repo import AgentRepository
from gnom_hub.infrastructure.process.process_manager import ProcessManager
from gnom_hub.core.exceptions import ValidationError

class AgentCommands:
    """Commands für Schreiboperationen auf Agenten (Start, Stop, Register)."""

    def __init__(self, agent_repo: AgentRepository, process_manager: ProcessManager):
        self.agent_repo = agent_repo
        self.process_manager = process_manager

    async def start_agent(self, agent_id: UUID) -> Agent:
        """Startet einen Agenten."""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent: raise ValidationError(f"Agent mit ID {agent_id} nicht gefunden")
        if not agent.is_running():
            pid = await self.process_manager.start_agent_process(agent)
            agent.mark_as_running(pid)
            await self.agent_repo.save(agent)
        return agent

    async def stop_agent(self, agent_id: UUID) -> Agent:
        """Stoppt einen Agenten."""
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent: raise ValidationError(f"Agent mit ID {agent_id} nicht gefunden")
        if agent.is_running():
            await self.process_manager.stop_agent_process(agent.pid)
            agent.mark_as_stopped()
            await self.agent_repo.save(agent)
        return agent

    async def register_agent(self, name: str, model: str) -> Agent:
        """Registriert einen neuen Agenten."""
        return await self.agent_repo.save(Agent(name=name, model=model))
