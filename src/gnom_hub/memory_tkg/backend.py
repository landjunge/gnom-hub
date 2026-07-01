"""MemoryBackend Protocol + Factory + Embedding-Helper (v4 simplified, MENTIONS-aware)."""
from __future__ import annotations

import logging
import os
import threading
from typing import Protocol, runtime_checkable

import numpy as np

from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation

_log = logging.getLogger(__name__)


def get_text_embedding(text: str) -> np.ndarray | None:
    """Embedding-Generierung mit klarem Fehler-Verhalten.

    Returns np.ndarray on success, None wenn Embedder nicht verfügbar.
    Bei Fail wird ein Warning geloggt — kein stilles Fallback.
    """
    try:
        from gnom_hub.memory.embeddings import get_embedding
        return np.asarray(get_embedding(text), dtype=np.float32)
    except Exception as e:  # noqa: BLE001
        _log.warning("get_text_embedding failed (embedder unavailable?): %s", e)
        return None


@runtime_checkable
class MemoryBackend(Protocol):
    """TKG-Backend-Interface. Strukturelles Subtyping — keine Vererbung nötig."""

    # Writes
    def upsert_entity(self, entity: Entity) -> str: ...
    def upsert_fact(self, fact: Fact) -> str: ...
    def add_relation(self, relation: Relation) -> str: ...
    def add_mention(self, mention: Mention) -> str: ...

    # Reads
    def get_entity(self, id: str) -> Entity | None: ...
    def get_fact(self, id: str) -> Fact | None: ...
    def find_entities_by_name(self, name: str) -> list[Entity]: ...
    def search_facts_by_vector(self, embedding: np.ndarray, k: int = 10) -> list[Fact]: ...
    def find_facts_mentioning(self, entity_id: str) -> list[Fact]: ...
    def find_relations(self, from_id: str, predicate: str | None = None) -> list[Relation]: ...
    def find_facts_valid_at(self, at_time: float) -> list[Fact]: ...
    def has_similar_fact(self, text: str, threshold: float = 0.85) -> bool: ...

    # Meta
    def count(self) -> int: ...
    def close(self) -> None: ...


_cache: MemoryBackend | None = None
_lock = threading.Lock()


def get_memory_backend() -> MemoryBackend:
    """Singleton-Factory. Konfiguration via MEMORY_BACKEND in .env."""
    global _cache
    if _cache is not None:
        return _cache
    with _lock:
        if _cache is not None:
            return _cache
        name = os.getenv("MEMORY_BACKEND", "kuzu")
        if name == "kuzu":
            from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
            _cache = KuzuDBBackend(os.getenv("KUZU_DB_PATH", "data/memory.kuzu"))
        elif name == "in_memory":
            from gnom_hub.memory_tkg.in_memory_backend import InMemoryBackend
            _cache = InMemoryBackend()
        else:
            raise ValueError(f"Unknown MEMORY_BACKEND: {name!r}")
        return _cache


def reset_memory_backend() -> None:
    """Test-Hook: Backend-Cache leeren."""
    global _cache
    with _lock:
        if _cache is not None:
            try:
                _cache.close()
            except Exception as e:  # noqa: BLE001
                logging.warning("reset_memory_backend: close() failed: %s", e)
        _cache = None
