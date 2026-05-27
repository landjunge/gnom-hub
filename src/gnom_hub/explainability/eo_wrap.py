# eo_wrap.py — Wraps raw LLM response into ExplainableOutput
from gnom_hub.explainability.eo_builder import ExplainableOutputBuilder
from gnom_hub.explainability.eo_class import ExplainableOutput
from gnom_hub.explainability.eo_store import ExplainableOutputStore

_store = None

def _get_store():
    global _store
    if _store is None:
        _store = ExplainableOutputStore()
    return _store

def wrap_response(answer, agent, task, lat_ms, provider="", model="", fallback=False):
    """Build + persist ExplainableOutput from raw LLM answer."""
    b = ExplainableOutputBuilder(agent or "unknown", task[:120])
    b.set_answer(answer).set_execution_time(int(lat_ms))
    b.add_reasoning(f"Anfrage empfangen: {task[:60]}")
    b.add_reasoning(f"Router → {provider}:{model}")
    b.add_reasoning("Antwort generiert")
    if provider:
        b.add_source(model, provider)
    b.set_confidence(0.5 if fallback else 0.75)
    if fallback:
        b.output.degradation_note = "Fallback-Provider verwendet"
    eo = b.build()
    _persist(eo)
    return eo

def wrap_error(message, agent="system", task=""):
    """Build ExplainableOutput for error/offline cases."""
    eo = ExplainableOutput(agent, task, answer=message, confidence=0.0)
    eo.reasoning_chain = ["Alle Provider fehlgeschlagen"]
    eo.degradation_note = "Kein Provider verfügbar"
    return eo

def _persist(eo):
    try: _get_store().store(eo)
    except Exception: pass
