"""Test: Koordinations-DB zeigt Lerneffekt.

Überprüft:
- coordination.db zeichnet Jobs auf
- find_best_agent_for_task() wählt nach Erfolgsrate
- Worker unter 40% nach 5+ Jobs werden übersprungen
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def coord_db():
    """Isolierte coordination.db für jeden Test."""
    from gnom_hub.soul.memory_layers import CoordinationDB, _coordination_db
    _coordination_db = None
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "coordination.db"
        with patch("gnom_hub.soul.memory_layers.DB_PATH", str(db_path)):
            from gnom_hub.soul.memory_layers import get_coordination_db
            cdb = get_coordination_db()
            cdb._path = str(db_path)
            cdb._init_db()
            yield cdb


def test_find_best_agent_picks_high_success_rate(coord_db):
    """CoderAG mit 90% Erfolg wird WriterAG mit 20% vorgezogen."""
    for i in range(10):
        coord_db.record_job("CoderAG", f"Task {i}", "success" if i < 9 else "failed", 5.0)
    for i in range(10):
        coord_db.record_job("WriterAG", f"Task {i}", "success" if i < 2 else "failed", 8.0)

    preferred, fallback = coord_db.get_best_worker("code_generation")
    assert preferred == "CoderAG", f"Erwartet CoderAG, bekam {preferred}"


def test_bad_worker_skipped_after_5_jobs(coord_db):
    """WriterAG mit 20% Erfolg nach 5 Jobs wird übersprungen."""
    for i in range(5):
        coord_db.record_job("WriterAG", f"Task {i}", "success" if i == 0 else "failed", 10.0)

    preferred, fallback = coord_db.get_best_worker("content_creation")
    assert preferred != "WriterAG", "WriterAG mit 20% sollte übersprungen werden"


def test_fresh_worker_still_usable(coord_db):
    """Worker mit nur 1 Job wird nicht übersprungen (zu wenig Daten)."""
    coord_db.record_job("EditorAG", "Review X", "failed", 3.0)

    preferred, fallback = coord_db.get_best_worker("editing")
    assert preferred == "EditorAG", "Ein Fehlschlag allein sollte nicht ausschließen"


def test_workflow_pattern_tracking(coord_db):
    """Workflow-Ergebnisse werden gespeichert und sind analysierbar."""
    coord_db.record_workflow("wf-1", "ctx-1", "Test WF", ["CoderAG", "EditorAG"], "success", 30.0)
    coord_db.record_workflow("wf-2", "ctx-2", "Test WF", ["CoderAG", "EditorAG"], "success", 45.0)
    coord_db.record_workflow("wf-3", "ctx-3", "Test WF", ["CoderAG", "EditorAG"], "failed", 60.0, failed_at_task="EditorAG")

    patterns = coord_db.get_best_workflow_patterns(min_samples=2)
    assert len(patterns) >= 1
    assert patterns[0]["task_chain"] == ["CoderAG", "EditorAG"]
    assert patterns[0]["successes"] == 2
    assert patterns[0]["total"] == 3
