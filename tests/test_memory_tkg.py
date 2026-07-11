"""Tests für memory_tkg. Laufen automatisch gegen beide Backends."""
from __future__ import annotations

import tempfile
import time

import numpy as np
import pytest

pytest.importorskip("kuzu", reason="kuzu nicht installiert — TKG-Backend-Skip")

from gnom_hub.memory_tkg.backend import (
    MemoryBackend, get_memory_backend, reset_memory_backend,
)
from gnom_hub.memory_tkg.in_memory_backend import InMemoryBackend
from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention, Relation


@pytest.fixture(params=["kuzu", "in_memory"])
def backend(request):
    """Parametrized: jeder Test läuft gegen beide Backends."""
    if request.param == "kuzu":
        b = KuzuDBBackend(tempfile.mkdtemp() + "/test.kuzu")
    else:
        b = InMemoryBackend()
    yield b
    b.close()


@pytest.fixture
def emb():
    return np.array([0.1] * 384, dtype=np.float64)


def test_both_backends_satisfy_protocol():
    """Repository-Pattern-Beleg: beide Backends sind MemoryBackend-konform."""
    for b in [InMemoryBackend(), KuzuDBBackend(tempfile.mkdtemp() + "/x.kuzu")]:
        assert isinstance(b, MemoryBackend), f"{type(b).__name__} ist nicht Protocol-konform"


def test_upsert_get_entity(backend):
    backend.upsert_entity(Entity(id="e1", name="FAISS", type="bug", importance=0.8, last_seen=100.0))
    got = backend.get_entity("e1")
    assert got is not None and got.name == "FAISS" and got.importance == 0.8
    backend.upsert_entity(Entity(id="e1", name="FAISS", type="bug", importance=0.9, last_seen=200.0))
    assert backend.get_entity("e1").importance == 0.9


def test_upsert_fact_and_search(backend, emb):
    backend.upsert_fact(Fact(id="f1", text="A", embedding=emb, importance=0.5, valid_at=100.0, invalid_at=None))
    got = backend.get_fact("f1")
    assert got.text == "A" and np.allclose(got.embedding, emb)
    backend.upsert_fact(Fact(id="f1", text="B", embedding=emb, importance=0.7, valid_at=100.0, invalid_at=None))
    assert backend.get_fact("f1").text == "B" and backend.get_fact("f1").importance == 0.7
    hits = backend.search_facts_by_vector(emb, k=5)
    assert len(hits) >= 1 and hits[0].id == "f1"


def test_mention_roundtrip(backend, emb):
    backend.upsert_fact(Fact(id="f1", text="X", embedding=emb, importance=0.5, valid_at=100.0, invalid_at=None))
    backend.upsert_entity(Entity(id="e1", name="X", type="concept", importance=0.5, last_seen=0.0))
    backend.add_mention(Mention(fact_id="f1", entity_id="e1", confidence=0.9))
    facts = backend.find_facts_mentioning("e1")
    assert len(facts) == 1 and facts[0].id == "f1"


def test_bitemporal_relation(backend, emb):
    backend.upsert_fact(Fact(id="f1", text="A", embedding=emb, importance=0.5, valid_at=100.0, invalid_at=None))
    backend.upsert_fact(Fact(id="f2", text="B", embedding=emb, importance=0.5, valid_at=100.0, invalid_at=None))
    backend.add_relation(Relation(from_id="f1", to_id="f2", predicate="causes", valid_at=100.0, invalid_at=None))
    time.sleep(0.01)
    backend.add_relation(Relation(from_id="f1", to_id="f2", predicate="causes", valid_at=200.0, invalid_at=None))
    rels = backend.find_relations("f1", "causes")
    assert len(rels) == 2
    active = [r for r in rels if r.invalid_at is None]
    inactive = [r for r in rels if r.invalid_at is not None]
    assert len(active) == 1 and len(inactive) == 1
    assert active[0].valid_at == 200.0  # der jüngere ist aktiv


def test_reset_memory_backend(monkeypatch, tmp_path):
    """Factory-Singleton: gleicher Call → gleicher Instance; nach reset → neuer."""
    monkeypatch.setenv("KUZU_DB_PATH", str(tmp_path / "x.kuzu"))
    b1 = get_memory_backend()
    b2 = get_memory_backend()
    assert b1 is b2
    reset_memory_backend()
    b3 = get_memory_backend()
    assert b3 is not b1
    reset_memory_backend()  # cleanup
