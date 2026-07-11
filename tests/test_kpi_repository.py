"""Tests für TKG Phase 4: KpiRepository + ReplayHarness.

Pattern analog zu test_memory_tkg.py: tempfile.mkdtemp() für DB-Isolation.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from gnom_hub.benchmark import ReplayHarness, ReplayResult
from gnom_hub.memory.kpi_repository import (
    KpiRecord,
    KpiRepository,
)
from gnom_hub.memory_tkg.in_memory_backend import InMemoryBackend
from gnom_hub.memory_tkg.retrieval_engine import RetrievalEngine


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def kpi_db_path(tmp_path):
    """Temporäre DB-Pfad im pytest-tmp_path (per-Test Isolation)."""
    return str(tmp_path / "kpi_test.db")


@pytest.fixture
def kpi_repo(kpi_db_path):
    """Frische KpiRepository-Instanz pro Test."""
    repo = KpiRepository(kpi_db_path)
    yield repo
    # Cleanup: temporäre DB-Dateien (tmp_path wird auto-cleanup, aber WAL-Files explizit)
    for suffix in ("", "-shm", "-wal", "-journal"):
        p = Path(kpi_db_path + suffix)
        if p.exists():
            p.unlink()


@pytest.fixture
def example_log_path():
    """Pfad zur mitgelieferten example_log.json (für Replay-Test)."""
    return str(Path(__file__).resolve().parent.parent / "src" / "gnom_hub" / "benchmark" / "example_log.json")


@pytest.fixture
def backend():
    """In-Memory TKG-Backend (kein KuzuDB-Overhead für Replay-Tests)."""
    b = InMemoryBackend()
    yield b
    b.close()


@pytest.fixture
def fake_emb(monkeypatch):
    """Patch `get_text_embedding` so der Vector-Path in Tests funktioniert."""
    cache: dict[str, np.ndarray] = {}

    def _fake(text: str):
        if text in cache:
            return cache[text]
        h = abs(hash(text))
        np.random.seed(h % (2**32))
        v = np.random.rand(384).astype(np.float64)
        v /= np.linalg.norm(v) + 1e-12
        cache[text] = v
        return v

    monkeypatch.setattr(
        "gnom_hub.memory_tkg.retrieval_engine.get_text_embedding",
        _fake,
    )
    monkeypatch.setattr(
        "gnom_hub.memory_tkg.backend.get_text_embedding",
        _fake,
    )
    return _fake


# ── KpiRepository Tests ────────────────────────────────────────────────────


def test_record_and_query(kpi_repo):
    """Roundtrip: record() → query() liefert exakt 1 Record."""
    rec = KpiRecord(name="avg_latency_ms", value=42.5, agent="coderag", ab_group="control")
    rid = kpi_repo.record(rec)
    assert rid > 0

    out = kpi_repo.query("avg_latency_ms", window_hours=24)
    assert len(out) == 1
    assert out[0].name == "avg_latency_ms"
    assert out[0].value == 42.5
    assert out[0].agent == "coderag"
    assert out[0].ab_group == "control"
    assert out[0].timestamp > 0.0


def test_query_with_window(kpi_repo):
    """window_hours filtert nach Zeit: 1h cutoff, älterer Record fällt raus."""
    now = time.time()
    # Alter Record: 48h her (außerhalb 24h-Fenster)
    old = KpiRecord(name="old_kpi", value=1.0, timestamp=now - 48 * 3600)
    # Frischer Record: jetzt
    fresh = KpiRecord(name="old_kpi", value=2.0, timestamp=now)

    kpi_repo.record(old)
    kpi_repo.record(fresh)

    out_24h = kpi_repo.query("old_kpi", window_hours=24)
    assert len(out_24h) == 1
    assert out_24h[0].value == 2.0

    out_72h = kpi_repo.query("old_kpi", window_hours=72)
    assert len(out_72h) == 2


def test_query_by_agent(kpi_repo):
    """Agent-Filter: records von 'coderag' vs. 'researcherag' sind getrennt."""
    kpi_repo.record(KpiRecord(name="latency", value=10.0, agent="coderag"))
    kpi_repo.record(KpiRecord(name="latency", value=20.0, agent="researcherag"))
    kpi_repo.record(KpiRecord(name="latency", value=30.0, agent="coderag"))

    out_coderag = kpi_repo.query("latency", agent="coderag")
    assert len(out_coderag) == 2
    assert all(r.agent == "coderag" for r in out_coderag)

    out_researcher = kpi_repo.query("latency", agent="researcherag")
    assert len(out_researcher) == 1
    assert out_researcher[0].value == 20.0

    out_all = kpi_repo.query("latency")
    assert len(out_all) == 3


def test_record_with_ab_group_treatment(kpi_repo):
    """ab_group='treatment' Records können separat abgefragt werden."""
    kpi_repo.record(KpiRecord(name="precision", value=0.85, ab_group="control"))
    kpi_repo.record(KpiRecord(name="precision", value=0.92, ab_group="treatment"))

    control = kpi_repo.query("precision", ab_group="control")
    treatment = kpi_repo.query("precision", ab_group="treatment")

    assert len(control) == 1 and control[0].value == 0.85
    assert len(treatment) == 1 and treatment[0].value == 0.92


def test_record_metadata_persists(kpi_repo):
    """metadata-Dict wird als JSON persistiert und round-tripped."""
    rec = KpiRecord(
        name="replay_metric",
        value=99.0,
        agent="replay_harness",
        metadata={"log_file": "/tmp/foo.json", "n_queries": 7},
    )
    kpi_repo.record(rec)

    out = kpi_repo.query("replay_metric")
    assert len(out) == 1
    assert out[0].metadata == {"log_file": "/tmp/foo.json", "n_queries": 7}


def test_latest_returns_most_recent(kpi_repo):
    """latest() liefert den Record mit höchstem timestamp."""
    kpi_repo.record(KpiRecord(name="x", value=1.0, timestamp=time.time() - 100))
    kpi_repo.record(KpiRecord(name="x", value=2.0, timestamp=time.time() - 50))
    kpi_repo.record(KpiRecord(name="x", value=3.0, timestamp=time.time()))

    latest = kpi_repo.latest("x")
    assert latest is not None
    assert latest.value == 3.0


def test_count_method(kpi_repo):
    """count() ohne/mit Filter liefert korrekte Anzahl."""
    assert kpi_repo.count() == 0
    kpi_repo.record(KpiRecord(name="a", value=1.0))
    kpi_repo.record(KpiRecord(name="a", value=2.0))
    kpi_repo.record(KpiRecord(name="b", value=3.0))
    assert kpi_repo.count() == 3
    assert kpi_repo.count("a") == 2
    assert kpi_repo.count("b") == 1
    assert kpi_repo.count("nonexistent") == 0


def test_table_auto_ensured_on_init(tmp_path):
    """Constructor stellt sicher, dass Tabelle existiert (idempotent)."""
    db = str(tmp_path / "fresh.db")
    # Pre-Init: keine Tabelle
    import sqlite3
    with sqlite3.connect(db) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
    assert "kpi_metrics" not in tables

    # Init → Tabelle wird erstellt
    KpiRepository(db)
    with sqlite3.connect(db) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
    assert "kpi_metrics" in tables


# ── ReplayHarness Tests ────────────────────────────────────────────────────


def test_replay_harness_runs(kpi_repo, backend, fake_emb, example_log_path):
    """Full Replay: 7-Message-Log → user-Queries durch RetrievalEngine → KPIs."""
    # TKG mit ein paar Facts seeden, damit Retrieval etwas findet
    emb = np.array([0.1] * 384, dtype=np.float64)
    from gnom_hub.memory_tkg.models import Entity, Fact
    backend.upsert_entity(Entity(id="e1", name="FAISS", type="bug", importance=0.9, last_seen=0.0))
    backend.upsert_entity(Entity(id="e2", name="KuzuDB", type="code_id", importance=0.85, last_seen=0.0))
    backend.upsert_fact(Fact(
        id="f1", text="FAISS ABI break in numpy 2.2.6 was fixed by pin",
        embedding=emb, importance=0.9, valid_at=time.time() - 100,
    ))
    backend.upsert_fact(Fact(
        id="f2", text="KuzuDB replaces FAISS for vector search in TKG v4",
        embedding=emb * 0.8, importance=0.85, valid_at=time.time() - 50,
    ))

    engine = RetrievalEngine(backend, cache_size=4)
    harness = ReplayHarness(kpi_repo, engine, ab_group="control", log_path=example_log_path)
    result = harness.replay()

    # ── Result-Struktur ──────────────────────────────────────────────
    assert isinstance(result, ReplayResult)
    assert result.queries_run == 3  # 3 user-messages im example_log
    assert result.log_file == example_log_path
    assert result.started_at > 0
    assert result.duration_ms >= 0
    assert len(result.queries) == 3

    # ── Aggregierte Metriken ────────────────────────────────────────
    assert result.avg_latency_ms >= 0
    assert 0.0 <= result.retrieval_precision_at_5 <= 1.0
    assert 0.0 <= result.token_economy_pct <= 100.0

    # ── KPIs wurden persistiert ─────────────────────────────────────
    latest_avg = kpi_repo.latest("avg_latency_ms")
    assert latest_avg is not None and latest_avg.value == result.avg_latency_ms
    latest_p5 = kpi_repo.latest("retrieval_precision_at_5")
    assert latest_p5 is not None
    latest_token = kpi_repo.latest("token_economy_pct")
    assert latest_token is not None

    # Per-Query Latencies (eine pro user-query)
    query_latencies = kpi_repo.query("query_latency_ms")
    assert len(query_latencies) == 3


def test_replay_harness_empty_log(kpi_repo, backend, fake_emb, tmp_path):
    """Leeres Log → ReplayResult mit queries_run=0, kein Crash."""
    # Leeres Log schreiben
    empty_log = tmp_path / "empty.json"
    empty_log.write_text('{"name": "empty", "messages": []}', encoding="utf-8")

    engine = RetrievalEngine(backend, cache_size=2)
    harness = ReplayHarness(kpi_repo, engine, log_path=str(empty_log))
    result = harness.replay()

    assert result.queries_run == 0
    assert result.avg_latency_ms == 0.0
    assert result.queries == []
    # Keine KPIs geschrieben (wir schreiben aggregierte KPIs nicht, wenn 0 queries)
    assert kpi_repo.count("avg_latency_ms") == 0


def test_replay_harness_ab_group_from_log(kpi_repo, backend, fake_emb, tmp_path):
    """A/B-Group aus dem Log-File überschreibt default."""
    log = tmp_path / "treatment_log.json"
    log.write_text(json_dumps := (
        '{"name": "t", "ab_group": "treatment", "messages": ['
        '{"id": "m1", "sender": "user", "agent": "coderag", "content": "test query"}]}'
    ), encoding="utf-8")

    engine = RetrievalEngine(backend, cache_size=2)
    harness = ReplayHarness(kpi_repo, engine, ab_group="control", log_path=str(log))
    assert harness.ab_group == "control"  # initial
    result = harness.replay()
    assert result.ab_group == "treatment"  # überschrieben aus Log
    # KPI wurde mit treatment ab_group geschrieben
    latest = kpi_repo.latest("queries_run")
    assert latest is not None and latest.ab_group == "treatment"


# ── API-Endpoint Tests (Smoke) ──────────────────────────────────────────────


def test_api_memory_kpis_endpoint_serves_json(monkeypatch, kpi_repo, tmp_path):
    """GET /api/memory/kpis liefert valides JSON-Schema."""
    # Hub-Default-DB-Pfad auf temp umlenken, damit Endpoint unsere Test-DB sieht
    fake_db = str(tmp_path / "api_test.db")
    fake_kpi_repo = KpiRepository(fake_db)
    fake_kpi_repo.record(KpiRecord(name="retrieval_precision_at_5", value=0.87, agent="coderag"))
    fake_kpi_repo.record(KpiRecord(name="avg_latency_ms", value=120.0, agent="coderag"))

    # Patch die Default-Repo-Factory im Endpoint-Modul
    import gnom_hub.api.endpoints.memory_kpis as ep
    monkeypatch.setattr(ep, "_get_default_repo", lambda: fake_kpi_repo)
    monkeypatch.setenv("MEMORY_AB_GROUP", "control")

    # FastAPI TestClient
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(ep.router)
    client = TestClient(app)

    # Einzelner KPI
    r1 = client.get("/api/memory/kpis?kpi=avg_latency_ms&window=24h")
    assert r1.status_code == 200
    body = r1.json()
    assert "kpis" in body
    assert "ab_group" in body and body["ab_group"] == "control"
    assert "window_hours" in body and body["window_hours"] == 24
    assert "avg_latency_ms" in body["kpis"]
    assert body["kpis"]["avg_latency_ms"]["count"] == 1
    assert body["kpis"]["avg_latency_ms"]["avg"] == 120.0

    # Alle KPIs
    r2 = client.get("/api/memory/kpis?window=24h")
    assert r2.status_code == 200
    body2 = r2.json()
    assert "avg_latency_ms" in body2["kpis"]
    assert "retrieval_precision_at_5" in body2["kpis"]

    # Bad ab_group → 400
    r3 = client.get("/api/memory/kpis?ab_group=invalid")
    assert r3.status_code == 400


def test_api_window_parsing(monkeypatch, tmp_path):
    """Window-Suffix-Parser: 7d → 168h, 1w → 168h, 30m → 1h."""
    import gnom_hub.api.endpoints.memory_kpis as ep
    assert ep._parse_window("24h") == 24
    assert ep._parse_window("7d") == 168
    assert ep._parse_window("1w") == 168
    assert ep._parse_window("30m") == 1  # 30 min, max(1, 30/60=0.5) → 1
    assert ep._parse_window("60m") == 1  # 60 min = 1h
    assert ep._parse_window("garbage") == 24  # default fallback


def test_api_ab_group_env_var(monkeypatch):
    """MEMORY_AB_GROUP env var steuert Default ab_group."""
    import gnom_hub.api.endpoints.memory_kpis as ep
    monkeypatch.setenv("MEMORY_AB_GROUP", "treatment")
    assert ep._resolve_ab_group() == "treatment"
    monkeypatch.setenv("MEMORY_AB_GROUP", "control")
    assert ep._resolve_ab_group() == "control"
    monkeypatch.setenv("MEMORY_AB_GROUP", "garbage")
    assert ep._resolve_ab_group() == "control"  # invalid → fallback
    monkeypatch.delenv("MEMORY_AB_GROUP")
    assert ep._resolve_ab_group() == "control"  # unset → default
