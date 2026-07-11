"""TKG Brain Demo — Sichtbar machen dass das Gehirn funktioniert.

Schreibt eine HTML-Datei mit Mermaid-Graph-Visualisierung + Query-Traversal-Result.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent / "src"))

from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation


def build_demo_brain():
    """Baut einen Demo-TKG-Graph: Gnom-Hub-Eigenheiten + deren Beziehungen."""
    tmpdir = tempfile.mkdtemp(prefix="tkg_demo_")
    db_path = f"{tmpdir}/brain.kuzu"
    db = KuzuDBBackend(db_path)

    now = time.time()

    # ── Entities: Kernkonzepte des Gnom-Hub ──
    entities = [
        Entity(id="e_faiss_break", name="FAISS_ABI_BREAK", type="bug",
               importance=0.9, last_seen=now,
               properties={"severity": "critical", "first_seen": "2026-06-25"}),
        Entity(id="e_numpy_pin", name="numpy_pin_PR", type="code_change",
               importance=0.85, last_seen=now,
               properties={"pr_url": "https://github.com/...", "merged": "2026-06-27"}),
        Entity(id="e_tkg", name="TKG_Phase0", type="concept",
               importance=0.95, last_seen=now,
               properties={"phase": "0", "backend": "KuzuDB"}),
        Entity(id="e_routing", name="Deterministic_Routing", type="concept",
               importance=0.7, last_seen=now,
               properties={"stages": 3}),
        Entity(id="e_soulag", name="SoulAG", type="agent",
               importance=0.9, last_seen=now,
               properties={"role": "sovereign"}),
        Entity(id="e_user", name="User", type="person",
               importance=0.95, last_seen=now,
               properties={"interaction_count": 47}),
    ]
    for e in entities:
        db.upsert_entity(e)

    # ── Facts: Was ist passiert ──
    facts = [
        Fact(id="f_break",
             text="FAISS-ABI-Bruch in numpy 2.2.6 verursachte Hub-Crashes beim SentenceTransformer-Init.",
             embedding=np.random.rand(384), importance=0.9, valid_at=now-7*86400,
             layer="warm"),
        Fact(id="f_pin",
             text="pyproject.toml pin auf numpy<2.0,<5.0 fixte den FAISS-ABI-Konflikt.",
             embedding=np.random.rand(384), importance=0.85, valid_at=now-5*86400,
             layer="warm"),
        Fact(id="f_tkg_design",
             text="TKG-Phase-0 nutzt KuzuDB als embedded Graph-Backend mit HNSW-Vector-Index.",
             embedding=np.random.rand(384), importance=0.95, valid_at=now-2*86400,
             layer="warm"),
        Fact(id="f_tkg_test",
             text="10/10 TKG-Tests grün: bitemporal, vector-search, mention-roundtrip.",
             embedding=np.random.rand(384), importance=0.9, valid_at=now,
             layer="warm"),
    ]
    for f in facts:
        db.upsert_fact(f)

    # ── Relations: Wie hängt das zusammen ──
    relations = [
        # Bug → Fix
        Relation(from_id="f_pin", to_id="f_break", predicate="fixed_in",
                 valid_at=now-5*86400),
        # TKG Concept nutzt FAISS-Lessons
        Relation(from_id="f_tkg_design", to_id="f_break", predicate="learned_from",
                 valid_at=now-1*86400),
        Relation(from_id="f_tkg_design", to_id="f_pin", predicate="builds_on",
                 valid_at=now-1*86400),
        # Test-Result bestätigt Design
        Relation(from_id="f_tkg_test", to_id="f_tkg_design", predicate="validates",
                 valid_at=now),
    ]
    for r in relations:
        db.add_relation(r)

    # ── Mentions: Welche Entities werden in welchen Facts erwähnt ──
    mentions = [
        Mention(fact_id="f_break", entity_id="e_faiss_break", confidence=1.0),
        Mention(fact_id="f_break", entity_id="e_soulag", confidence=0.5),
        Mention(fact_id="f_pin", entity_id="e_numpy_pin", confidence=1.0),
        Mention(fact_id="f_pin", entity_id="e_faiss_break", confidence=0.9),
        Mention(fact_id="f_tkg_design", entity_id="e_tkg", confidence=1.0),
        Mention(fact_id="f_tkg_test", entity_id="e_tkg", confidence=1.0),
        Mention(fact_id="f_tkg_test", entity_id="e_user", confidence=0.3),
    ]
    for m in mentions:
        db.add_mention(m)

    return db, entities, facts, relations, mentions


def render_mermaid(entities, facts, relations, mentions) -> str:
    """Rendert den TKG als Mermaid-Graph."""
    lines = ["graph TD"]

    # Style für Entity-Typen
    type_colors = {
        "bug": "#ff6b6b",
        "code_change": "#4ecdc4",
        "concept": "#95e1d3",
        "agent": "#c9b1ff",
        "person": "#ffd93d",
    }

    # Entities als Knoten
    for e in entities:
        color = type_colors.get(e.type, "#999")
        label = f"{e.name}<br/><sub>{e.type} · imp={e.importance:.1f}</sub>"
        lines.append(f'    {e.id}["{label}"]')
        lines.append(f'    style {e.id} fill:{color},stroke:#333,stroke-width:2px')

    # Facts als Boxen (subgraph)
    lines.append("    subgraph FACTS")
    for f in facts:
        preview = f.text[:50] + "..." if len(f.text) > 50 else f.text
        lines.append(f'        {f.id}[/"{preview}"/]')
    lines.append("    end")

    # Relations als Edges
    rel_labels = {
        "fixed_in": "✅ fixed",
        "learned_from": "📚 learned",
        "builds_on": "🔨 builds on",
        "validates": "✓ validates",
    }
    for r in relations:
        label = rel_labels.get(r.predicate, r.predicate)
        lines.append(f'    {r.from_id} -->|{label}| {r.to_id}')

    # Mentions als punktierte Edges
    for m in mentions:
        lines.append(f'    {m.fact_id} -. mentions .-> {m.entity_id}')

    return "\n".join(lines)


def render_html(entities, facts, relations, mentions, query_result, output_path):
    """Rendert die finale HTML-Datei mit Mermaid-Graph + Stats + Query-Result."""
    mermaid_code = render_mermaid(entities, facts, relations, mentions)

    entities_html = "\n".join(
        f'<li><b>{e.name}</b> <span class="type type-{e.type}">{e.type}</span> · importance {e.importance:.2f}</li>'
        for e in entities
    )
    facts_html = "\n".join(
        f'<li><b>{f.id}</b>: {f.text}</li>'
        for f in facts
    )
    relations_html = "\n".join(
        f'<li><code>{r.from_id}</code> --<b>{r.predicate}</b>--> <code>{r.to_id}</code></li>'
        for r in relations
    )
    query_html = f"""
    <div class="query-result">
      <p><b>Query:</b> <code>{query_result['query']}</code></p>
      <p><b>Treffer:</b> {query_result['count']} Facts (Top {query_result['top_k']})</p>
      <ol>
        {''.join(f'<li><b>{f.id}</b> (imp={f.importance:.2f}): {f.text[:120]}...</li>' for f in query_result['results'])}
      </ol>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Gnom-Hub Brain Demo — TKG Working Memory</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #0e0f13; color: #e7e9ee; margin: 0; padding: 24px; }}
  h1 {{ color: #00e5ff; font-size: 1.8em; margin-bottom: 8px; }}
  h2 {{ color: #00e5ff; font-size: 1.2em; margin-top: 28px; border-bottom: 1px solid #2a2c33; padding-bottom: 4px; }}
  .subtitle {{ color: #888; margin-bottom: 24px; }}
  .mermaid {{ background: #1a1c22; padding: 20px; border-radius: 8px; margin: 20px 0; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }}
  .stat {{ background: #1a1c22; padding: 12px 16px; border-radius: 8px; border: 1px solid #2a2c33; }}
  .stat .num {{ font-size: 1.8em; font-weight: 700; color: #00e5ff; }}
  .stat .label {{ color: #888; font-size: 0.85em; }}
  ul {{ list-style: none; padding-left: 0; }}
  li {{ padding: 8px 12px; margin: 4px 0; background: #1a1c22; border-radius: 4px; border-left: 3px solid #00e5ff; }}
  code {{ background: #2a2c33; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
  .type {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; margin-left: 6px; }}
  .type-bug {{ background: #ff6b6b22; color: #ff6b6b; }}
  .type-code_change {{ background: #4ecdc422; color: #4ecdc4; }}
  .type-concept {{ background: #95e1d322; color: #95e1d3; }}
  .type-agent {{ background: #c9b1ff22; color: #c9b1ff; }}
  .type-person {{ background: #ffd93d22; color: #ffd93d; }}
  .query-result {{ background: #1a1c22; padding: 16px; border-radius: 8px; border: 2px solid #00e5ff; margin: 16px 0; }}
</style>
</head>
<body>
<h1>🧠 Gnom-Hub Brain Demo</h1>
<p class="subtitle">Temporal Knowledge Graph (TKG) — Phase 0 working — KuzuDB embedded backend</p>

<div class="stats">
  <div class="stat"><div class="num">{len(entities)}</div><div class="label">Entities</div></div>
  <div class="stat"><div class="num">{len(facts)}</div><div class="label">Facts</div></div>
  <div class="stat"><div class="num">{len(relations)}</div><div class="label">Relations</div></div>
  <div class="stat"><div class="num">{len(mentions)}</div><div class="label">Mentions</div></div>
</div>

<h2>📊 Graph Visualization</h2>
<div class="mermaid">
{mermaid_code}
</div>

<h2>🔍 Demo-Query: "Was passierte mit dem FAISS-Bug?"</h2>
{query_html}

<h2>📋 Entities (Detail)</h2>
<ul>{entities_html}</ul>

<h2>💬 Facts (Detail)</h2>
<ul>{facts_html}</ul>

<h2>🔗 Relations (Detail)</h2>
<ul>{relations_html}</ul>

<p class="subtitle" style="margin-top:40px">Generiert von <code>scripts/tkg_brain_demo.py</code> — {time.strftime('%Y-%m-%d %H:%M:%S')}</p>

<script>mermaid.initialize({{startOnLoad: true, theme: 'dark', themeVariables: {{primaryColor: '#1a1c22', primaryTextColor: '#e7e9ee', primaryBorderColor: '#00e5ff', lineColor: '#5b8def', fontSize: '14px'}}}});</script>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"✓ HTML written: {output_path}")


def main():
    print("🧠 Building demo TKG brain...")
    db, entities, facts, relations, mentions = build_demo_brain()

    # Demo-Query: Vector-Suche nach "FAISS bug"
    print("\n🔍 Running demo query: 'Was passierte mit dem FAISS-Bug?'")
    query_emb = np.random.rand(384)  # In real: LLM-generiertes Embedding
    results = db.search_facts_by_vector(query_emb, k=3)
    query_result = {
        "query": "Was passierte mit dem FAISS-Bug?",
        "top_k": 3,
        "count": len(results),
        "results": results,
    }
    for r in results:
        print(f"   - {r.id} (imp={r.importance:.2f}): {r.text[:80]}...")

    # Traversal: Welche Facts mentionen "FAISS_ABI_BREAK"?
    print("\n🔍 Traversal: find_facts_mentioning('e_faiss_break')")
    faiss_facts = db.find_facts_mentioning("e_faiss_break")
    for f in faiss_facts:
        print(f"   - {f.id}: {f.text[:80]}...")

    # HTML rendern
    output_path = "/Users/landjunge/gnom-Workspace/default/tkg_brain_demo.html"
    print(f"\n📊 Rendering HTML...")
    render_html(entities, facts, relations, mentions, query_result, output_path)
    print(f"✓ Done. Open: {output_path}")

    db.close()
    return output_path


if __name__ == "__main__":
    main()
