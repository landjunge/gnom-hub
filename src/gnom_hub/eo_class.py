# eo_class.py
from typing import List, Dict, Optional

class ExplainableOutput:
    def __init__(
        self, agent: str, task: str, answer: str = "", confidence: float = 0.0,
        reasoning_chain: List[str] = None, sources: List[Dict[str, str]] = None,
        alternatives: List[Dict] = None, execution_time_ms: int = 0,
        degradation_note: Optional[str] = None
    ):
        self.agent = agent
        self.task = task
        self.answer = answer
        self.confidence = confidence
        self.reasoning_chain = reasoning_chain or []
        self.sources = sources or []
        self.alternatives = alternatives or []
        self.execution_time_ms = execution_time_ms
        self.degradation_note = degradation_note
