"""tests/test_swarm_comms.py — Unit Tests für Swarm Communications (swarm_comms.py)"""

import sqlite3

import pytest

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
# 2. FIND BEST AGENT FOR TASK (routing — replaces old _find_capability_for_task)
# ==============================================================================

class TestFindBestAgentForTask:
    def setup_method(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
            CREATE TABLE agents (
                name TEXT PRIMARY KEY,
                status TEXT DEFAULT 'online'
            );
            CREATE TABLE agent_capabilities (
                agent_name TEXT,
                capability TEXT,
                confidence REAL DEFAULT 0.5
            );
            CREATE TABLE agent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT,
                status TEXT DEFAULT 'pending'
            );
        """)
        for ag in ["coderag", "writerag", "researcherag", "editorag", "securityag"]:
            self.conn.execute("INSERT INTO agents (name, status) VALUES (?, 'online')", (ag,))
        for ag, cap in [
            ("coderag", "code_generation"),
            ("writerag", "content_creation"),
            ("researcherag", "web_research"),
            ("editorag", "editing"),
            ("securityag", "security_audit"),
        ]:
            self.conn.execute(
                "INSERT INTO agent_capabilities (agent_name, capability, confidence) VALUES (?, ?, 0.9)",
                (ag, cap),
            )

    def teardown_method(self):
        self.conn.close()

    def test_code_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        assert find_best_agent_for_task("python script schreiben", self.conn) == "coderag"
        assert find_best_agent_for_task("implementiere funktion", self.conn) == "coderag"

    def test_research_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        assert find_best_agent_for_task("recherchiere thema", self.conn) == "researcherag"
        assert find_best_agent_for_task("google das", self.conn) == "researcherag"

    def test_content_creation_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        result = find_best_agent_for_task("artikel verfassen", self.conn)
        assert result in ("writerag", "coderag")  # "schreib" overlaps

    def test_editing_tasks(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        result = find_best_agent_for_task("lektorat durchführen", self.conn)
        assert result in ("editorag", "coderag", "writerag")

    def test_unknown_task_returns_none(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        assert find_best_agent_for_task("random unknown task xyz123", self.conn) is None

    def test_empty_task_returns_none(self):
        from gnom_hub.agents.swarm.swarm_comms import find_best_agent_for_task
        assert find_best_agent_for_task("", self.conn) is None


# ==============================================================================
# 3. CAN ACCEPT MESSAGE
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
        from gnom_hub.agents.swarm.swarm_comms import MAX_QUEUE_DEPTH, can_accept_message
        for _ in range(MAX_QUEUE_DEPTH):
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
# 5. AGENT EVENTS (THREADING)
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
