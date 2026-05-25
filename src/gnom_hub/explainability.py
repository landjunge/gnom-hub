# explainability.py — Render agent reasoning, alternatives, sources, and uncertainty
from typing import List

class ExplainableOutput:
    def __init__(
        self,
        primary_answer: str,
        confidence: float,
        reasoning_chain: List[str],
        alternatives: List[dict],
        sources: List[str],
        agent_uncertainty: str
    ):
        self.primary_answer = primary_answer
        self.confidence = confidence
        self.reasoning_chain = reasoning_chain
        self.alternatives = alternatives
        self.sources = sources
        self.agent_uncertainty = agent_uncertainty

    def render_for_user(self) -> str:
        # Build alternatives string dynamically to avoid Python f-string syntax error
        alts_list = []
        for alt in self.alternatives:
            score_pct = alt.get('score', 0.0) * 100
            alts_list.append(f"  • {alt.get('answer', '')} ({score_pct:.0f}%) — {alt.get('why_not', '')}")
        alts_str = "\n".join(alts_list)

        return f"""
        {self.primary_answer}
        
        **Zuversicht:** {self.confidence * 100:.0f}%
        **Reasoning:** {" → ".join(self.reasoning_chain)}
        **Quellen:** {", ".join(self.sources)}
        
        **Unsicherheiten:** {self.agent_uncertainty}
        **Alternativen:** 
{alts_str}
        """
