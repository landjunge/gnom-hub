"""
Tests für /api/workflows* und /api/observability/metrics Endpoints.

Diese Tests wurden im Rahmen des Workflow-Page-Fix erstellt (Plan
plan_7b2e1a17 / workflow-page-fix). Sie decken ab:

  * Pydantic-Validierung von POST /api/workflows
  * 200/4xx-Verhalten aller Workflow-Endpoints
  * Frontend-Schema-Konformität (alle vom Frontend benötigten Felder)
  * Regression-Tests für die im Diagnose-Lauf entdeckten Bugs:
      - _record_wf_result → CoordinationDB.record_job() kwarg-Mismatch
      - POST-Erfolg trotz Dispatch-Failure
      - Fehlende Felder im Response (depends_on, error_summary, ...)
      - DAG-Renderer-null-Safety (capability, status)
      - Zyklische depends_on (kein Stack-Overflow)

Jeder Fix, der in dieser Aufgabe implementiert wurde, hat einen
korrespondierenden Test hier.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ── Schema-Helper (für Test-Setup + Frontend-Schema-Validierung) ────────────

REQUIRED_LIST_FIELDS = {"id", "name", "status", "created_at", "completed_at"}
REQUIRED_TASK_FIELDS = {
    "task_id", "capability", "input_template", "depends_on",
    "status", "msg_id", "result", "error_summary",
}
REQUIRED_WORKFLOW_FIELDS = {
    "id", "name", "status", "created_at", "completed_at", "tasks",
}
REQUIRED_OBS_METRICS_FIELDS = {
    "agents", "capabilities", "workflows_summary", "workflows",
}
REQUIRED_OBS_WORKFLOW_FIELDS = {
    "id", "name", "status", "created_at", "completed_at", "duration_s",
}


def _create_full_schema(db_path: Path) -> None:
    """Erstellt ein vollständiges, gnom-hub-konformes DB-Schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at REAL NOT NULL,
            completed_at REAL
        );
        CREATE TABLE IF NOT EXISTS workflow_tasks (
            workflow_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            capability TEXT NOT NULL,
            input_template TEXT NOT NULL,
            depends_on TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            msg_id INTEGER,
            result_json TEXT,
            error_summary TEXT,
            retry_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (workflow_id, task_id)
        );
        CREATE TABLE IF NOT EXISTS agent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT, recipient TEXT, payload TEXT,
            priority INTEGER DEFAULT 5, status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0, created_at REAL,
            deliver_after REAL DEFAULT 0, context_id TEXT, depth INTEGER DEFAULT 0,
            processing_since REAL DEFAULT NULL,
            parent_msg_id INTEGER DEFAULT NULL,
            completed_at REAL DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS agents (
            name TEXT PRIMARY KEY, id TEXT UNIQUE, port INTEGER DEFAULT 0,
            description TEXT DEFAULT '', status TEXT DEFAULT 'offline',
            capabilities TEXT DEFAULT '[]', role TEXT DEFAULT 'normal',
            active_job TEXT, last_seen TEXT,
            circuit_state TEXT DEFAULT 'CLOSED',
            consecutive_failures INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS agent_capabilities (
            agent_name TEXT NOT NULL,
            capability TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            PRIMARY KEY (agent_name, capability)
        );
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY, value TEXT
        );
    """)
    conn.commit()
    conn.close()


def _insert_workflow_directly(db_path: Path, wf_id: str, name: str,
                               status: str = "running",
                               created_at: float = 1700000000.0,
                               completed_at: float = None) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO workflows (id, name, status, created_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (wf_id, name, status, created_at, completed_at),
    )
    conn.commit()
    conn.close()


# ── Fixture: isolierte DB + TestClient ───────────────────────────────────────

@pytest.fixture
def full_db(tmp_path, monkeypatch):
    """Vollständige isolierte DB mit allen Tabellen für Workflow-Tests."""
    db_file = tmp_path / "test_workflows.db"
    _create_full_schema(db_file)

    # Pfade patchen, BEVOR die App importiert wird (aber sie ist schon importiert,
    # daher reicht das Patchen in der laufenden Session).
    monkeypatch.setattr("gnom_hub.core.config.DB_PATH", db_file)
    monkeypatch.setattr("gnom_hub.core.config.Config.DB_PATH", db_file)
    monkeypatch.setattr("gnom_hub.db.connection.Config.DB_PATH", db_file)
    return db_file


@pytest.fixture
def client(full_db):
    """FastAPI TestClient mit isolierter DB."""
    # TestClient muss innerhalb des Patches erzeugt werden, damit die
    # Connection-Patches wirksam sind.
    from fastapi.testclient import TestClient
    from gnom_hub.api.app import app
    return TestClient(app)


# ════════════════════════════════════════════════════════════════════════════
# Tests für GET /api/workflows
# ════════════════════════════════════════════════════════════════════════════


def test_01_list_workflows_returns_empty_array(client):
    """Empty-DB → leere Liste, kein 404 oder 500."""
    r = client.get("/api/workflows")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert body == []


def test_02_list_workflows_returns_inserted_workflow(client, full_db):
    """Eine eingefügte Workflow-Zeile wird zurückgegeben."""
    _insert_workflow_directly(full_db, "wf-1", "alpha", "running", 1700000000.0)
    r = client.get("/api/workflows")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    # Schema-Validierung: alle vom Frontend benötigten Felder vorhanden
    wf = body[0]
    missing = REQUIRED_LIST_FIELDS - set(wf.keys())
    assert not missing, f"Fehlende Felder: {missing}"
    assert wf["id"] == "wf-1"
    assert wf["name"] == "alpha"
    assert wf["status"] == "running"


def test_03_list_workflows_schema_compliance(client, full_db):
    """Schema-Konformität: jede Zeile hat genau die erwarteten Felder."""
    _insert_workflow_directly(full_db, "wf-A", "test-A", "completed", 1700000000.0, 1700000100.0)
    _insert_workflow_directly(full_db, "wf-B", "test-B", "failed",    1700000200.0, 1700000210.0)
    _insert_workflow_directly(full_db, "wf-C", "test-C", "running",   1700000300.0, None)
    r = client.get("/api/workflows")
    body = r.json()
    for wf in body:
        assert REQUIRED_LIST_FIELDS.issubset(set(wf.keys())), \
            f"Workflow {wf} fehlt Felder: {REQUIRED_LIST_FIELDS - set(wf.keys())}"
        # created_at darf float (Unix-ts) ODER string (ISO) sein, aber nicht None
        assert wf["created_at"] is not None, "created_at ist None"


# ════════════════════════════════════════════════════════════════════════════
# Tests für POST /api/workflows — Pydantic-Validierung
# ════════════════════════════════════════════════════════════════════════════


def test_04_post_empty_body_returns_422(client):
    """Leerer Body → 422 (Pydantic-Validation), nicht 500."""
    r = client.post("/api/workflows", json={})
    assert r.status_code == 422, r.text
    body = r.json()
    assert "detail" in body
    # Mindestens ein Validation-Error
    assert isinstance(body["detail"], list) and len(body["detail"]) > 0


def test_05_post_empty_tasks_returns_422(client):
    """tasks:[] → 422 (Field min_length=1), nicht 500."""
    r = client.post("/api/workflows", json={"name": "test", "tasks": []})
    assert r.status_code == 422
    detail = r.json()["detail"]
    # Pydantic meldet min_length für 'tasks'
    assert any("tasks" in str(d.get("loc", "")) for d in detail)


def test_06_post_duplicate_task_ids_returns_422(client):
    """Doppelte task_id → 422 mit klarer Fehlermeldung."""
    r = client.post("/api/workflows", json={
        "name": "test",
        "tasks": [
            {"task_id": "a", "capability": "general", "input_template": "x"},
            {"task_id": "a", "capability": "general", "input_template": "y"},
        ],
    })
    assert r.status_code == 422
    detail = r.json()["detail"]
    msg_blob = json.dumps(detail)
    assert "Duplicate" in msg_blob or "duplicate" in msg_blob


def test_07_post_self_dependency_returns_422(client):
    """Task der von sich selbst abhängt → 422."""
    r = client.post("/api/workflows", json={
        "name": "test",
        "tasks": [
            {"task_id": "a", "capability": "general",
             "input_template": "x", "depends_on": ["a"]},
        ],
    })
    assert r.status_code == 422
    msg_blob = json.dumps(r.json()["detail"])
    assert "self" in msg_blob.lower()


def test_08_post_empty_task_id_returns_422(client):
    """task_id='' → 422 (Field min_length=1)."""
    r = client.post("/api/workflows", json={
        "name": "test",
        "tasks": [
            {"task_id": "", "capability": "general", "input_template": "x"},
        ],
    })
    assert r.status_code == 422


def test_09_post_valid_workflow_returns_200(client, full_db):
    """Valides Workflow-Payload → 200 mit workflow_id + workflow_status."""
    r = client.post("/api/workflows", json={
        "name": "test-wf",
        "tasks": [
            {"task_id": "t1", "capability": "general", "input_template": "hello"},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    # Schema-Konformität: alle vom Frontend benötigten Felder
    for k in ("status", "workflow_id", "workflow_status", "task_count", "dispatch_failed"):
        assert k in body, f"Feld {k!r} fehlt im POST-Response"
    assert isinstance(body["workflow_id"], str) and len(body["workflow_id"]) >= 16
    assert body["task_count"] == 1
    # Dispatch_failed=True weil kein Agent 'general' kann
    assert body["dispatch_failed"] is True
    assert body["status"] in ("partial", "success")
    # Workflow-Status muss nach evaluate_workflow auf 'failed' stehen (Task failed)
    assert body["workflow_status"] == "failed"


def test_10_post_workflow_appears_in_list(client, full_db):
    """Nach POST taucht der Workflow in GET /api/workflows auf."""
    r = client.post("/api/workflows", json={
        "name": "appearing-wf",
        "tasks": [
            {"task_id": "t1", "capability": "general", "input_template": "x"},
        ],
    })
    assert r.status_code == 200
    wf_id = r.json()["workflow_id"]

    r = client.get("/api/workflows")
    body = r.json()
    assert any(w["id"] == wf_id for w in body), "Workflow nicht in Liste"


# ════════════════════════════════════════════════════════════════════════════
# Tests für GET /api/workflows/{id}
# ════════════════════════════════════════════════════════════════════════════


def test_11_get_unknown_workflow_returns_404(client):
    """Unbekannte ID → 404 (nicht 500)."""
    r = client.get("/api/workflows/does-not-exist")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_12_get_workflow_returns_all_required_fields(client, full_db):
    """Workflow mit Tasks → alle vom Frontend benötigten Felder."""
    _insert_workflow_directly(full_db, "wf-X", "test-X", "running", 1700000000.0)

    # Tasks einfügen
    conn = sqlite3.connect(str(full_db))
    conn.execute(
        "INSERT INTO workflow_tasks (workflow_id, task_id, capability, "
        "input_template, depends_on, status, msg_id, result_json, error_summary) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("wf-X", "t1", "general", "Hello", "[]", "completed", 42, '{"content":"ok"}', None),
    )
    conn.execute(
        "INSERT INTO workflow_tasks (workflow_id, task_id, capability, "
        "input_template, depends_on, status, msg_id, result_json, error_summary) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("wf-X", "t2", "general", "Hi", '["t1"]', "failed", None, None, "[DISPATCH] No agent"),
    )
    conn.commit()
    conn.close()

    r = client.get("/api/workflows/wf-X")
    assert r.status_code == 200
    body = r.json()

    # Workflow-Felder
    missing_wf = REQUIRED_WORKFLOW_FIELDS - set(body.keys())
    assert not missing_wf, f"Workflow fehlt Felder: {missing_wf}"
    assert body["id"] == "wf-X"
    assert body["name"] == "test-X"

    # Tasks
    assert isinstance(body["tasks"], list)
    assert len(body["tasks"]) == 2
    for t in body["tasks"]:
        missing = REQUIRED_TASK_FIELDS - set(t.keys())
        assert not missing, f"Task {t} fehlt Felder: {missing}"
        # depends_on muss Array sein (Frontend ruft .length darauf)
        assert isinstance(t["depends_on"], list), \
            f"depends_on muss Liste sein, ist {type(t['depends_on']).__name__}"


def test_13_get_workflow_handles_empty_capability(client, full_db):
    """Regression: capability darf leer sein — Backend liefert '' (Frontend
    ruft .toUpperCase() darauf auf, null würde crashen)."""
    _insert_workflow_directly(full_db, "wf-Y", "test-Y", "running", 1700000000.0)
    conn = sqlite3.connect(str(full_db))
    conn.execute(
        "INSERT INTO workflow_tasks (workflow_id, task_id, capability, "
        "input_template, depends_on, status) "
        "VALUES (?, ?, '', ?, ?, ?)",
        ("wf-Y", "t1", "x", "[]", "pending"),
    )
    conn.commit()
    conn.close()

    r = client.get("/api/workflows/wf-Y")
    assert r.status_code == 200
    task = r.json()["tasks"][0]
    # Frontend ruft t.capability.toUpperCase() — wenn null → TypeError.
    # Backend muss daher '' oder einen Default liefern, nicht null.
    assert task["capability"] is not None, "capability darf nicht null sein (Frontend-Safety)"
    assert task["status"] is not None


def test_14_get_workflow_handles_invalid_depends_on_json(client, full_db):
    """Robustheit: kaputtes JSON in depends_on → leere Liste, nicht 500."""
    _insert_workflow_directly(full_db, "wf-Z", "test-Z", "running", 1700000000.0)
    conn = sqlite3.connect(str(full_db))
    conn.execute(
        "INSERT INTO workflow_tasks (workflow_id, task_id, capability, "
        "input_template, depends_on, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("wf-Z", "t1", "general", "x", "{broken json[", "pending"),
    )
    conn.commit()
    conn.close()

    r = client.get("/api/workflows/wf-Z")
    assert r.status_code == 200, r.text
    task = r.json()["tasks"][0]
    assert task["depends_on"] == [], f"depends_on muss [] sein, ist {task['depends_on']}"


# ════════════════════════════════════════════════════════════════════════════
# Regression-Tests für die im Diagnose-Lauf entdeckten Bugs
# ════════════════════════════════════════════════════════════════════════════


def test_15_workflow_result_recording_no_typeerror(client, full_db, caplog):
    """Regression: _record_wf_result ruft CoordinationDB.record_job mit den
    RICHTIGEN kwargs auf (worker, task_summary, result, duration_s, context_id, notes).
    Vor dem Fix wurden kwargs wie workflow_id/task_chain übergeben → TypeError.
    """
    # Wenn wir einen Workflow POSTen der dispatched wird (oder fehlschlägt),
    # darf KEIN TypeError über die 'unexpected keyword'-Schiene geloggt werden.
    import logging
    caplog.set_level(logging.WARNING, logger="gnom_hub.agents.swarm.workflow_engine")

    r = client.post("/api/workflows", json={
        "name": "regression-test",
        "tasks": [
            {"task_id": "t1", "capability": "general", "input_template": "x"},
        ],
    })
    assert r.status_code == 200
    # KEIN 'unexpected keyword argument'-Fehler im Log
    bad_logs = [rec for rec in caplog.records
                if "unexpected keyword" in str(rec.getMessage()).lower()
                or "record_job()" in str(rec.getMessage())]
    assert not bad_logs, \
        f"record_job-Kwarg-Bug taucht wieder auf: {[r.getMessage() for r in bad_logs]}"


def test_16_post_returns_partial_status_on_dispatch_failure(client, full_db):
    """Regression: POST /api/workflows liefert NICHT 'success' wenn dispatch_failed.
    Vor dem Fix: immer 'success', auch wenn Workflow intern failed.
    """
    r = client.post("/api/workflows", json={
        "name": "dispatch-fail-test",
        "tasks": [
            {"task_id": "t1", "capability": "general", "input_template": "x"},
        ],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["dispatch_failed"] is True
    assert body["workflow_status"] == "failed"
    assert body["status"] == "partial"  # NICHT "success"


def test_17_get_observability_metrics_returns_required_keys(client, full_db):
    """Observability-Endpoint muss alle vom Frontend benötigten Top-Level-Keys liefern."""
    r = client.get("/api/observability/metrics")
    assert r.status_code == 200, r.text
    body = r.json()
    missing = REQUIRED_OBS_METRICS_FIELDS - set(body.keys())
    assert not missing, f"Fehlende Top-Level-Felder: {missing}"

    # workflows_summary muss die 4 vom Frontend erwarteten Felder haben
    summary = body["workflows_summary"]
    for k in ("total_count", "completed_count", "failed_count", "avg_duration_s"):
        assert k in summary, f"workflows_summary.{k} fehlt"


def test_18_get_observability_workflow_schema(client, full_db):
    """Jeder Workflow in observability/workflows hat die richtigen Felder."""
    _insert_workflow_directly(full_db, "wf-O", "obs-test", "completed",
                               created_at=1700000000.0, completed_at=1700000010.0)
    r = client.get("/api/observability/metrics")
    assert r.status_code == 200
    body = r.json()
    # Wenn es Workflows gibt, müssen sie schema-konform sein
    if body.get("workflows"):
        for w in body["workflows"]:
            missing = REQUIRED_OBS_WORKFLOW_FIELDS - set(w.keys())
            assert not missing, f"Observability-Workflow fehlt Felder: {missing}"


def test_19_post_status_field_normalization(client, full_db):
    """Regression: Falls DB status leer ist, normalisiert das Backend auf 'pending'."""
    _insert_workflow_directly(full_db, "wf-null", "null-status-test", "", 1700000000.0)
    r = client.get("/api/workflows")
    assert r.status_code == 200
    body = r.json()
    # Falls status leer war (NULL oder ''), wird er auf 'pending' normalisiert
    wf = next(w for w in body if w["id"] == "wf-null")
    assert wf["status"] in ("pending",), \
        f"status wurde nicht normalisiert, ist {wf['status']!r}"


# ════════════════════════════════════════════════════════════════════════════
# Frontend-Schema-Validator (für Verifikations-Step)
# ════════════════════════════════════════════════════════════════════════════


def test_20_frontend_schema_validator_runs(client, full_db):
    """End-to-End-Smoke: POST → GET list → GET detail, alle Felder vorhanden."""
    # 1. POST
    r = client.post("/api/workflows", json={
        "name": "schema-smoke",
        "tasks": [
            {"task_id": "t1", "capability": "general", "input_template": "x"},
            {"task_id": "t2", "capability": "general", "input_template": "y",
             "depends_on": ["t1"]},
        ],
    })
    assert r.status_code == 200
    wf_id = r.json()["workflow_id"]

    # 2. GET list
    r = client.get("/api/workflows")
    assert r.status_code == 200
    list_body = r.json()
    assert isinstance(list_body, list)
    wf_in_list = next((w for w in list_body if w["id"] == wf_id), None)
    assert wf_in_list is not None
    missing = REQUIRED_LIST_FIELDS - set(wf_in_list.keys())
    assert not missing, f"List-Schema fehlt: {missing}"

    # 3. GET detail
    r = client.get(f"/api/workflows/{wf_id}")
    assert r.status_code == 200
    detail = r.json()
    missing_wf = REQUIRED_WORKFLOW_FIELDS - set(detail.keys())
    assert not missing_wf, f"Detail-Schema fehlt: {missing_wf}"
    assert isinstance(detail["tasks"], list)
    for t in detail["tasks"]:
        missing_t = REQUIRED_TASK_FIELDS - set(t.keys())
        assert not missing_t, f"Task-Schema fehlt: {missing_t}"
        assert isinstance(t["depends_on"], list)

    # 4. Observability ebenfalls prüfen
    r = client.get("/api/observability/metrics")
    assert r.status_code == 200
    obs = r.json()
    missing_obs = REQUIRED_OBS_METRICS_FIELDS - set(obs.keys())
    assert not missing_obs, f"Observability-Schema fehlt: {missing_obs}"
    print(f"\n✓ Schema-Smoke bestanden — {wf_id} hat alle Felder")


# ════════════════════════════════════════════════════════════════════════════
# DAG-Renderer-Safety (Frontend-Logik als Python-Spiegel, smoke)
# ════════════════════════════════════════════════════════════════════════════


def test_21_dag_levels_iterative_no_stackoverflow():
    """Spiegelt die iterative Level-Berechnung des DAG-Renderers.
    Eine zyklische depends_on (A→B→A) darf NICHT zu Endlos-Rekursion führen.
    """
    MAX_LEVELS = 10  # tasks.length + 1, hier reichen 10 für den Test

    def compute_levels_iterative(tasks):
        levels = {}
        tasks_map = {t["task_id"]: t for t in tasks}
        for _ in range(MAX_LEVELS):
            progress = False
            for t in tasks:
                if levels.get(t["task_id"]) is not None:
                    continue
                deps = [d for d in (t.get("depends_on") or []) if d in tasks_map]
                if not deps:
                    levels[t["task_id"]] = 0
                    progress = True
                else:
                    dep_levels = [levels[d] for d in deps if levels.get(d) is not None]
                    if len(dep_levels) == len(deps):
                        levels[t["task_id"]] = max(dep_levels) + 1
                        progress = True
            if not progress:
                break
        # Cycle-Erkennung
        for t in tasks:
            if levels.get(t["task_id"]) is None:
                levels[t["task_id"]] = 0  # fallback
        return levels

    # Cycle: A → B → A
    cyclic = [
        {"task_id": "A", "depends_on": ["B"]},
        {"task_id": "B", "depends_on": ["A"]},
        {"task_id": "C", "depends_on": []},
    ]
    levels = compute_levels_iterative(cyclic)
    # Alle bekommen einen Level (A=0, B=0, C=0), kein Crash
    assert set(levels.keys()) == {"A", "B", "C"}
    assert all(isinstance(v, int) for v in levels.values())

    # Linear: A → B → C
    linear = [
        {"task_id": "A", "depends_on": []},
        {"task_id": "B", "depends_on": ["A"]},
        {"task_id": "C", "depends_on": ["B"]},
    ]
    levels = compute_levels_iterative(linear)
    assert levels["A"] == 0
    assert levels["B"] == 1
    assert levels["C"] == 2