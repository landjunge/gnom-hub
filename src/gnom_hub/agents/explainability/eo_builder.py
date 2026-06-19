# eo_builder.py
from gnom_hub.agents.explainability.eo_class import ExplainableOutput

class ExplainableOutputBuilder:
    def __init__(self, agent: str, task: str):
        self.output = ExplainableOutput(agent, task)
    def set_answer(self, answer: str):
        self.output.answer = answer
        return self
    def set_confidence(self, confidence: float):
        self.output.confidence = confidence
        return self
    def add_reasoning(self, step: str):
        self.output.reasoning_chain.append(step)
        return self
    def add_source(self, source_id: str, source_type: str):
        self.output.sources.append({"id": source_id, "type": source_type})
        return self
    def add_alternative(self, answer: str, score: float, why_not: str):
        self.output.alternatives.append({"answer": answer, "score": score, "why_not": why_not})
        return self
    def set_execution_time(self, ms: int):
        self.output.execution_time_ms = ms
        return self
    def build(self) -> ExplainableOutput:
        return self.output
