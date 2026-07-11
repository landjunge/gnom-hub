"""Heuristic Re-Ranker for TKG retrieval candidates.

Phase 2 des TKG-Plans: §1.4 (RetrievalEngineer).

Heuristik (per `MEMORY_REDESIGN_2026_TKG.md` §2.4):
    score = w_cos · cosine
          + w_gc  · graph_centrality
          + w_so  · symbol_overlap_ratio
          + w_rec · recency_decay

Defaults aus dem Design-Doc:
    {"cosine": 0.4, "graph_centrality": 0.3, "symbol_overlap": 0.2, "recency": 0.1}

- `cosine`: vorab-berechneter Vektor-Score (kommt aus dem Vector-Index, max=1.0)
- `graph_centrality`: PageRank-artiger Hub-Score (mehr Relationen → höher)
- `symbol_overlap_ratio`: |query_tokens ∩ fact_tokens| / |query_tokens|
- `recency_decay`: lineare Decay über `valid_at` (neuer = höher, älter = niedriger)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from gnom_hub.memory_tkg.models import Fact

# Default Heuristik-Gewichte (Summe muss 1.0 sein, sonst Werte normalisiert)
DEFAULT_WEIGHTS: dict[str, float] = {
    "cosine": 0.4,
    "graph_centrality": 0.3,
    "symbol_overlap": 0.2,
    "recency": 0.1,
}

# Recency-Decay: Halbwertszeit in Sekunden (90 Tage).
# Edges älter als 4× Halbwertszeit bekommen Score ≈ 0.05.
_RECENTLY_HALFLIFE_SEC = 90.0 * 24.0 * 3600.0

# Tokenizer für symbol_overlap: Wörter ≥3 Zeichen, lowercase
_TOKEN_RE = re.compile(r"\b\w{3,}\b")
_STOPWORDS = {
    "der", "die", "das", "und", "oder", "ist", "sind", "wird", "wurde",
    "the", "and", "for", "with", "this", "that", "from", "have", "has",
    "von", "mit", "auf", "ein", "eine", "einer", "eines", "einem", "einen",
    "was", "wie", "wer", "wo", "wann", "warum", "wieso", "weshalb",
}


@dataclass
class ScoredFact:
    """Fact + finaler Heuristic-Score. Output des Re-Rankers."""
    fact: Fact
    score: float
    components: dict[str, float]  # debugging/inspection


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOPWORDS}


def _cosine_score(fact: Fact, query_emb: np.ndarray | None) -> float:
    """Cosinus-Similarity (0..1). Normalisiert: 0.5*(cos+1) damit [-1,1] → [0,1]."""
    if query_emb is None or fact.embedding is None:
        return 0.0
    a = np.asarray(query_emb, dtype=np.float64).ravel()
    b = np.asarray(fact.embedding, dtype=np.float64).ravel()
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return 0.0
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    cos = float(np.dot(a, b) / (na * nb))
    # clamp + map [-1, 1] → [0, 1]
    return max(0.0, min(1.0, 0.5 * (cos + 1.0)))


def _graph_centrality_score(fact: Fact, all_facts: list[Fact]) -> float:
    """PageRank-Heuristik: Anzahl gleicher/wiederholter Themen im Subgraph (0..1).

    Da wir keine zentralen PageRank-Datenstrukturen haben, nähern wir:
        centrality ≈ |{f ∈ all_facts : token_overlap(f, fact) > 0.1}| / total
    d.h. je mehr thematisch verwandte Facts existieren, desto "zentraler" ist
    dieser Fact. Clamped auf 1.0.
    """
    if not all_facts:
        return 0.0
    fact_tokens = _tokenize(fact.text)
    if not fact_tokens:
        return 0.0
    related = 0
    for other in all_facts:
        if other.id == fact.id:
            continue
        other_tokens = _tokenize(other.text)
        if not other_tokens:
            continue
        overlap = len(fact_tokens & other_tokens) / max(1, min(len(fact_tokens), len(other_tokens)))
        if overlap > 0.1:
            related += 1
    return min(1.0, related / max(1, len(all_facts) - 1))


def _symbol_overlap_score(fact: Fact, query: str) -> float:
    """Symbol-Overlap: |query_tokens ∩ fact_tokens| / |query_tokens| (0..1)."""
    q_tokens = _tokenize(query)
    f_tokens = _tokenize(fact.text)
    if not q_tokens:
        return 0.0
    return len(q_tokens & f_tokens) / len(q_tokens)


def _recency_score(fact: Fact, now: float | None = None) -> float:
    """Recency-Decay: 1.0 = jetzt, → 0 mit Halbwertszeit ~90 Tagen."""
    if now is None:
        now = time.time()
    if fact.valid_at <= 0.0:
        return 0.5  # neutral wenn unbekannt
    age = max(0.0, now - fact.valid_at)
    return float(0.5 ** (age / _RECENTLY_HALFLIFE_SEC))


class HeuristicReranker:
    """Heuristik-basierter Re-Ranker.

    Args:
        weights: Optional dict mit 4 Keys (siehe DEFAULT_WEIGHTS). Falls Summe ≠ 1.0
                 werden die Gewichte intern normalisiert (Summe = 1).
        now: Override für "jetzt" (nur für Tests, sonst time.time()).
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        now: Optional[float] = None,
    ):
        if weights is None:
            self.weights = dict(DEFAULT_WEIGHTS)
        else:
            # Merge mit defaults (Caller kann Teilmenge überschreiben)
            self.weights = {**DEFAULT_WEIGHTS, **weights}
        # Normalisieren auf Summe=1
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError(f"weights must be positive, got {weights!r}")
        self.weights = {k: v / total for k, v in self.weights.items()}
        self._now = now

    def rerank(
        self,
        candidates: list[Fact],
        query: str,
        query_emb: np.ndarray | None = None,
    ) -> list[ScoredFact]:
        """Re-Rankt eine Liste von Fact-Candidates nach Heuristik-Score.

        Args:
            candidates: Liste von Fact-Objekten (Output aus Vector + Graph + Symbolic).
            query: Original-Query-Text (für symbol_overlap).
            query_emb: Optional Embedding der Query (für cosine). Falls None, cosine=0.

        Returns:
            Liste von ScoredFact, sortiert nach score absteigend.
        """
        if not candidates:
            return []

        scored: list[ScoredFact] = []
        for fact in candidates:
            components = {
                "cosine": _cosine_score(fact, query_emb),
                "graph_centrality": _graph_centrality_score(fact, candidates),
                "symbol_overlap": _symbol_overlap_score(fact, query),
                "recency": _recency_score(fact, self._now),
            }
            score = sum(self.weights[k] * components[k] for k in self.weights)
            scored.append(ScoredFact(fact=fact, score=float(score), components=components))

        scored.sort(key=lambda s: s.score, reverse=True)
        return scored

    def score_one(
        self,
        fact: Fact,
        query: str,
        query_emb: np.ndarray | None = None,
        all_facts: list[Fact] | None = None,
    ) -> ScoredFact:
        """Convenience: einzelner Fact scoren (z.B. für Tests)."""
        if all_facts is None:
            all_facts = [fact]
        components = {
            "cosine": _cosine_score(fact, query_emb),
            "graph_centrality": _graph_centrality_score(fact, all_facts),
            "symbol_overlap": _symbol_overlap_score(fact, query),
            "recency": _recency_score(fact, self._now),
        }
        score = sum(self.weights[k] * components[k] for k in self.weights)
        return ScoredFact(fact=fact, score=float(score), components=components)


__all__ = ["HeuristicReranker", "ScoredFact", "DEFAULT_WEIGHTS"]
