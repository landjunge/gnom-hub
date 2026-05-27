# graceful_fallback.py — Graceful agent degradation and backup execution
import asyncio
import logging
import re
from typing import Dict, Union
from gnom_hub.router import ask_router
from gnom_hub.monitoring.monitoring import get_agent_metrics

logger = logging.getLogger("fallback")

class AgentUnavailableError(Exception):
    """Raised when an agent is offline or fails to respond."""
    pass

class AllAgentsFailedError(Exception):
    """Raised when all fallback strategies fail."""
    pass

class FallbackResult:
    def __init__(self, completion: str):
        self.completion = completion
        self.degradation_note = None

    def __repr__(self):
        return f"<FallbackResult note={self.degradation_note} content_length={len(self.completion)}>"

class FallbackAgent:
    def __init__(self, name: str):
        self.name = name

    def is_online(self) -> bool:
        # Resolve clean name (e.g. "GeneralAG (pseudocode)" -> "generalag")
        clean_name = self.name.split("(")[0].strip().lower()
        metrics = get_agent_metrics()
        agent_data = metrics.get(clean_name)
        if agent_data:
            return agent_data.get("status") == "online"
        # Default fallback for standard system agents is online
        return clean_name in ["generalag", "soulag"]

    async def execute(self, task: str) -> FallbackResult:
        # Check if agent is online in database
        if not self.is_online():
            raise AgentUnavailableError(f"Agent {self.name} is offline.")

        clean_name = self.name.split("(")[0].strip()
        
        # Execute the task
        prompt = f"Führe diese Aufgabe aus: {task}"
        eo = await asyncio.to_thread(ask_router, prompt, sys=f"Du repräsentierst {self.name}.", agent_name=clean_name)
        
        if eo.content.startswith("[ROUTER-FEHLER]"):
            raise AgentUnavailableError(f"Agent {self.name} failed to route request.")

        return FallbackResult(eo.content)

    def __repr__(self):
        return self.name

async def estimate_quality(fallback_agent: Union[str, FallbackAgent], task: str) -> float:
    """Estimates the confidence score (0.0 - 1.0) of a fallback agent executing the task."""
    agent_name = fallback_agent.name if isinstance(fallback_agent, FallbackAgent) else str(fallback_agent)
    prompt = (
        f"Schätze die Qualität (0.0 bis 1.0) ein, wenn {agent_name} diese Aufgabe ausführt: {task}\n"
        f"Antworte NUR mit einer Fließkommazahl zwischen 0.0 und 1.0."
    )
    res = (await asyncio.to_thread(ask_router, prompt, sys="Du bist ein präziser Qualitäts-Schätzer.", agent_name="GeneralAG")).content
    match = re.search(r'\b(0\.\d+|1\.0|0)\b', res)
    if match:
        return float(match.group(1))
    return 0.8  # Fallback quality

async def execute_with_fallback(agent: Union[str, FallbackAgent], task: str) -> FallbackResult:
    # Convert string agent to FallbackAgent wrapper
    main_agent = FallbackAgent(agent) if isinstance(agent, str) else agent
    agent_name = main_agent.name

    try:
        return await main_agent.execute(task)
    except AgentUnavailableError:
        logger.warning(f"{agent_name} unavailable, trying fallback")
        print(f"[Fallback] {agent_name} unavailable, trying fallback...")
        
        fallback_options = {
            "CoderAG": ["GeneralAG (pseudocode)", "WriterAG (step-by-step)"],
            "WriterAG": ["GeneralAG (rough draft)", "EditorAG (expand outline)"],
        }
        
        options = fallback_options.get(agent_name, ["GeneralAG"])
        
        for fallback_name in options:
            fallback_agent = FallbackAgent(fallback_name)
            confidence = await estimate_quality(fallback_agent, task)
            
            if confidence > 0.7:
                print(f"[Fallback] Selected fallback {fallback_name} with confidence {confidence:.2f}")
                result = await fallback_agent.execute(task)
                result.degradation_note = f"Note: {agent_name} was unavailable, {fallback_name} handled this instead."
                return result
        
        raise AllAgentsFailedError(f"No fallback available for {task}")
