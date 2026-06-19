# team_velocity.py — Track agent utilization and identify pipeline bottlenecks
from typing import Dict

class VelocityMetric:
    def __init__(
        self,
        jobs_completed_per_day: int,
        avg_duration_per_job: float,
        agent_utilization: Dict[str, float],
        critical_path_overhead: float
    ):
        self.jobs_completed_per_day = jobs_completed_per_day
        self.avg_duration_per_job = avg_duration_per_job
        self.agent_utilization = agent_utilization
        self.critical_path_overhead = critical_path_overhead

    def identify_bottleneck(self) -> str:
        if self.critical_path_overhead > 0.3:
            return "Parallelization issue — jobs wait for predecessors"
        if self.agent_utilization.get("WriterAG", 1.0) < 0.2:
            return "WriterAG underutilized — consider reassigning tasks"
        return "No bottleneck detected"
