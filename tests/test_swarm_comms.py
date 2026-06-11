"""tests/test_swarm_comms.py — Unit Tests für Swarm Communications (swarm_comms.py)"""

import pytest
import sqlite3
import time
from unittest.mock import patch, MagicMock
from typing import Optional


# ==============================================================================
# 1. PARSE AGENT SEQUENCE
# ==============================================================================

class TestParseAgentSequence:
    """Format: @Agent -> Aufgabe"""

    def test_single_mention_with_arrow(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        result = parse_agent_sequence("@CoderAG -> Hilf mir bitte")
        assert ("coderag", "Hilf mir bitte") in result

    def test_multiple_mentions(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        result = parse_agent_sequence("@CoderAG -> Code schreiben\n@WriterAG -> Text schreiben")
        assert ("coderag", "Code schreiben") in result
        assert ("writerag", "Text schreiben") in result

    def test_supports_dash_arrow(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        result = parse_agent_sequence("@CoderAG --> Task erledigen")
        assert ("coderag", "Task erledigen") in result

    def test_supports_unicode_arrow(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        result = parse_agent_sequence("@CoderAG → Task erledigen")
        assert ("coderag", "Task erledigen") in result

    def test_none_text_raises(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        with pytest.raises(AttributeError):
            parse_agent_sequence(None)

    def test_empty_text_returns_empty(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        assert parse_agent_sequence("") == []

    def test_no_arrow_no_match(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        assert parse_agent_sequence("@CoderAG Hallo Welt") == []

    def test_no_mention_no_match(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        assert parse_agent_sequence("Hallo Welt") == []

    def test_lowercases_agent_names(self):
        from gnom_hub.agents.swarm.swarm_comms import parse_agent_sequence
        result = parse_agent_sequence("@CODERAG -> schreib code\n@WRITERAG -> schreib text")
        assert ("coderag", "schreib code") in result
        assert ("writerag", "schreib text") in result


# ==============================================================================
# 2. FIND CAPABILITY FOR TASK
# ==============================================================================

class TestFindCapabilityForTask:
    def test_code_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("python script schreiben") == "code_generation"
        assert _find_capability_for_task("implementiere funktion") == "code_generation"
        assert _find_capability_for_task("bash command") == "code_generation"

    def test_research_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("recherchiere thema") == "web_research"
        assert _find_capability_for_task("suche information") == "web_research"
        assert _find_capability_for_task("google das") == "web_research"

    def test_content_creation_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("blog verfassen") == "content_creation"
        assert _find_capability_for_task("artikel verfassen") == "content_creation"
        assert _find_capability_for_task("slogan erstellen") == "content_creation"

    def test_editing_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("lektorat durchführen") == "editing"
        assert _find_capability_for_task("prüf die datei") == "editing"

    def test_security_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("sicherheits audit") == "security_audit"
        assert _find_capability_for_task("security scan") == "security_audit"

    def test_unknown_task_returns_none(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("random unknown task") is None

    def test_empty_task_returns_none(self):
        from gnom_hub.agents.swarm.swarm_comms import _find_capability_for_task
        assert _find_capability_for_task("") is None


# ==============================================================================
# 3. GET QUEUE DEPTHS
# ==============================================================================

class TestGetQueueDepths:
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT,
                status TEXT DEFAULT 'pending',
                created_at REAL
            )
        """)

    def teardown_method(self):
        self.conn.close()

    def test_returns_dict_with_counts(self):
        from gnom_hub.agents.swarm.swarm_comms import _get_queue_depths
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'pending')")
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'pending')")
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('writerag', 'pending')")
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('writerag', 'delivered')")
        result = _get_queue_depths(self.conn)
        assert result.get("coderag") == 2
        assert result.get("writerag") == 1

    def test_empty_queue_returns_empty_dict(self):
        from gnom_hub.agents.swarm.swarm_comms import _get_queue_depths
        result = _get_queue_depths(self.conn)
        assert result == {}

    def test_counts_processing_as_active(self):
        from gnom_hub.agents.swarm.swarm_comms import _get_queue_depths
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'processing')")
        self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'pending')")
        result = _get_queue_depths(self.conn)
        assert result.get("coderag") == 2


# ==============================================================================
# 4. CAN ACCEPT MESSAGE
# ==============================================================================

class TestCanAcceptMessage:
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE agent_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT, status TEXT DEFAULT 'pending', created_at REAL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS agents (name TEXT PRIMARY KEY, circuit_state TEXT DEFAULT 'CLOSED', consecutive_failures INTEGER DEFAULT 0, status TEXT DEFAULT 'online')")
        self.conn.execute("INSERT OR IGNORE INTO agents (name, circuit_state, consecutive_failures, status) VALUES ('coderag', 'CLOSED', 0, 'online')")

    def teardown_method(self):
        self.conn.close()

    def test_accepts_when_queue_below_limit(self):
        from gnom_hub.agents.swarm.swarm_comms import can_accept_message
        assert can_accept_message("coderag", self.conn) is True

    def test_rejects_when_queue_at_limit(self):
        from gnom_hub.agents.swarm.swarm_comms import can_accept_message
        for _ in range(30):
            self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'pending')")
        assert can_accept_message("coderag", self.conn) is False

    def test_accepts_when_processing_under_limit(self):
        from gnom_hub.agents.swarm.swarm_comms import can_accept_message
        for _ in range(7):
            self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'processing')")
        assert can_accept_message("coderag", self.conn) is True

    def test_accepts_when_processing_at_limit(self):
        from gnom_hub.agents.swarm.swarm_comms import can_accept_message
        for _ in range(8):
            self.conn.execute("INSERT INTO agent_messages (recipient, status) VALUES ('coderag', 'processing')")
        assert can_accept_message("coderag", self.conn) is True  # no hard reject on processing, just log


# ==============================================================================
# 5. SUCCESS RATE & JOB THRESHOLD
# ==============================================================================

class TestGetSuccessRate:
    def test_no_jobs_returns_zero(self):
        from gnom_hub.agents.swarm.swarm_comms import _get_success_rate
        mock_cdb = MagicMock()
        mock_cdb._path = ":memory:"
        with patch("gnom_hub.soul.memory_layers.get_coordination_db",
                   return_value=mock_cdb):
            result = _get_success_rate(MagicMock(), "coderag")
        assert result == 0.0


class TestHasEnoughJobs:
    def test_no_jobs_returns_false(self):
        from gnom_hub.agents.swarm.swarm_comms import _has_enough_jobs
        mock_cdb = MagicMock()
        mock_cdb._path = ":memory:"
        with patch("gnom_hub.soul.memory_layers.get_coordination_db",
                   return_value=mock_cdb):
            result = _has_enough_jobs(MagicMock(), "coderag", threshold=5)
        assert result is False


# ==============================================================================
# 6. AGENT EVENTS (THREADING)
# ==============================================================================

class TestAgentEvents:
    def test_get_agent_event_creates_event_for_new_agent(self):
        from gnom_hub.agents.swarm.swarm_comms import get_agent_event
        event = get_agent_event("test_agent")
        assert event is not None
        assert event.is_set() is False

    def test_get_agent_event_returns_same_event(self):
        from gnom_hub.agents.swarm.swarm_comms import get_agent_event
        e1 = get_agent_event("test_agent_2")
        e2 = get_agent_event("test_agent_2")
        assert e1 is e2

    def test_notify_agent_sets_event(self):
        from gnom_hub.agents.swarm.swarm_comms import get_agent_event, notify_agent
        event = get_agent_event("test_agent_3")
        assert event.is_set() is False
        notify_agent("test_agent_3")
        assert event.is_set() is True

    def test_notify_unknown_agent_does_not_raise(self):
        from gnom_hub.agents.swarm.swarm_comms import notify_agent
        notify_agent("nonexistent_agent")


# ==============================================================================
# 7. FAIL DEPENDENT MESSAGES
# ==============================================================================

class TestFailDependentMessages:
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript("""
            CREATE TABLE agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT 'pending',
                parent_msg_id INTEGER DEFAULT NULL,
                context_id TEXT,
                sender TEXT,
                completed_at REAL DEFAULT NULL
            )
        """)
        self.conn.execute("INSERT INTO agent_messages (id, status, parent_msg_id, context_id, completed_at) VALUES (1, 'failed', NULL, 'ctx_1', NULL)")
        self.conn.execute("INSERT INTO agent_messages (id, status, parent_msg_id, context_id, completed_at) VALUES (2, 'pending', 1, 'ctx_1', NULL)")
        self.conn.execute("INSERT INTO agent_messages (id, status, parent_msg_id, context_id, completed_at) VALUES (3, 'pending', 2, 'ctx_1', NULL)")
        self.conn.execute("INSERT INTO agent_messages (id, status, parent_msg_id, context_id, completed_at) VALUES (4, 'pending', NULL, 'ctx_2', NULL)")

    def test_fails_child_messages(self):
        from gnom_hub.agents.swarm.swarm_comms import fail_dependent_messages
        fail_dependent_messages(1, "Parent failed", self.conn)
        status_2 = self.conn.execute("SELECT status FROM agent_messages WHERE id = 2").fetchone()[0]
        status_3 = self.conn.execute("SELECT status FROM agent_messages WHERE id = 3").fetchone()[0]
        status_4 = self.conn.execute("SELECT status FROM agent_messages WHERE id = 4").fetchone()[0]
        assert status_2 == "dead_letter"
        assert status_3 == "dead_letter"
        assert status_4 == "pending"

    def test_no_children_does_not_raise(self):
        from gnom_hub.agents.swarm.swarm_comms import fail_dependent_messages
        fail_dependent_messages(99, "No children", self.conn)
