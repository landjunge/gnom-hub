"""Hybrid Retrieval Engine: Vector + Graph + Symbolic mit RRF-Fusion + Re-Rank.

Phase 2 des TKG-Plans: §1.4 (RetrievalEngineer), §2.4 (Hybrid Retrieval).

Pipeline:
    query_text
        │
        ├──[Embedder]──► HNSW-Vector-Search  ──► Vector-Hits (top N)
        │
        ├──[Symbol-Match]──► find_entities_by_name() ──► find_facts_mentioning() ──► Symbol-Hits
        │
        ├──[Graph-Traversal 1-2 Hops]──► follow RELATES_TO + MENTIONS edges
        │
        ├──[RRF-Fusion]──► Reciprocal Rank Fusion der 3 Listen
        │
        └──[Heuristic Re-Rank]──► 0.4·cosine + 0.3·graph_centrality + 0.2·symbol_overlap + 0.1·recency

Cache:
    LRU (default 1000 entries). Hash-Key: `query + symbols + time_bucket(5min)`.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from gnom_hub.memory_tkg.backend import MemoryBackend, get_text_embedding
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation
from gnom_hub.memory_tkg.reranker import HeuristicReranker, ScoredFact
from gnom_hub.memory_tkg.subgraph_serializer import to_mermaid


# ── Konstanten ──────────────────────────────────────────────────────────────

# RRF-Konstante (Original paper: 60). Höher = glattere Fusion.
RRF_K: int = 60

# Vector-Suche holt mehr als nötig, damit RRF & Reranker was zum Auswählen haben.
VECTOR_OVERFETCH: int = 30
SYMBOL_OVERFETCH: int = 30
GRAPH_TRAVERSAL_MAX_HOPS: int = 2
GRAPH_TRAVERSAL_MAX_NODES: int = 50

# Cache-Key-Bucket: 5 Minuten. Innerhalb des Buckets gilt der Cache-Hit.
# Bewusst grob, weil Live-Daten in der DB sich ändern können.
CACHE_TIME_BUCKET_SEC: int = 300


# ── Datentypen ──────────────────────────────────────────────────────────────


@dataclass
class RetrievalResult:
    """Output eines `RetrievalEngine.query()`-Calls."""
    query: str
    symbols: list[str] = field(default_factory=list)
    facts: list[ScoredFact] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    mentions: list[Mention] = field(default_factory=list)
    mermaid: str = ""
    cached: bool = False
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def top_facts(self, n: int = 5) -> list[ScoredFact]:
        return self.facts[:n]


# ── LRU-Cache ───────────────────────────────────────────────────────────────


class _LRUCache:
    """Einfacher LRU-Cache (Hash-Key → RetrievalResult)."""

    def __init__(self, capacity: int = 1000):
        self._capacity = max(1, capacity)
        self._data: "OrderedDict[str, RetrievalResult]" = OrderedDict()

    def get(self, key: str) -> Optional[RetrievalResult]:
        if key not in self._data:
            return None
        # Move-to-end
        result = self._data.pop(key)
        self._data[key] = result
        return result

    def put(self, key: str, value: RetrievalResult) -> None:
        if key in self._data:
            self._data.pop(key)
        elif len(self._data) >= self._capacity:
            self._data.popitem(last=False)  # FIFO-evict oldest
        self._data[key] = value

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        self._data.clear()


def _cache_key(query: str, symbols: list[str] | None, k: int, now: float) -> str:
    """Stabile Hash-Funktion: query + sorted(symbols) + k + 5min-time-bucket."""
    sym_part = ",".join(sorted(s.strip() for s in (symbols or []) if s and s.strip()))
    bucket = int(now // CACHE_TIME_BUCKET_SEC)
    raw = f"{query.strip().lower()}|{sym_part}|k={k}|b={bucket}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


# ── Hybrid Retrieval Engine ──────────────────────────────────────────────────


class RetrievalEngine:
    """Hauptklasse. Nimmt ein MemoryBackend + optional Reranker, macht Hybrid-Query.

    Args:
        backend: MemoryBackend-Impl (KuzuDB, InMemory, ...). Strukturelles Subtyping
                 — `KuzuDBBackend` und `InMemoryBackend` erfüllen das Protocol.
        cache_size: LRU-Cache-Größe. Default 1000 (per Design-Doc).
        reranker: Optional eigener HeuristicReranker. Default = Heuristik-Defaults.
        max_hops: Graph-Traversal-Tiefe. Default 2.
        vector_k: Vector-Overfetch. Default 30.
    """

    def __init__(
        self,
        backend: MemoryBackend,
        cache_size: int = 1000,
        reranker: HeuristicReranker | None = None,
        max_hops: int = GRAPH_TRAVERSAL_MAX_HOPS,
        vector_k: int = VECTOR_OVERFETCH,
    ):
        self.backend = backend
        self.cache = _LRUCache(cache_size)
        self.reranker = reranker or HeuristicReranker()
        self.max_hops = max(1, max_hops)
        self.vector_k = max(1, vector_k)

    # ── Public API ───────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        symbols: list[str] | None = None,
        k: int = 10,
    ) -> RetrievalResult:
        """Hauptmethode: Hybrid-Retrieval mit Cache + RRF + Re-Rank.

        Args:
            query_text: Natürlichsprachige Query (z.B. "FAISS-ABI-Bruch")
            symbols: Optional Liste von Symbolen (z.B. ["routing.txt", "2026-06-25"]).
                     Dient als zusätzlicher Filter — Facts ohne Symbol-Match werden
                     niedriger gewichtet, aber nicht hart ausgeschlossen.
            k: Anzahl der finalen Top-Facts. Default 10.

        Returns:
            RetrievalResult mit `facts` (ScoredFact-Liste), Subgraph-Kontext, Mermaid.
        """
        t0 = time.time()
        if not query_text or not query_text.strip():
            return RetrievalResult(
                query=query_text or "",
                symbols=symbols or [],
                cached=False,
                latency_ms=(time.time() - t0) * 1000.0,
            )

        # 1. Cache-Check
        now = time.time()
        ck = _cache_key(query_text, symbols, k, now)
        cached = self.cache.get(ck)
        if cached is not None:
            # Return a copy with cached=True; mutable lists müssen neu sein
            new = RetrievalResult(
                query=cached.query,
                symbols=list(cached.symbols),
                facts=list(cached.facts),
                entities=list(cached.entities),
                relations=list(cached.relations),
                mentions=list(cached.mentions),
                mermaid=cached.mermaid,
                cached=True,
                latency_ms=(time.time() - t0) * 1000.0,
                metadata={**cached.metadata, "cache_hit": True},
            )
            return new

        # 2. Query-Embedding
        query_emb = get_text_embedding(query_text)

        # 3. Vector-Hits (HNSW oder Brute-Force je nach Backend)
        vector_hits: list[Fact] = []
        if query_emb is not None:
            try:
                vector_hits = self.backend.search_facts_by_vector(query_emb, k=self.vector_k)
            except Exception:
                vector_hits = []

        # 4. Symbol-Hits (Entity → Mentions)
        symbol_hits: list[Fact] = []
        symbol_entities: list[Entity] = []
        if symbols:
            seen_entity_ids: set[str] = set()
            for sym in symbols:
                if not sym or not sym.strip():
                    continue
                try:
                    entities = self.backend.find_entities_by_name(sym)
                except Exception:
                    entities = []
                for e in entities:
                    if e.id in seen_entity_ids:
                        continue
                    seen_entity_ids.add(e.id)
                    symbol_entities.append(e)
                    try:
                        facts = self.backend.find_facts_mentioning(e.id)
                    except Exception:
                        facts = []
                    for f in facts:
                        if f not in symbol_hits:
                            symbol_hits.append(f)

        # 5. Graph-Traversal: 1-2 Hop von Vector/Symbol-Hits aus
        graph_facts, graph_relations, graph_mentions = self._graph_traverse(
            seed_facts=vector_hits + symbol_hits,
            seed_entities=symbol_entities,
            max_hops=self.max_hops,
        )

        # 6. RRF-Fusion: 3 Listen (vector, symbol, graph)
        rrf_scores: dict[str, float] = OrderedDict()
        fact_index: dict[str, Fact] = {}
        for f in vector_hits:
            fact_index[f.id] = f
        for f in symbol_hits:
            fact_index.setdefault(f.id, f)
        for f in graph_facts:
            fact_index.setdefault(f.id, f)

        for rank, f in enumerate(vector_hits):
            rrf_scores[f.id] = rrf_scores.get(f.id, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, f in enumerate(symbol_hits):
            rrf_scores[f.id] = rrf_scores.get(f.id, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, f in enumerate(graph_facts):
            rrf_scores[f.id] = rrf_scores.get(f.id, 0.0) + 1.0 / (RRF_K + rank + 1)

        # 7. Rerank auf allen RRF-Top-Candidates
        candidates = [fact_index[fid] for fid, _ in sorted(
            rrf_scores.items(), key=lambda kv: kv[1], reverse=True
        )]
        if not candidates:
            result = RetrievalResult(
                query=query_text,
                symbols=symbols or [],
                cached=False,
                latency_ms=(time.time() - t0) * 1000.0,
                metadata={"candidates": 0},
            )
            self.cache.put(ck, result)
            return result

        scored = self.reranker.rerank(candidates, query_text, query_emb)

        # 8. Top-k cutoff
        top = scored[: max(1, k)]

        # 9. Subgraph-Context: alle Top-Facts + 1-Hop-Umgebung
        context_entities: dict[str, Entity] = {e.id: e for e in symbol_entities}
        context_facts: dict[str, Fact] = {sf.fact.id: sf.fact for sf in top}
        context_relations: list[Relation] = []
        context_mentions: list[Mention] = []

        for sf in top:
            try:
                rels = self.backend.find_relations(sf.fact.id)
            except Exception:
                rels = []
            for r in rels:
                if r.from_id in context_facts and r.to_id in context_facts:
                    context_relations.append(r)
                # 1-Hop: andere Fact, falls im Top-Subset
                if r.to_id in fact_index and r.to_id not in context_facts:
                    context_facts[r.to_id] = fact_index[r.to_id]
                if r.from_id in fact_index and r.from_id not in context_facts:
                    context_facts[r.from_id] = fact_index[r.from_id]

        # Mentions für alle Top-Facts
        for sf in top:
            try:
                # Wir brauchen Entity-ID-Lookup, also: pro Fact alle Entities
                # die sie mentionen. Dafür gibt es keine direkte Backend-Methode,
                # also machen wir reverse: pro Entity in unserem Subset,
                # schauen ob Fact sie mentiont.
                for e in symbol_entities + list(context_entities.values()):
                    try:
                        facts = self.backend.find_facts_mentioning(e.id)
                    except Exception:
                        facts = []
                    if sf.fact.id in [f.id for f in facts]:
                        m = Mention(fact_id=sf.fact.id, entity_id=e.id, confidence=0.9)
                        if m not in context_mentions:
                            context_mentions.append(m)
                            context_entities.setdefault(e.id, e)
            except Exception:
                pass

        # 10. Mermaid-Subgraph
        mermaid = to_mermaid(
            entities=list(context_entities.values()),
            facts=list(context_facts.values()),
            relations=context_relations,
            mentions=context_mentions,
        )

        result = RetrievalResult(
            query=query_text,
            symbols=symbols or [],
            facts=top,
            entities=list(context_entities.values()),
            relations=context_relations,
            mentions=context_mentions,
            mermaid=mermaid,
            cached=False,
            latency_ms=(time.time() - t0) * 1000.0,
            metadata={
                "candidates": len(candidates),
                "vector_hits": len(vector_hits),
                "symbol_hits": len(symbol_hits),
                "graph_hits": len(graph_facts),
                "rrf_k": RRF_K,
                "max_hops": self.max_hops,
            },
        )
        self.cache.put(ck, result)
        return result

    def clear_cache(self) -> None:
        """Test-Hook / Admin: Cache leeren."""
        self.cache.clear()

    # ── Private: Graph-Traversal ──────────────────────────────────────────

    def _graph_traverse(
        self,
        seed_facts: list[Fact],
        seed_entities: list[Entity],
        max_hops: int,
    ) -> tuple[list[Fact], list[Relation], list[Mention]]:
        """BFS 1-2 Hop von seed_facts (Fact→Fact via RELATES_TO) und seed_entities.

        Returns:
            (facts, relations, mentions) — alle in der traversierten Subgraph-Region.
        """
        visited_facts: dict[str, Fact] = {f.id: f for f in seed_facts}
        visited_entities: dict[str, Entity] = {e.id: e for e in seed_entities}
        relations: list[Relation] = []
        mentions: list[Mention] = []

        # BFS-Frontier
        frontier_facts: list[str] = [f.id for f in seed_facts]
        frontier_entities: list[str] = [e.id for e in seed_entities]

        for hop in range(max_hops):
            next_fact_ids: set[str] = set()
            next_entity_ids: set[str] = set()

            # 1. Fact → Fact (RELATES_TO)
            for fid in frontier_facts:
                if len(visited_facts) >= GRAPH_TRAVERSAL_MAX_NODES:
                    break
                try:
                    rels = self.backend.find_relations(fid)
                except Exception:
                    rels = []
                for r in rels:
                    if r.invalid_at is not None:
                        continue  # nur aktive Edges
                    if r not in relations:
                        relations.append(r)
                    for endpoint_id in (r.from_id, r.to_id):
                        if endpoint_id in visited_facts:
                            continue
                        if len(visited_facts) >= GRAPH_TRAVERSAL_MAX_NODES:
                            break
                        try:
                            other = self.backend.get_fact(endpoint_id)
                        except Exception:
                            other = None
                        if other is not None:
                            visited_facts[other.id] = other
                            next_fact_ids.add(other.id)

            # 2. Fact → Entity (MENTIONS) und Entity → Facts (reverse)
            for fid in frontier_facts:
                for eid in frontier_entities:
                    m = Mention(fact_id=fid, entity_id=eid, confidence=0.9)
                    if m not in mentions:
                        mentions.append(m)
                        # Mark entity als relevant
                        e = visited_entities.get(eid)
                        if e is None:
                            try:
                                e = self.backend.get_entity(eid)
                            except Exception:
                                e = None
                            if e is not None:
                                visited_entities[e.id] = e
                                next_entity_ids.add(e.id)

            # 3. Entity → Facts (reverse): welche Facts mentionen eine frontier entity?
            for eid in frontier_entities:
                if len(visited_facts) >= GRAPH_TRAVERSAL_MAX_NODES:
                    break
                try:
                    related_facts = self.backend.find_facts_mentioning(eid)
                except Exception:
                    related_facts = []
                for f in related_facts:
                    if f.id not in visited_facts:
                        if len(visited_facts) >= GRAPH_TRAVERSAL_MAX_NODES:
                            break
                        visited_facts[f.id] = f
                        next_fact_ids.add(f.id)

            if not next_fact_ids and not next_entity_ids:
                break
            frontier_facts = list(next_fact_ids)
            frontier_entities = list(next_entity_ids)

        return list(visited_facts.values()), relations, mentions


__all__ = [
    "RetrievalEngine",
    "RetrievalResult",
    "RRF_K",
    "VECTOR_OVERFETCH",
    "CACHE_TIME_BUCKET_SEC",
]
