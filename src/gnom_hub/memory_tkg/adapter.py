"""Strangler Adapter: Legacy Memory-API → MemoryBackend.

Schlanker Übersetzer, keine eigene Logik. Jede Funktion mappt 1:1 auf
eine Backend-Methode, damit alte Callsites schrittweise migriert werden
können ohne Big-Bang-Rewrite.
"""
from __future__ import annotations

import time
import uuid

from gnom_hub.memory_tkg.backend import get_memory_backend, get_text_embedding
from gnom_hub.memory_tkg.models import Fact, Mention


def _now() -> float:
    return time.time()


# Alt: add_to_soul_memory(fact, priority, agent)  →  Neu: upsert_fact(Fact)
def store_memory(text: str, importance: float = 0.6) -> str:
    fact = Fact(
        id=str(uuid.uuid4()),
        text=text,
        embedding=get_text_embedding(text),
        importance=importance,
        valid_at=_now(),
    )
    return get_memory_backend().upsert_fact(fact)


# Alt: retrieve_relevant_facts(query, agent_name, top_k)  →  Neu: search_facts_by_vector
def retrieve_relevant(query: str, top_k: int = 8) -> list[str]:
    emb = get_text_embedding(query)
    if emb is None:
        return []
    facts = get_memory_backend().search_facts_by_vector(emb, k=top_k)
    return [f.text for f in facts]


# Alt: _fetch_recent(agent_name, limit)  →  Neu: find_facts_valid_at(now)
def get_recent_facts(limit: int = 15) -> list[str]:
    facts = get_memory_backend().find_facts_valid_at(_now())
    facts.sort(key=lambda f: f.valid_at, reverse=True)
    return [f.text for f in facts[:limit]]


# Alt: MENTIONS-Logik in add_fact_with_entity  →  Neu: add_mention(Mention)
def add_mention(fact_id: str, entity_name: str, confidence: float = 0.8) -> str | None:
    backend = get_memory_backend()
    entities = backend.find_entities_by_name(entity_name)
    if not entities:
        return None
    mention = Mention(
        fact_id=fact_id,
        entity_id=entities[0].id,
        confidence=confidence,
    )
    return backend.add_mention(mention)


# Alt: save_soul_fact_smart(key, value, agent, priority) → Jaccard-Dedup
# Phase 2: nutzt Backend.has_similar_fact für Embedding-basierte Similarity.
_PRIORITY_IMPORTANCE = {"low": 0.3, "medium": 0.6, "high": 0.75, "critical": 0.9}


def save_soul_fact_smart(
    key: str,
    value: str,
    agent: str = "SoulAG",
    priority: str = "medium",
) -> str | None:
    if get_memory_backend().has_similar_fact(value):
        return key
    store_memory(value, importance=_PRIORITY_IMPORTANCE.get(priority, 0.5))
    return key


__all__ = ["store_memory", "retrieve_relevant", "get_recent_facts", "add_mention", "save_soul_fact_smart"]