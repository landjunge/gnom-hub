# explainability.py — DEPRECATED: Use eo_class.ExplainableOutput instead
#
# This module previously defined a separate ExplainableOutput class with
# different fields (primary_answer, agent_uncertainty). It has been removed
# to avoid confusion. The canonical class is in eo_class.py.
#
# For backward compatibility, re-export the canonical class:
from gnom_hub.agents.explainability.eo_class import ExplainableOutput

__all__ = ["ExplainableOutput"]
