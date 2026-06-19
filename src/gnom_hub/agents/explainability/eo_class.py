# eo_class.py — ExplainableOutput: Einzige Antwort-Struktur der Pipeline
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

    @property
    def content(self) -> str:
        """Roher LLM-Antworttext für interne/machine-parsed Calls."""
        import re
        if not self.answer:
            return ""
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', self.answer)
        return cleaned.strip()

    def __str__(self) -> str:
        """Formatiertes Markdown mit Reasoning Chain, Confidence, Quellen."""
        from gnom_hub.agents.explainability.eo_formatter import ExplainableOutputFormatter
        return ExplainableOutputFormatter.to_markdown(self)

    def __repr__(self) -> str:
        return f"<EO agent={self.agent} conf={self.confidence:.0%}>"
