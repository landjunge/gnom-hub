# adaptive_decomposition.py — Adaptive task decomposition and execution routing
import asyncio
import json
import re
from typing import List, Dict
from gnom_hub.infrastructure.router.router import ask_router
from gnom_hub.infrastructure.monitoring import get_agent_metrics

class Route:
    def __init__(self, subtasks: List[str], agents: List[str], duration: float, cost: float):
        self.subtasks = subtasks
        self.agents = agents
        self.duration = duration
        self.cost = cost

    def __repr__(self):
        return f"<Route agents={self.agents} duration={self.duration:.1f}s cost=${self.cost:.2f}>"

class RouteOptimizer:
    def pick_cheapest_route(self, task: str, capacities: Dict[str, Dict], complexity: int) -> Route:
        # We define three standard fallback routing strategies based on task characteristics
        # Strategy A: Parallel (e.g. WriterAG + CoderAG)
        # Strategy B: Serial (e.g. WriterAG -> EditorAG)
        # Strategy C: Single Agent (GeneralAG)

        # Default agent pricing / billing rate per second (simulated)
        rates = {
            "coderag": 0.05,
            "writerag": 0.03,
            "editorag": 0.025,
            "researcherag": 0.03,
            "generalag": 0.08
        }

        # Calculate estimated durations from capacities (avg_time_ms converted to seconds)
        # Fallback to standard durations if no metrics exist yet
        def get_dur(agent: str, default: float) -> float:
            m = capacities.get(agent.lower(), {})
            avg_ms = m.get("last_response_time", 0.0)
            if avg_ms > 0.0:
                return (avg_ms / 1000.0) * (1.0 + m.get("error_rate", 0.0))
            return default * (1.0 + (complexity / 10.0))

        dur_coder = get_dur("coderag", 25.0)
        dur_writer = get_dur("writerag", 15.0)
        dur_editor = get_dur("editorag", 10.0)
        dur_researcher = get_dur("researcherag", 12.0)
        dur_general = get_dur("generalag", 40.0)

        # Evaluate routes
        # Route A: Parallel (e.g., Coder writes code, Writer writes docs concurrently)
        # total duration = max of parallel branches
        dur_a = max(dur_writer, dur_coder)
        cost_a = (dur_writer * rates["writerag"]) + (dur_coder * rates["coderag"])
        route_a = Route(
            subtasks=["Implement core functionality", "Write project documentation"],
            agents=["CoderAG", "WriterAG"],
            duration=dur_a,
            cost=cost_a
        )

        # Route B: Serial (Writer writes draft, Editor refines it)
        # total duration = sum of durations
        dur_b = dur_writer + dur_editor
        cost_b = (dur_writer * rates["writerag"]) + (dur_editor * rates["editorag"])
        route_b = Route(
            subtasks=["Draft outline and content", "Proofread and polish texts"],
            agents=["WriterAG", "EditorAG"],
            duration=dur_b,
            cost=cost_b
        )

        # Route C: Single General agent (GeneralAG manages everything)
        dur_c = dur_general
        cost_c = dur_general * rates["generalag"]
        route_c = Route(
            subtasks=["Analyze request and execute task end-to-end"],
            agents=["GeneralAG"],
            duration=dur_c,
            cost=cost_c
        )

        # Decide route based on task text heuristics and complexity
        task_lower = task.lower()
        if "code" in task_lower or "landingpage" in task_lower:
            # Code tasks benefit most from parallel code + docs (Route A)
            return route_a
        elif "blog" in task_lower or "text" in task_lower or "schreib" in task_lower:
            # Text drafting tasks benefit most from serial draft + review (Route B)
            return route_b
        else:
            # Complex, generic tasks default to GeneralAG or Route A/B based on complexity
            if complexity > 7:
                # Highly complex tasks benefit from parallelism
                return route_a
            else:
                return route_c

optimizer = RouteOptimizer()

async def estimate_complexity(task: str) -> int:
    """Invokes GeneralAG to estimate the complexity of the task (1-10)."""
    prompt = (
        f"Schätze die Komplexität dieser Aufgabe auf einer Skala von 1 bis 10 ein.\n"
        f"Aufgabe: {task}\n"
        f"Antworte NUR mit einer einzigen Zahl zwischen 1 und 10."
    )
    import functools
    loop = asyncio.get_running_loop()
    res_obj = await loop.run_in_executor(
        None,
        functools.partial(ask_router, prompt, sys="Du bist ein präziser Komplexitäts-Bewerter.", agent_name="GeneralAG")
    )
    res = res_obj.content
    
    # Extract number
    match = re.search(r'\b([1-9]|10)\b', res)
    if match:
        return int(match.group(1))
    return 5  # Fallback

async def get_agent_capacities() -> dict:
    """Measures agent response times and error rates based on historical metrics."""
    metrics = get_agent_metrics()
    capacities = {}
    for agent, m in metrics.items():
        capacities[agent] = {
            "last_response_time": m.get("avg_time_ms", 0.0),
            "error_rate": 1.0 - m.get("success_rate", 1.0)
        }
    return capacities

async def decompose_job(task: str) -> dict:
    # 1. Task-Komplexität schätzen
    complexity = await estimate_complexity(task)
    
    # 2. Agent-Kapazität messen
    capacities = await get_agent_capacities()
    
    # 3. Optimal-Route berechnen
    route = optimizer.pick_cheapest_route(task, capacities, complexity)
    
    return {
        "subtasks": route.subtasks,
        "assigned_agents": route.agents,
        "expected_duration": route.duration,
        "cost_estimate": route.cost
    }
