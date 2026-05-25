# project_planner.py — Critical path analysis and lookahead execution coordinator
import asyncio
from typing import List, Literal, Dict

class Step:
    def __init__(
        self,
        id: str,
        description: str,
        assigned_agent: str,
        depends_on: List[str],
        estimated_duration: int,
        criticality: Literal["blocker", "important", "nice_to_have"]
    ):
        self.id = id
        self.description = description
        self.assigned_agent = assigned_agent
        self.depends_on = depends_on
        self.estimated_duration = estimated_duration
        self.criticality = criticality

    def __repr__(self):
        return f"<Step id={self.id} agent={self.assigned_agent} duration={self.estimated_duration}>"

class ProjectPlan:
    def __init__(self, id: str, title: str, steps: List[Step]):
        self.id = id
        self.title = title
        self.steps = steps
        self.lookahead_prepped = set()
        self.executed_steps = set()

    def calculate_critical_path(self) -> List[Step]:
        """Calculates the critical path (longest duration path of dependent steps)."""
        if not self.steps:
            return []

        # Map steps by their ID for easy lookup
        step_map: Dict[str, Step] = {s.id: s for s in self.steps}

        # Memoization dictionary for storing (longest_duration, path_list)
        memo: Dict[str, tuple] = {}

        def get_longest_path(step_id: str) -> tuple:
            if step_id in memo:
                return memo[step_id]

            step = step_map[step_id]
            if not step.depends_on:
                res = (step.estimated_duration, [step])
                memo[step_id] = res
                return res

            max_dur = 0
            best_path = []
            for dep_id in step.depends_on:
                if dep_id in step_map:
                    dur, path = get_longest_path(dep_id)
                    if dur > max_dur:
                        max_dur = dur
                        best_path = path

            res = (max_dur + step.estimated_duration, best_path + [step])
            memo[step_id] = res
            return res

        # Find the overall longest path in the project
        max_total_dur = -1
        critical_path = []

        for step in self.steps:
            dur, path = get_longest_path(step.id)
            if dur > max_total_dur:
                max_total_dur = dur
                critical_path = path

        return critical_path

    def prepare_lookahead(self, step: Step):
        """Prepares subsequent steps (e.g. N+2 or child steps) in parallel."""
        critical_path = self.calculate_critical_path()
        try:
            idx = critical_path.index(step)
            # Lookahead N+2 step in the critical path
            if idx + 2 < len(critical_path):
                lookahead_step = critical_path[idx + 2]
                if lookahead_step.id not in self.lookahead_prepped:
                    self.lookahead_prepped.add(lookahead_step.id)
                    print(f"[Lookahead] Prepping subsequent step '{lookahead_step.id}' ({lookahead_step.description}) in parallel while executing '{step.id}'...")
        except ValueError:
            pass

    async def execute_step(self, step: Step):
        """Simulates step execution with logging and a small speed-adjusted sleep."""
        print(f"[Planner] Executing step '{step.id}' ({step.description}) assigned to {step.assigned_agent}...")
        # Scale sleep down for testing speed (1 duration unit = 10ms)
        await asyncio.sleep(step.estimated_duration * 0.01)
        self.executed_steps.add(step.id)
        print(f"[Planner] Completed step '{step.id}'.")

    async def execute_with_lookahead(self):
        # Critical path analysis: Wo sind die Bottlenecks?
        critical_path = self.calculate_critical_path()
        print(f"[Planner] Critical path identified: {[s.id for s in critical_path]}")
        
        # Execute steps topologically
        for step in self.steps:
            if step in critical_path:
                # Prep step N+2 parallel while step N executes
                self.prepare_lookahead(step)
            
            await self.execute_step(step)
