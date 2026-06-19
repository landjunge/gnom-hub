# eo_formatter.py
import json
from gnom_hub.agents.explainability.eo_class import ExplainableOutput

class ExplainableOutputFormatter:
    @staticmethod
    def to_markdown(o: ExplainableOutput) -> str:
        srcs = ", ".join(f"{s['type']}:{s['id']}" for s in o.sources) if o.sources else "Keine"
        rc = " → ".join(o.reasoning_chain) if o.reasoning_chain else "Kein Pfad"
        alts = "\n".join(f"  • {a['answer']} ({a['score']*100:.0f}%) — {a['why_not']}" for a in o.alternatives) if o.alternatives else "  • Keine Alternativen"
        deg = f"\n**Abstufungs-Hinweis:** {o.degradation_note}\n" if o.degradation_note else ""
        return f"{o.answer}\n{deg}\n**Zuversicht:** {o.confidence*100:.0f}%\n**Reasoning:** {rc}\n**Quellen:** {srcs}\n**Ausführungszeit:** {o.execution_time_ms} ms\n\n**Alternativen:**\n{alts}"

    @staticmethod
    def to_json(o: ExplainableOutput) -> str:
        return json.dumps({
            "agent": o.agent, "task": o.task, "answer": o.answer, "confidence": o.confidence,
            "reasoning_chain": o.reasoning_chain, "sources": o.sources,
            "alternatives": o.alternatives, "execution_time_ms": o.execution_time_ms, "degradation_note": o.degradation_note
        })

    @staticmethod
    def to_html(o: ExplainableOutput) -> str:
        srcs = "".join(f"<span class='badge bg-secondary me-1'>{s['type']}:{s['id']}</span>" for s in o.sources) if o.sources else "Keine"
        rc = " &rarr; ".join(f"<span class='step'>{step}</span>" for step in o.reasoning_chain) if o.reasoning_chain else "Kein Pfad"
        alts_list = [f"<li><strong>{a['answer']}</strong> ({a['score']*100:.0f}%) &ndash; <em>{a['why_not']}</em></li>" for a in o.alternatives]
        alts = f"<ul>{''.join(alts_list)}</ul>" if alts_list else "<p>Keine Alternativen.</p>"
        deg = f"<div class='alert alert-warning'>{o.degradation_note}</div>" if o.degradation_note else ""
        return f'<div class="card explainable-output-card shadow-sm"><div class="card-body"><h5 class="card-title text-primary">Antwort von {o.agent}</h5><p class="card-text answer-text">{o.answer}</p>{deg}<hr/><div class="meta-section"><p><strong>Zuversicht:</strong> <span class="badge bg-success">{o.confidence*100:.0f}%</span></p><p><strong>Reasoning Chain:</strong> <span class="reasoning-flow">{rc}</span></p><p><strong>Quellen:</strong> {srcs}</p><p><strong>Ausführungszeit:</strong> <span class="text-muted">{o.execution_time_ms} ms</span></p></div><div class="alternatives-section mt-3"><h6>Alternativen:</h6>{alts}</div></div></div>'
