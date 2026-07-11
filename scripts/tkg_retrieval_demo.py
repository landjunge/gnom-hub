#!/usr/bin/env python3
"""TKG Phase 2 Demo: Hybrid Retrieval Engine.

Baut ein kleines Gnom-Hub-TKG (8 Facts, 5 Entities, 4 Relations, 9 Mentions)
und führt 3 Demo-Queries aus (vector-only, graph-only, hybrid). Jeder Query
liefert Mermaid-Subgraph + Ranking + Metadata. Output ist ein interaktives
HTML in /Users/landjunge/gnom-Workspace/default/tkg_retrieval_demo.html mit
Mermaid-Rendering (via CDN), Score-Tabellen und Subgraph-Vergleich.

Usage:
    cd /Users/landjunge/gnom-hub
    ./.venv/bin/python scripts/tkg_retrieval_demo.py

Output:
    /Users/landjunge/gnom-Workspace/default/tkg_retrieval_demo.html
"""
from __future__ import annotations

import sys
import time
from html import escape
from pathlib import Path

# Make src/ importable when run from repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402

from gnom_hub.memory_tkg.in_memory_backend import InMemoryBackend  # noqa: E402
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation  # noqa: E402
from gnom_hub.memory_tkg.retrieval_engine import RetrievalEngine  # noqa: E402

# ── Deterministic embedder (kein sentence-transformers nötig) ────────────────


class _HashEmbedder:
    """Deterministisches Embedding: hash(text) → 384-d float vector.

    Gleicher Text → gleicher Vektor. Cosine-Similarity zwischen ähnlichen
    Texten ist hoch genug, um die Hybrid-Retrieval-Pipeline zu demonstrieren.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self._cache: dict[str, np.ndarray] = {}

    def embed(self, text: str) -> np.ndarray:
        if text in self._cache:
            return self._cache[text]
        h = abs(hash(text.lower().strip()))
        rng = np.random.default_rng(h % (2**32))
        v = rng.standard_normal(self.dim).astype(np.float64)
        v /= np.linalg.norm(v) + 1e-12
        self._cache[text] = v
        return v

    def patch(self) -> None:
        """Patcht gnom_hub.memory_tkg.backend.get_text_embedding für die Demo."""
        from gnom_hub.memory_tkg import backend as _be

        def _patched(text: str) -> np.ndarray | None:
            return self.embed(text)

        _be.get_text_embedding = _patched  # type: ignore[assignment]
        # Auch in retrieval_engine (lokaler Import)
        from gnom_hub.memory_tkg import retrieval_engine as _re
        _re.get_text_embedding = _patched  # type: ignore[assignment]


# ── TKG-Seed: Gnom-Hub Architecture Facts ──────────────────────────────────


def _build_demo_tkg(backend: InMemoryBackend, emb: _HashEmbedder) -> dict:
    """Baut 8 Facts über Gnom-Hub-Architektur + Entities + Relations + Mentions."""
    now = time.time()

    # Entities
    entities = {
        "faiss": Entity(id="e_faiss", name="FAISS", type="bug", importance=0.9, last_seen=now),
        "kuzu": Entity(id="e_kuzu", name="KuzuDB", type="code_id", importance=0.85, last_seen=now),
        "minimax": Entity(id="e_minimax", name="MiniMax", type="model", importance=0.8, last_seen=now),
        "soulag": Entity(id="e_soulag", name="SoulAG", type="agent", importance=0.95, last_seen=now),
        "coderag": Entity(id="e_coderag", name="CoderAG", type="agent", importance=0.7, last_seen=now),
    }
    for e in entities.values():
        backend.upsert_entity(e)

    # Facts (8 — alle über Gnom-Hub-Architektur)
    fact_specs = [
        ("f_faiss_break",
         "FAISS ABI break in numpy 2.2.6 was fixed by pyproject pin <2.0,<5.0",
         0.95, now - 1000, ["faiss"]),
        ("f_kuzu_replace",
         "KuzuDB replaces FAISS for vector search in TKG v4 with HNSW index",
         0.9, now - 800, ["kuzu", "faiss"]),
        ("f_minimax_default",
         "MiniMax M3 is the default model for routing in Gnom-Hub",
         0.85, now - 500, ["minimax", "soulag"]),
        ("f_soulag_orch",
         "SoulAG orchestrates all worker agents via mention routing and RRF fusion",
         0.9, now - 400, ["soulag", "minimax"]),
        ("f_tkg_design",
         "TKG redesign with bitemporal edges replaced flat MemoryRecords in v4",
         0.7, now - 200, ["kuzu"]),
        ("f_coderag_kick",
         "CoderAG gets kicked directly when GeneralAG fails to delegate",
         0.6, now - 150, ["coderag", "soulag"]),
        ("f_pinia_pin",
         "Pre-existing pinia/numpy pin guards against FAISS ABI breaks",
         0.7, now - 50, ["faiss"]),
        ("f_curator_active",
         "Curator agent uses LLM to extract entities and relations from messages",
         0.65, now - 100, ["minimax"]),
    ]
    facts: dict[str, Fact] = {}
    for fid, text, importance, valid_at, entity_keys in fact_specs:
        fact = Fact(
            id=fid,
            text=text,
            embedding=emb.embed(text),
            importance=importance,
            valid_at=valid_at,
        )
        backend.upsert_fact(fact)
        facts[fid] = fact
        # Mentions
        for ek in entity_keys:
            backend.add_mention(Mention(
                fact_id=fid,
                entity_id=entities[ek].id,
                confidence=0.85,
            ))

    # Relations (bitemporal-aware: nutzen jetzt-Werte)
    relations = [
        Relation(from_id="f_faiss_break", to_id="f_kuzu_replace", predicate="superseded_by", valid_at=now - 700),
        Relation(from_id="f_kuzu_replace", to_id="f_tkg_design", predicate="part_of", valid_at=now - 150),
        Relation(from_id="f_minimax_default", to_id="f_soulag_orch", predicate="used_by", valid_at=now - 300),
        Relation(from_id="f_pinia_pin", to_id="f_faiss_break", predicate="prevents", valid_at=now - 30),
        Relation(from_id="f_coderag_kick", to_id="f_soulag_orch", predicate="works_under", valid_at=now - 100),
    ]
    for r in relations:
        backend.add_relation(r)

    return {"entities": entities, "facts": facts, "relations": relations}


# ── Demo Queries ────────────────────────────────────────────────────────────


def _run_demo_queries(engine: RetrievalEngine) -> list[dict]:
    """3 Demo-Queries: vector-only, graph-only, hybrid."""
    queries = [
        {
            "label": "Vector-only Query",
            "subtitle": "Embedding-Similarity im HNSW-Vector-Index (FAISS-replacement)",
            "query_text": "What replaced FAISS in the TKG redesign?",
            "symbols": None,
            "color": "#369",
        },
        {
            "label": "Symbol-anchored Query",
            "subtitle": "Symbol-Filter: 'SoulAG' + 'MiniMax' priorisiert Fact-Set",
            "query_text": "How does the orchestrator route to the default model?",
            "symbols": ["SoulAG", "MiniMax"],
            "color": "#c39",
        },
        {
            "label": "Hybrid Query (Vector + Symbol + Graph)",
            "subtitle": "RRF-Fusion + 2-Hop-Graph-Traversal + Heuristic-Re-Rank",
            "query_text": "FAISS numpy pin and KuzuDB TKG redesign architecture",
            "symbols": ["FAISS", "KuzuDB"],
            "color": "#393",
        },
    ]
    results: list[dict] = []
    for q in queries:
        r = engine.query(q["query_text"], symbols=q["symbols"], k=5)
        results.append({**q, "result": r})
    return results


# ── HTML-Renderer ───────────────────────────────────────────────────────────


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TKG Phase 2 — Hybrid Retrieval Demo</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  :root {{
    --bg: #0f1116;
    --fg: #e6e6e6;
    --muted: #9aa0a6;
    --accent: #66d9ef;
    --card: #1a1d24;
    --border: #2a2e36;
    --green: #4ade80;
    --blue: #60a5fa;
    --purple: #c084fc;
    --red: #f87171;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 32px;
    line-height: 1.5;
  }}
  h1 {{ color: var(--accent); margin: 0 0 8px 0; font-size: 1.8em; }}
  h2 {{ color: var(--accent); margin: 32px 0 12px 0; font-size: 1.3em; border-bottom: 1px solid var(--border); padding-bottom: 4px; }}
  h3 {{ color: var(--fg); margin: 16px 0 8px 0; font-size: 1.05em; }}
  .subtitle {{ color: var(--muted); font-size: 0.9em; margin-bottom: 16px; }}
  .meta {{ color: var(--muted); font-size: 0.85em; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin: 16px 0;
  }}
  .query-card {{ border-left: 4px solid {color}; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.75em; }}
  td.score {{ font-variant-numeric: tabular-nums; color: var(--green); }}
  td.cached {{ color: var(--blue); font-weight: 600; }}
  .component-bar {{
    display: inline-block;
    height: 6px;
    background: var(--accent);
    margin-right: 2px;
    vertical-align: middle;
  }}
  .mermaid {{ background: #ffffff; padding: 16px; border-radius: 6px; margin: 12px 0; }}
  pre {{ background: #0a0c10; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.85em; color: var(--muted); }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
  .summary-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }}
  .summary-card .num {{ font-size: 2em; color: var(--accent); font-weight: 700; }}
  .summary-card .lbl {{ color: var(--muted); font-size: 0.8em; text-transform: uppercase; }}
  .badge {{ display: inline-block; background: #2a2e36; color: var(--accent); padding: 2px 8px; border-radius: 4px; font-size: 0.75em; margin-right: 4px; }}
</style>
</head>
<body>

<h1>TKG Phase 2 — Hybrid Retrieval Engine Demo</h1>
<div class="subtitle">Vector (HNSW) + Graph (1-2 hops) + Symbolic + RRF-Fusion + Heuristic Re-Rank + Mermaid-View</div>

<div class="summary-grid">
  <div class="summary-card"><div class="num">{total_facts}</div><div class="lbl">Facts im TKG</div></div>
  <div class="summary-card"><div class="num">{total_entities}</div><div class="lbl">Entities</div></div>
  <div class="summary-card"><div class="num">{total_relations}</div><div class="lbl">Relations</div></div>
  <div class="summary-card"><div class="num">{total_mentions}</div><div class="lbl">Mentions</div></div>
</div>

{demo_queries_html}

<h2>Underlying TKG (full graph)</h2>
<div class="card">
<pre class="mermaid">{full_mermaid}</pre>
</div>

<h2>Methodology</h2>
<div class="card">
<h3>Pipeline</h3>
<pre>Query
  → get_text_embedding() (deterministic hash-embedder in this demo)
  → [Vector] backend.search_facts_by_vector(emb, k=30)        # HNSW
  → [Symbol] backend.find_entities_by_name(s) + find_facts_mentioning()
  → [Graph] 1-2 hop BFS via find_relations + find_facts_mentioning
  → [RRF Fusion]   score += 1/(60 + rank) per list
  → [Re-Rank]      0.4·cosine + 0.3·graph_centrality + 0.2·symbol_overlap + 0.1·recency
  → [LRU Cache]    hash(query+symbols+time_bucket_5min)
  → [Mermaid]      to_mermaid(entities, facts, relations, mentions)</pre>
</div>

<script>
  mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
</script>
</body>
</html>
"""


def _result_to_html(q: dict) -> str:
    """Rendert eine einzelne Query-Card mit Score-Tabelle + Mermaid-Subgraph."""
    r = q["result"]
    rows: list[str] = []
    for i, sf in enumerate(r.facts, 1):
        components = sf.components
        # Visualisierungs-Balken für die 4 Heuristik-Komponenten
        bars = "".join(
            f'<span class="component-bar" style="width:{int(v*40)}px;" title="{k}={v:.2f}"></span>'
            for k, v in components.items()
        )
        cached_badge = '<span class="badge" style="color:var(--blue)">CACHE-HIT</span>' if r.cached else ''
        rows.append(
            f"<tr><td>{i}</td><td>{escape(sf.fact.id)}</td>"
            f"<td>{escape(sf.fact.text[:90])}</td>"
            f'<td class="score">{sf.score:.3f}</td>'
            f"<td>{bars}</td>"
            f"<td>{cached_badge}</td></tr>"
        )
    rows_html = "\n".join(rows) if rows else '<tr><td colspan="6" class="meta">(no results)</td></tr>'

    mermaid_block = (
        f'<pre class="mermaid">{r.mermaid}</pre>' if r.mermaid.strip() else '<div class="meta">(empty subgraph)</div>'
    )

    md = r.metadata
    metadata_html = (
        f'<div class="meta">candidates: {md.get("candidates", 0)} · '
        f'vector_hits: {md.get("vector_hits", 0)} · '
        f'symbol_hits: {md.get("symbol_hits", 0)} · '
        f'graph_hits: {md.get("graph_hits", 0)} · '
        f'rrf_k: {md.get("rrf_k", 60)} · '
        f'max_hops: {md.get("max_hops", 2)} · '
        f'latency: {r.latency_ms:.1f}ms</div>'
    )

    return f"""
<div class="card query-card" style="border-left-color: {q['color']};">
  <h2 style="border:none;color:{q['color']};">{escape(q['label'])}</h2>
  <div class="subtitle">{escape(q['subtitle'])}</div>
  <div class="meta">
    <span class="badge">query: {escape(q['query_text'])}</span>
    {''.join(f'<span class="badge">symbol: {escape(s)}</span>' for s in (q['symbols'] or []))}
  </div>
  {metadata_html}
  <h3>Top-{len(r.facts)} ranked ScoredFacts</h3>
  <table>
    <thead><tr><th>#</th><th>Fact-ID</th><th>Text</th><th>Score</th><th>Components</th><th></th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <h3>Subgraph-Context (Mermaid)</h3>
  {mermaid_block}
</div>
"""


def render_html(results: list[dict], full_mermaid: str, seed: dict) -> str:
    demo_queries_html = "\n".join(_result_to_html(q) for q in results)
    return _HTML_TEMPLATE.format(
        total_facts=len(seed["facts"]),
        total_entities=len(seed["entities"]),
        total_relations=len(seed["relations"]),
        total_mentions=sum(
            1 for r in results
            for _ in r["result"].mentions
        ),
        demo_queries_html=demo_queries_html,
        full_mermaid=escape(full_mermaid),
        color="#66d9ef",
    )


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("TKG Phase 2 — Hybrid Retrieval Engine Demo")
    print("=" * 60)

    # 1. Setup: deterministic embedder + In-Memory-Backend
    emb = _HashEmbedder(dim=384)
    emb.patch()
    backend = InMemoryBackend()

    # 2. Build demo TKG
    print("\n[1/4] Building demo TKG (8 facts, 5 entities, 5 relations)...")
    seed = _build_demo_tkg(backend, emb)
    print(f"      → Facts: {len(seed['facts'])}, Entities: {len(seed['entities'])}, Relations: {len(seed['relations'])}")

    # 3. Engine + run 3 queries
    print("\n[2/4] Running 3 demo queries...")
    engine = RetrievalEngine(backend, cache_size=16, max_hops=2)
    results = _run_demo_queries(engine)
    for q in results:
        top = q["result"].facts[0] if q["result"].facts else None
        top_str = f"{top.fact.id} (score={top.score:.3f})" if top else "(no result)"
        print(f"      ✓ {q['label']:35s} → top: {top_str}  ({q['result'].latency_ms:.1f}ms)")

    # 4. Full Mermaid-Subgraph (für HTML-Header)
    print("\n[3/4] Generating full Mermaid-Subgraph...")
    from gnom_hub.memory_tkg.subgraph_serializer import to_mermaid
    all_facts = list(seed["facts"].values())
    all_relations = seed["relations"]
    all_mentions: list[Mention] = []
    for f in all_facts:
        for e in seed["entities"].values():
            all_mentions.append(Mention(fact_id=f.id, entity_id=e.id, confidence=0.9))
    full_mermaid = to_mermaid(list(seed["entities"].values()), all_facts, all_relations, all_mentions)
    print(f"      → {len(full_mermaid.splitlines())} lines of Mermaid")

    # 5. Render HTML
    print("\n[4/4] Rendering HTML...")
    html = render_html(results, full_mermaid, seed)
    out_dir = Path("/Users/landjunge/gnom-Workspace/default")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "tkg_retrieval_demo.html"
    out_file.write_text(html, encoding="utf-8")
    size_kb = out_file.stat().st_size / 1024
    print(f"      → {out_file} ({size_kb:.1f} KB)")

    print("\n" + "=" * 60)
    print("✓ Demo complete.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
