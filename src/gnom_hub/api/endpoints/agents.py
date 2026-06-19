from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from gnom_hub.api.dependencies import get_agent_commands, get_agent_queries

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/")
async def list_agents(queries=Depends(get_agent_queries)):
    """Gibt alle Agenten zurück."""
    return await queries.list_agents()

@router.get("/{agent_id}")
async def get_agent(agent_id: UUID, queries=Depends(get_agent_queries)):
    """Gibt einen einzelnen Agenten zurück."""
    try:
        return await queries.get_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/register")
async def register_agent(name: str, model: str, commands=Depends(get_agent_commands)):
    """Registriert einen neuen Agenten."""
    return await commands.register_agent(name, model)

@router.post("/{agent_id}/start")
async def start_agent(agent_id: UUID, commands=Depends(get_agent_commands)):
    """Startet einen Agenten."""
    try:
        return await commands.start_agent(agent_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: UUID, commands=Depends(get_agent_commands)):
    """Stoppt einen Agenten."""
    try:
        return await commands.stop_agent(agent_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
