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
    """Embedding-Generierung mit Hash-Fallback.

    Versucht zuerst den echten LLM-Embedder (SoulEmbedder). Falls der nicht
    verfügbar ist (z.B. sentence-transformers nicht installiert), wird ein
    deterministischer Hash-basierter Embedder verwendet — so dass die
    Pipeline IMMER funktioniert, nur mit schlechterer semantischer Qualität.

    Returns:
        np.ndarray of shape (384,) dtype float32. Niemals None.
    """
    DIM = 384
    try:
        from gnom_hub.memory.embeddings import get_embedder
        embedder = get_embedder()
        if embedder is not None and hasattr(embedder, "embed_text"):
            emb = embedder.embed_text(text)
            if emb is not None:
                return np.asarray(emb, dtype=np.float32)
    except Exception as e:  # noqa: BLE001
        _log.info("Real embedder unavailable (%s), using hash fallback", e)

    # Hash-basierter Fallback: deterministisch, normalisiert, 384-dim
    import hashlib
    h = hashlib.sha512(text.encode("utf-8")).digest()
    # 64 bytes = 512 bits, brauchen 384 floats → jeden 4. Byte zu 3 floats
    vec = np.zeros(DIM, dtype=np.float32)
    for i in range(DIM):
        # bytes[i % len(h)] mod 256 / 255 → [0, 1]
        vec[i] = (h[i % len(h)] ^ h[(i * 7 + 13) % len(h)]) / 255.0
    # Normalisieren
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


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
