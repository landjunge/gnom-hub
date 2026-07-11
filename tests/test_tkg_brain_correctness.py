"""Regression test: Hybrid TKG precision beats Vector-only baseline.

The TKG brain was silently broken (0% precision) when:
  - get_text_embedding() returned None (missing import)
  - MENTIONS weren't seeded
  - benchmark scripts used wrong API (ScoredFact.text vs ScoredFact.fact.text)

This test is the canary: if vector-only beats hybrid, the brain is broken.
Real benchmark: Vector 70% / Hybrid 95% (precision@5, 100 facts, 20 queries).
"""
from __future__ import annotations

import random
import time

import numpy as np
import pytest

from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention
from gnom_hub.memory_tkg.retrieval_engine import RetrievalEngine


def _hash_embed(text: str, dim: int = 384) -> np.ndarray:
    """Deterministic hash-embedder — same fallback as backend.get_text_embedding."""
    import hashlib

    h = hashlib.sha512(text.encode("utf-8")).digest()
    vec = np.zeros(dim, dtype=np.float32)
    for i in range(dim):
        vec[i] = (h[i % len(h)] ^ h[(i * 7 + 13) % len(h)]) / 255.0
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


TOPICS = {
    "KuzuDB": ["backend", "graph", "hnsw"],
    "FAISS": ["index", "similarity"],
    "TKG": ["curator", "extraction"],
    "Hub": ["startup", "thundering"],
    "Prompts": ["showbox", "worker"],
    "Routing": ["generalag", "soulag"],
}


@pytest.fixture
def seeded_kuzu(tmp_path):
    """100 facts + mentions across 6 topics, deterministic seed."""
    db_path = tmp_path / "tkg_brain.kuzu"
    db = KuzuDBBackend(str(db_path))
    rng = random.Random(42)
    topic_to_eid = {t: f"e_{t.lower()}" for t in TOPICS}
    for topic in TOPICS:
        db.upsert_entity(Entity(id=topic_to_eid[topic], name=topic, type="concept", importance=0.8))
    for i in range(100):
        topic = rng.choice(list(TOPICS.keys()))
        related = rng.choice(TOPICS[topic])
        other = rng.choice(list(TOPICS.keys()))
        templates = [
            f"During the {topic} implementation we discovered that {related} had issues with {other}.",
            f"The {topic} subsystem uses {related} for {other} processing.",
            f"Performance issue: {topic} + {related} combination was 5x slower than expected.",
            f"Refactoring: replaced {related} in {topic} with better alternative.",
            f"Documentation: {topic} requires {related} setup for {other} to work.",
        ]
        text = rng.choice(templates)
        db.upsert_fact(Fact(
            id=f"f_{i:03d}", text=text, embedding=_hash_embed(text),
            importance=rng.uniform(0.3, 0.9),
            valid_at=time.time() - rng.randint(0, 30 * 86400),
        ))
        db.add_mention(Mention(fact_id=f"f_{i:03d}", entity_id=topic_to_eid[topic], confidence=1.0))
        if rng.random() > 0.5:
            db.add_mention(Mention(fact_id=f"f_{i:03d}", entity_id=topic_to_eid[other], confidence=0.7))
    return db, topic_to_eid


def test_hybrid_beats_vector_only(seeded_kuzu):
    """The canary: if vector-only > hybrid, the TKG brain is broken."""
    db, _ = seeded_kuzu
    engine = RetrievalEngine(db, cache_size=0)

    queries = [
        ("KuzuDB backend performance", "KuzuDB"),
        ("FAISS index fallback issue", "FAISS"),
        ("TKG curator extraction", "TKG"),
        ("Hub startup thundering herd", "Hub"),
        ("Prompts showbox format", "Prompts"),
        ("Routing generalag default", "Routing"),
        ("KuzuDB cypher schema", "KuzuDB"),
        ("FAISS similarity cosine", "FAISS"),
        ("TKG bitemporal memory", "TKG"),
        ("Hub subprocess waisen", "Hub"),
        ("Prompts worker showbox", "Prompts"),
        ("Routing soulag delegation", "Routing"),
        ("KuzuDB vector hnsw", "KuzuDB"),
        ("FAISS tfidf fallback", "FAISS"),
        ("TKG entity relation", "TKG"),
        ("Hub registry lock", "Hub"),
        ("Prompts json format", "Prompts"),
        ("Routing general soul", "Routing"),
        ("KuzuDB embedded graph", "KuzuDB"),
        ("TKG curator extraction pipeline", "TKG"),
    ]

    vector_hits = 0
    hybrid_hits = 0
    for query, gold in queries:
        # Vector-only
        v = db.search_facts_by_vector(_hash_embed(query), k=5)
        if any(gold in f.text for f in v):
            vector_hits += 1
        # Hybrid (no gold symbols — honest mode)
        r = engine.query(query, symbols=None, k=5)
        if any(gold in sf.fact.text for sf in r.facts):
            hybrid_hits += 1

    vector_p = vector_hits / len(queries)
    hybrid_p = hybrid_hits / len(queries)
    # The canary: hybrid must beat vector-only. If it doesn't, the brain regressed.
    assert hybrid_p > vector_p, (
        f"Hybrid ({hybrid_p:.0%}) did not beat Vector-only ({vector_p:.0%}). "
        f"Possible regressions: get_text_embedding broken, MENTIONS not seeded, "
        f"or ScoredFact API changed. Re-run scripts/benchmark_hybrid_vs_vector.py."
    )


def test_scoredfact_exposes_fact(seeded_kuzu):
    """ScoredFact wraps Fact — explicit API contract test."""
    db, _ = seeded_kuzu
    engine = RetrievalEngine(db, cache_size=0)
    r = engine.query("KuzuDB backend", k=3)
    assert r.facts, "Engine returned no results"
    for sf in r.facts:
        # Contract: ScoredFact.fact is the wrapped Fact
        assert hasattr(sf, "fact"), "ScoredFact missing .fact"
        assert hasattr(sf.fact, "text"), "Fact missing .text"
        assert hasattr(sf, "score"), "ScoredFact missing .score"
        assert 0.0 <= sf.score <= 1.0
