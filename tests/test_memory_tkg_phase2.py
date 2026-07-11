"""Tests für TKG Phase 2: Hybrid Retrieval Engine + Reranker + Mermaid Serializer.

Parametrisiert über `backend` Fixture (KuzuDB + In-Memory) — analog zu
`test_memory_tkg.py`.

Embedder-Realität: `gnom_hub.memory.embeddings.get_embedding` existiert in dieser
Codebase nicht (nur `get_embedder`). Daher ist `get_text_embedding()` in Test-
Umgebung immer `None` — Vector-Path wird via `monkeypatch` simuliert.
"""
from __future__ import annotations

import re
import time

import numpy as np
import pytest

from gnom_hub.memory_tkg.in_memory_backend import InMemoryBackend
from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation
from gnom_hub.memory_tkg.reranker import (
    HeuristicReranker,
    ScoredFact,
)
from gnom_hub.memory_tkg.retrieval_engine import (
    RRF_K,
    RetrievalEngine,
    RetrievalResult,
)
from gnom_hub.memory_tkg.subgraph_serializer import (
    to_mermaid,
    to_mermaid_safe,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(params=["kuzu", "in_memory"])
def backend(request, tmp_path):
    if request.param == "kuzu":
        b = KuzuDBBackend(str(tmp_path / "phase2.kuzu"))
    else:
        b = InMemoryBackend()
    yield b
    b.close()


@pytest.fixture
def emb_384():
    return np.array([0.1] * 384, dtype=np.float64)


@pytest.fixture
def fake_emb(monkeypatch):
    """Patch `get_text_embedding` so der Vector-Path in Tests funktioniert.

    Liefert für bekannte Texte stabile Embeddings, sonst default-zeros.
    """
    cache: dict[str, np.ndarray] = {}

    def _fake(text: str):
        if text in cache:
            return cache[text]
        # Deterministisches Embedding: hash(text) → 384-d float
        h = abs(hash(text))
        np.random.seed(h % (2**32))
        v = np.random.rand(384).astype(np.float64)
        v /= np.linalg.norm(v) + 1e-12
        cache[text] = v
        return v

    # Patch in retrieval_engine-Modul (dort wird es importiert)
    monkeypatch.setattr(
        "gnom_hub.memory_tkg.retrieval_engine.get_text_embedding",
        _fake,
    )
    # Auch im backend-Modul (für has_similar_fact)
    monkeypatch.setattr(
        "gnom_hub.memory_tkg.backend.get_text_embedding",
        _fake,
    )
    return _fake


def _seed_gnomhub_tkg(backend, emb_384, now: float | None = None) -> dict:
    """Baut ein kleines Gnom-Hub-TKG mit 6 Facts, 4 Entities, Relations, Mentions.

    Returns:
        dict mit Referenzen auf alle erstellten Objekte (für Test-Inspektion).
    """
    if now is None:
        now = time.time()

    # Entities
    faiss = Entity(id="e_faiss", name="FAISS", type="bug", importance=0.9, last_seen=now)
    kuzu = Entity(id="e_kuzu", name="KuzuDB", type="code_id", importance=0.85, last_seen=now)
    minimax = Entity(id="e_minimax", name="MiniMax", type="model", importance=0.8, last_seen=now)
    soulag = Entity(id="e_soulag", name="SoulAG", type="agent", importance=0.9, last_seen=now)
    for e in (faiss, kuzu, minimax, soulag):
        backend.upsert_entity(e)

    # 6 Facts (alle mit Embedding = emb_384, leichte Variationen für cosine-Vielfalt)
    base = np.array(emb_384, dtype=np.float64)
    facts = {
        "f_faiss_break": Fact(
            id="f_faiss_break",
            text="FAISS ABI break in numpy 2.2.6 was fixed by pyproject pin <2.0,<5.0",
            embedding=base * 1.0,
            importance=0.95,
            valid_at=now - 1000.0,
        ),
        "f_kuzu_replace": Fact(
            id="f_kuzu_replace",
            text="KuzuDB replaces FAISS for vector search in TKG v4",
            embedding=base * 0.9,
            importance=0.9,
            valid_at=now - 800.0,
        ),
        "f_minimax_default": Fact(
            id="f_minimax_default",
            text="MiniMax M3 is the default model for routing in Gnom-Hub",
            embedding=base * 0.7,
            importance=0.8,
            valid_at=now - 500.0,
        ),
        "f_soulag_orch": Fact(
            id="f_soulag_orch",
            text="SoulAG orchestrates all worker agents via mention routing",
            embedding=base * 0.5,
            importance=0.85,
            valid_at=now - 400.0,
        ),
        "f_tkg_redisign": Fact(
            id="f_tkg_redisign",
            text="TKG redesign with bitemporal edges replaced flat MemoryRecords",
            embedding=base * 0.3,
            importance=0.7,
            valid_at=now - 200.0,
        ),
        "f_pinia_pin": Fact(
            id="f_pinia_pin",
            text="Pre-existing pinia/numpy pin guards against FAISS ABI breaks",
            embedding=base * 1.1,
            importance=0.6,
            valid_at=now - 50.0,
        ),
    }
    for f in facts.values():
        backend.upsert_fact(f)

    # Mentions: Facts → Entities
    mentions = [
        Mention(fact_id="f_faiss_break", entity_id="e_faiss", confidence=0.95),
        Mention(fact_id="f_kuzu_replace", entity_id="e_faiss", confidence=0.85),
        Mention(fact_id="f_kuzu_replace", entity_id="e_kuzu", confidence=0.95),
        Mention(fact_id="f_minimax_default", entity_id="e_minimax", confidence=0.9),
        Mention(fact_id="f_minimax_default", entity_id="e_soulag", confidence=0.5),
        Mention(fact_id="f_soulag_orch", entity_id="e_soulag", confidence=0.95),
        Mention(fact_id="f_soulag_orch", entity_id="e_minimax", confidence=0.5),
        Mention(fact_id="f_tkg_redisign", entity_id="e_kuzu", confidence=0.7),
        Mention(fact_id="f_pinia_pin", entity_id="e_faiss", confidence=0.6),
    ]
    for m in mentions:
        backend.add_mention(m)

    # Relations: Fact → Fact
    relations = [
        Relation(from_id="f_faiss_break", to_id="f_kuzu_replace", predicate="superseded_by", valid_at=now - 700.0),
        Relation(from_id="f_kuzu_replace", to_id="f_tkg_redisign", predicate="part_of", valid_at=now - 150.0),
        Relation(from_id="f_minimax_default", to_id="f_soulag_orch", predicate="used_by", valid_at=now - 300.0),
        Relation(from_id="f_pinia_pin", to_id="f_faiss_break", predicate="prevents", valid_at=now - 30.0),
    ]
    for r in relations:
        backend.add_relation(r)

    return {
        "entities": {"faiss": faiss, "kuzu": kuzu, "minimax": minimax, "soulag": soulag},
        "facts": facts,
        "mentions": mentions,
        "relations": relations,
        "now": now,
    }


# ── RetrievalEngine Tests ───────────────────────────────────────────────────


def test_retrieval_engine_basic(backend, emb_384, fake_emb):
    """Hybrid-Query liefert ranked ScoredFact-Liste."""
    _seed_gnomhub_tkg(backend, emb_384)
    engine = RetrievalEngine(backend, cache_size=4)

    r = engine.query("FAISS ABI break numpy", k=3)
    assert isinstance(r, RetrievalResult)
    assert r.query == "FAISS ABI break numpy"
    assert 1 <= len(r.facts) <= 3
    # Jedes Fact hat einen Score in [0, 1]
    for sf in r.facts:
        assert isinstance(sf, ScoredFact)
        assert 0.0 <= sf.score <= 1.0
        assert isinstance(sf.fact, Fact)
    # Ranking: absteigend
    for a, b in zip(r.facts, r.facts[1:], strict=False):
        assert a.score >= b.score
    # Latency plausibel (< 5s für ein 6-Fact-Seed mit KuzuDB-Overhead)
    assert r.latency_ms < 5000.0


def test_retrieval_engine_with_symbols(backend, emb_384, fake_emb):
    """Symbol-Filter boosted Facts die das Symbol mentionen.

    Verifiziert: `symbol_hits`-Metadata dokumentiert die Mentions, und
    FAISS-mentionende Facts sind im Top-Set.
    """
    _seed_gnomhub_tkg(backend, emb_384)
    engine = RetrievalEngine(backend, cache_size=2)

    # Mit Symbol "FAISS" → Facts die FAISS mentionen müssen in den Top-Results sein
    r_faiss = engine.query("architecture", symbols=["FAISS"], k=10)
    faiss_ids = {sf.fact.id for sf in r_faiss.facts}

    # FAISS-mentionende Facts müssen im Top-Set sein
    assert "f_faiss_break" in faiss_ids
    assert "f_kuzu_replace" in faiss_ids
    assert "f_pinia_pin" in faiss_ids
    # Metadata dokumentiert die Symbol-Pfad-Hits
    assert r_faiss.metadata.get("symbol_hits", 0) >= 3

    # Mit spezifischerem Symbol (nur ein Mention) → weniger oder gleiche Hits
    engine.clear_cache()
    r_soulag = engine.query("architecture", symbols=["SoulAG"], k=10)
    soulag_ids = {sf.fact.id for sf in r_soulag.facts}
    # SoulAG-mentionende Facts müssen in den Top-Results sein
    assert "f_soulag_orch" in soulag_ids
    assert "f_minimax_default" in soulag_ids
    assert r_soulag.metadata.get("symbol_hits", 0) >= 2

    # FAISS-Symbol produziert mindestens so viele symbol_hits wie SoulAG-Symbol
    # (FAISS wird von 3 Facts mentiont, SoulAG von 2)
    engine.clear_cache()
    r_faiss2 = engine.query("architecture", symbols=["FAISS"], k=10)
    assert r_faiss2.metadata.get("symbol_hits", 0) >= r_soulag.metadata.get("symbol_hits", 0)


def test_retrieval_engine_cache(backend, emb_384, fake_emb):
    """LRU-Cache: identische Query innerhalb Time-Bucket liefert cached=True."""
    _seed_gnomhub_tkg(backend, emb_384)
    engine = RetrievalEngine(backend, cache_size=10)

    r1 = engine.query("FAISS", k=3)
    r2 = engine.query("FAISS", k=3)  # gleiche Query, gleiches Bucket → Cache-Hit
    assert r1.cached is False
    assert r2.cached is True
    # Beide haben dasselbe Top-Set
    assert [sf.fact.id for sf in r1.facts] == [sf.fact.id for sf in r2.facts]


def test_retrieval_engine_mermaid_output(backend, emb_384, fake_emb):
    """Query liefert non-empty Mermaid-Subgraph-String."""
    _seed_gnomhub_tkg(backend, emb_384)
    engine = RetrievalEngine(backend, cache_size=4)
    r = engine.query("FAISS", symbols=["FAISS"], k=3)

    assert r.mermaid.startswith("graph TD")
    assert "f_" in r.mermaid or "e_" in r.mermaid
    # Mindestens eine Edge
    assert "-->" in r.mermaid or "-.->" in r.mermaid


def test_retrieval_engine_empty_query(backend, emb_384):
    """Leere Query: leere RetrievalResult, kein Crash."""
    engine = RetrievalEngine(backend, cache_size=2)
    r = engine.query("", k=5)
    assert r.facts == []
    assert r.cached is False


# ── Reranker Tests ──────────────────────────────────────────────────────────


def test_reranker_weights_default():
    """Default-Gewichte sind exakt wie Design-Doc §2.4."""
    rr = HeuristicReranker()
    assert rr.weights == pytest.approx({
        "cosine": 0.4, "graph_centrality": 0.3, "symbol_overlap": 0.2, "recency": 0.1
    })


def test_reranker_weights_normalization():
    """Nicht-Summe=1 Weights werden normalisiert."""
    rr = HeuristicReranker(weights={"cosine": 4, "graph_centrality": 3, "symbol_overlap": 2, "recency": 1})
    total = sum(rr.weights.values())
    assert total == pytest.approx(1.0)


def test_reranker_weights_invalid():
    """Alle-Null-Gewichte werfen ValueError."""
    with pytest.raises(ValueError):
        HeuristicReranker(weights={"cosine": 0, "graph_centrality": 0, "symbol_overlap": 0, "recency": 0})


def test_reranker_basic_ranking(emb_384):
    """Verschiedene Candidates → unterschiedliche Scores, sortiert desc."""
    now = time.time()
    f_match = Fact(id="f1", text="FAISS ABI break fixed by numpy pin", embedding=emb_384, importance=0.9, valid_at=now)
    f_partial = Fact(id="f2", text="Routing uses MiniMax M3 as default", embedding=emb_384 * 0.5, importance=0.6, valid_at=now - 10000)
    f_irrelevant = Fact(id="f3", text="completely unrelated topic about cooking", embedding=emb_384 * 0.0, importance=0.1, valid_at=now - 100000)

    rr = HeuristicReranker(now=now)
    results = rr.rerank([f_irrelevant, f_match, f_partial], "FAISS numpy", query_emb=emb_384)
    assert len(results) == 3
    # f_match sollte höchsten Score haben
    assert results[0].fact.id == "f1"
    assert results[0].score > results[1].score > results[2].score
    # Komponenten sind alle in [0, 1]
    for r in results:
        for k, v in r.components.items():
            assert 0.0 <= v <= 1.0, f"{k}={v} out of [0,1]"


def test_reranker_weights_different_orderings(emb_384):
    """Verschiedene Weight-Profile produzieren verschiedene Orderings.

    Konstruiere 2 Facts: einer gut im cosine, einer gut im symbol_overlap.
    Mit cosine-dominantem Weight sollte cosine-Fact vorne sein,
    mit symbol_overlap-dominantem Weight sollte der andere vorne sein.
    """
    now = time.time()
    # Cosine-Fact: hohe Vektor-Ähnlichkeit zur query_emb, aber kein Wort-Overlap
    f_cos = Fact(
        id="f_cos",
        text="completely orthogonal word salad pineapple zebra quantum",
        embedding=emb_384,  # gleicher Vektor wie Query
        importance=0.5,
        valid_at=now,
    )
    # Symbol-Fact: identische Wörter wie Query, aber orthogonaler Vektor
    f_sym = Fact(
        id="f_sym",
        text="FAISS numpy pin ABI break this is exact match for query",
        embedding=emb_384 * 0.0,  # senkrecht zur query
        importance=0.5,
        valid_at=now,
    )
    query = "FAISS numpy pin ABI break"
    query_emb = emb_384

    # Cosine-dominant
    rr_cos = HeuristicReranker(
        weights={"cosine": 1.0, "graph_centrality": 0.0, "symbol_overlap": 0.0, "recency": 0.0},
        now=now,
    )
    res_cos = rr_cos.rerank([f_sym, f_cos], query, query_emb=query_emb)
    assert res_cos[0].fact.id == "f_cos", f"cosine-dominant should rank f_cos first, got {res_cos[0].fact.id}"

    # Symbol-dominant
    rr_sym = HeuristicReranker(
        weights={"cosine": 0.0, "graph_centrality": 0.0, "symbol_overlap": 1.0, "recency": 0.0},
        now=now,
    )
    res_sym = rr_sym.rerank([f_sym, f_cos], query, query_emb=query_emb)
    assert res_sym[0].fact.id == "f_sym", f"symbol-dominant should rank f_sym first, got {res_sym[0].fact.id}"

    # Orderings sind verschieden
    assert [r.fact.id for r in res_cos] != [r.fact.id for r in res_sym]


def test_reranker_empty_candidates():
    """Leere Candidate-Liste → leere Output, kein Crash."""
    rr = HeuristicReranker()
    assert rr.rerank([], "test") == []


# ── Subgraph Serializer Tests ───────────────────────────────────────────────


def test_mermaid_serializer_basic(backend, emb_384):
    """to_mermaid liefert valides Mermaid-Markup mit Type-Colors."""
    _seed_gnomhub_tkg(backend, emb_384)
    # Hole die echten Entities + Facts
    entities = [
        backend.get_entity("e_faiss"),
        backend.get_entity("e_kuzu"),
    ]
    facts = [
        backend.get_fact("f_faiss_break"),
        backend.get_fact("f_kuzu_replace"),
    ]
    relations = backend.find_relations("f_faiss_break", "superseded_by")
    mentions = [
        Mention(fact_id="f_faiss_break", entity_id="e_faiss", confidence=0.9),
    ]
    md = to_mermaid(entities, facts, relations, mentions)
    assert md.startswith("graph TD")
    # Knoten
    assert "e_e_faiss" in md
    assert "f_f_faiss_break" in md
    # Solid Edge (RELATION)
    assert '-->' in md
    # Dotted Edge (MENTION)
    assert '-.->' in md
    # classDef-Block
    assert "classDef bug" in md
    # class-Zuweisung
    assert "class e_e_faiss bug" in md


def test_mermaid_serializer_empty():
    """Leere Inputs: 'graph TD' mit classDef-Block, kein Crash."""
    md = to_mermaid([], [], [], [])
    assert md.startswith("graph TD")
    assert "classDef default" in md
    md_safe = to_mermaid_safe([], [], [], [])
    assert md_safe.startswith("graph TD")


def test_mermaid_serializer_node_id_escaping(emb_384):
    """Node-IDs mit Sonderzeichen werden sicher escaped."""
    e = Entity(id="e/with-dash & space!", name="X", type="bug")
    f = Fact(id="f.123:abc", text="some text", embedding=emb_384, importance=0.5, valid_at=100.0)
    md = to_mermaid([e], [f], [], [])
    # Mermaid-IDs dürfen nur [A-Za-z0-9_] enthalten
    ids = re.findall(r"^\s+([A-Za-z0-9_]+)\s*\[", md, flags=re.MULTILINE)
    assert all(re.match(r"^[A-Za-z0-9_]+$", nid) for nid in ids), f"unsafe ids: {ids}"


def test_mermaid_serializer_truncates_long_text():
    """Sehr lange Fact-Texte werden gekürzt (…-Suffix)."""
    f = Fact(id="f1", text="x" * 500, embedding=None, importance=0.5, valid_at=100.0)
    md = to_mermaid([], [f], [], [])
    assert "…" in md
    # Label darf nicht zu lang sein
    label_match = re.search(r'f_f1\["(.+?)"\]', md)
    assert label_match is not None
    assert len(label_match.group(1)) < 100


def test_mermaid_serializer_skip_orphan_endpoints():
    """Relations/Mentions deren Endpoints nicht im Subset sind, werden gefiltert."""
    f1 = Fact(id="f1", text="A", embedding=None, importance=0.5, valid_at=100.0)
    e1 = Entity(id="e1", name="X", type="bug")
    # r verweist auf f2 (nicht im Subset), m verweist auf e2 (nicht im Subset)
    r_orphan = Relation(from_id="f1", to_id="f2", predicate="causes", valid_at=100.0)
    m_orphan = Mention(fact_id="f1", entity_id="e2", confidence=0.9)
    md = to_mermaid([e1], [f1], [r_orphan], [m_orphan])
    # Orphan-Edges dürfen nicht im Markup sein
    assert "f_f2" not in md
    assert "e_e2" not in md


# ── Cross-Cutting: Engine + Mermaid integriert ─────────────────────────────


def test_engine_uses_reranker_and_serializer(backend, emb_384, fake_emb):
    """End-to-end: Engine nutzt Reranker + Serializer, alles ist verdrahtet."""
    _seed_gnomhub_tkg(backend, emb_384)
    custom_reranker = HeuristicReranker(
        weights={"cosine": 0.0, "graph_centrality": 0.0, "symbol_overlap": 1.0, "recency": 0.0},
    )
    engine = RetrievalEngine(backend, cache_size=2, reranker=custom_reranker)
    r = engine.query("FAISS", symbols=["FAISS"], k=2)
    assert len(r.facts) >= 1
    # Top-Fact enthält "FAISS" → sollte mit symbol-only-reranker die höchste symbol_overlap haben
    top = r.facts[0]
    assert top.components["symbol_overlap"] > 0.0


def test_engine_rrf_fuses_multiple_lists(backend, emb_384, fake_emb):
    """Metadata dokumentiert: vector + symbol + graph Listen werden fusioniert."""
    _seed_gnomhub_tkg(backend, emb_384)
    engine = RetrievalEngine(backend, cache_size=2)
    r = engine.query("Gnom-Hub", symbols=["MiniMax", "FAISS"], k=3)
    md = r.metadata
    # Mindestens eine der drei Listen muss nicht-leer sein
    assert (md.get("symbol_hits", 0) > 0
            or md.get("vector_hits", 0) > 0
            or md.get("graph_hits", 0) > 0)
    assert md.get("rrf_k") == RRF_K
