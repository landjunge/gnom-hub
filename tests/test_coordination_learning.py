"""Test: Koordinations-DB zeigt Lerneffekt.

Überprüft:
- coordination.db zeichnet Jobs auf
- find_best_agent_for_task() wählt nach Erfolgsrate
- Worker unter 40% nach 5+ Jobs werden übersprungen
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def coord_db():
    """Isolierte coordination.db für jeden Test."""
    from gnom_hub.soul.memory_layers import CoordinationDB
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "coordination.db"
        with patch("gnom_hub.core.config.DB_PATH", str(db_path.parent / "gnomhub.db")):
            import gnom_hub.soul.memory_layers as ml
            ml._coordination_db = CoordinationDB()
            ml._coordination_db._path = str(db_path)
            ml._coordination_db._init_db()
            yield ml._coordination_db


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

    preferred, fallback = coord_db.get_best_worker("review")
    assert preferred == "EditorAG", "Ein Fehlschlag allein sollte nicht ausschließen"


def test_workflow_pattern_tracking(coord_db):
    """Workflow-Ergebnisse werden gespeichert und sind analysierbar (record_workflow noch nicht implementiert)."""
    import pytest
    pytest.skip("record_workflow / get_best_workflow_patterns noch nicht in CoordinationDB")
