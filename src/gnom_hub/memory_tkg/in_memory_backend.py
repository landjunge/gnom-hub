"""In-Memory-Backend für Tests. Dicts + brute-force numpy Cosine."""
from __future__ import annotations
import numpy as np
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation


class InMemoryBackend:
    def __init__(self):
        self._entities: dict[str, Entity] = {}
        self._facts: dict[str, Fact] = {}
        self._relations: list[Relation] = []
        self._mentions: dict[str, dict[str, float]] = {}

    def upsert_entity(self, e: Entity) -> str:
        self._entities[e.id] = e
        return e.id

    def upsert_fact(self, f: Fact) -> str:
        self._facts[f.id] = f
        return f.id

    def add_relation(self, r: Relation) -> str:
        # Bitemporal-Split: aktive Relation mit gleichem (from, predicate, to) invalidieren.
        for ex in self._relations:
            if (ex.from_id == r.from_id and ex.predicate == r.predicate
                    and ex.to_id == r.to_id and ex.invalid_at is None):
                ex.invalid_at = r.valid_at
        self._relations.append(r)
        return f"{r.from_id}:{r.predicate}:{r.to_id}@{r.valid_at}"

    def add_mention(self, m: Mention) -> str:
        self._mentions.setdefault(m.fact_id, {})[m.entity_id] = m.confidence
        return f"{m.fact_id}->{m.entity_id}"

    def get_entity(self, id: str) -> Entity | None:
        return self._entities.get(id)

    def get_fact(self, id: str) -> Fact | None:
        return self._facts.get(id)

    def find_entities_by_name(self, name: str) -> list[Entity]:
        return [e for e in self._entities.values() if e.name == name]

    def search_facts_by_vector(self, emb: np.ndarray, k: int = 10) -> list[Fact]:
        scored = [(self._cosine(emb, f.embedding), f) for f in self._facts.values()
                  if f.embedding is not None]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:k]]

    def find_facts_mentioning(self, entity_id: str) -> list[Fact]:
        return [self._facts[fid] for fid, ents in self._mentions.items()
                if entity_id in ents and fid in self._facts]

    def find_relations(self, from_id: str, predicate: str | None = None) -> list[Relation]:
        return [r for r in self._relations if r.from_id == from_id
                and (predicate is None or r.predicate == predicate)]

    def find_facts_valid_at(self, t: float) -> list[Fact]:
        return [f for f in self._facts.values()
                if f.valid_at <= t and (f.invalid_at is None or f.invalid_at > t)]

    def count(self) -> int:
        return len(self._entities) + len(self._facts)

    def close(self) -> None:
        pass

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
