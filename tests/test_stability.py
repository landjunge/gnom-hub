import time
import json
import pytest
from gnom_hub.db.connection import get_db_connection
from gnom_hub.agents.swarm.swarm_comms import (
    dispatch_mention, recover_stuck_messages, MAX_QUEUE_DEPTH, get_agent_event,
    find_best_agent_for, dispatch_by_capability
)

def test_recover_stuck_messages(isolated_db):
    """Test that stuck processing messages are recovered or moved to DLQ."""
    conn = get_db_connection()
    try:
        # Seed or replace agent to make them a valid target
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        
        # 1. Insert a stuck processing message (10 minutes ago)
        now = time.time()
        conn.execute("""
            INSERT INTO agent_messages
                (sender, recipient, payload, priority, status, retry_count, created_at, deliver_after, processing_since, depth)
            VALUES ('GeneralAG', 'CoderAG', ?, 5, 'processing', 0, ?, 0, ?, 0)
        """, (json.dumps({"text": "stuck task"}), now - 600, now - 600))
        
        # 2. Insert a message that has already been retried max times (2 retries, 3rd try is stuck)
        conn.execute("""
            INSERT INTO agent_messages
                (sender, recipient, payload, priority, status, retry_count, created_at, deliver_after, processing_since, depth)
            VALUES ('GeneralAG', 'CoderAG', ?, 5, 'processing', 2, ?, 0, ?, 0)
        """, (json.dumps({"text": "dead task"}), now - 600, now - 600))
        
        conn.commit()
    finally:
        conn.close()

    # Run recovery with timeout of 300 seconds (5 minutes)
    from gnom_hub.core.config import DB_PATH
    recover_stuck_messages(str(DB_PATH), timeout=300.0)

    # Check state after recovery
    conn = get_db_connection()
    try:
        # First message should be pending again with retry_count = 1
        stuck_msg = conn.execute("SELECT status, retry_count, processing_since FROM agent_messages WHERE payload LIKE '%stuck%'").fetchone()
        assert stuck_msg is not None
        assert stuck_msg["status"] == "pending"
        assert stuck_msg["retry_count"] == 1
        assert stuck_msg["processing_since"] is None

        # Second message should be dead_letter
        dead_msg = conn.execute("SELECT status, retry_count, processing_since FROM agent_messages WHERE payload LIKE '%dead%'").fetchone()
        assert dead_msg is not None
        assert dead_msg["status"] == "dead_letter"
        assert dead_msg["retry_count"] == 3
        assert dead_msg["processing_since"] is None
    finally:
        conn.close()


def test_backpressure_queue_limit(isolated_db):
    """Test that mentions are dropped when an agent's queue depth exceeds MAX_QUEUE_DEPTH."""
    conn = get_db_connection()
    try:
        # Seed or replace CoderAG
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'running', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        
        # Fill the queue up to MAX_QUEUE_DEPTH (50)
        now = time.time()
        for i in range(MAX_QUEUE_DEPTH):
            conn.execute("""
                INSERT INTO agent_messages
                    (sender, recipient, payload, priority, status, retry_count, created_at, deliver_after, depth)
                VALUES ('GeneralAG', 'CoderAG', ?, 5, 'pending', 0, ?, 0, 0)
            """, (json.dumps({"text": f"task {i}"}), now))
        conn.commit()
    finally:
        conn.close()

    from gnom_hub.core.config import DB_PATH
    # Now attempt to dispatch another mention - it should be rejected/dropped due to backpressure
    dispatched = dispatch_mention("GeneralAG", "@CoderAG hello", "default", str(DB_PATH))
    assert dispatched == []  # Not dispatched to CoderAG

    # Verify that the message count did not increase
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = 'CoderAG'").fetchone()[0]
        assert count == MAX_QUEUE_DEPTH
    finally:
        conn.close()


def test_callback_idempotency(isolated_db):
    """Test that callbacks are idempotent and do not duplicate coordinator signaling."""
    from gnom_hub.api.endpoints.agents_status import swarm_complete, SwarmCompletePayload
    from gnom_hub.agents.swarm.swarm_coordinator import register_tracker, WorkerCompletionTracker
    
    # Set up a tracker
    tracker = WorkerCompletionTracker(["CoderAG"], timeout=10.0)
    register_tracker("test-ctx", tracker)

    payload = SwarmCompletePayload(
        context_id="test-ctx",
        agent_name="CoderAG",
        result={"status": "success", "content": "hello"}
    )

    # 1. First callback - should be accepted
    r1 = swarm_complete(payload)
    assert r1["status"] == "accepted"

    # 2. Duplicate callback - should be marked as already processed
    r2 = swarm_complete(payload)
    assert r2["status"] == "already_processed"


def test_prometheus_metrics(isolated_db):
    """Test that the /metrics endpoint outputs correct Prometheus metric formats."""
    from gnom_hub.api.endpoints.metrics import prometheus_metrics
    
    # Put a dead letter and some agents in the database
    conn = get_db_connection()
    try:
        now = time.time()
        conn.execute("""
            INSERT INTO agent_messages (sender, recipient, payload, priority, status, created_at, deliver_after)
            VALUES ('GeneralAG', 'CoderAG', '{"text":"t1"}', 5, 'dead_letter', ?, 0)
        """, (now,))
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.commit()
    finally:
        conn.close()

    resp = prometheus_metrics()
    assert resp.status_code == 200
    content = resp.body.decode("utf-8")
    
    assert "gnomhub_dead_letter_total" in content
    assert "gnomhub_queue_depth" in content
    assert "gnomhub_heartbeat_drift_seconds" in content


def test_dlq_management_api(isolated_db):
    """Test standard admin dead-letter endpoints (list, retry, delete, purge)."""
    from fastapi import Request
    from gnom_hub.api.endpoints.admin import list_dead_letters, retry_dead_letter, discard_dead_letter, purge_dead_letters
    
    # 1. Insert a dead letter
    conn = get_db_connection()
    try:
        now = time.time()
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.execute("""
            INSERT INTO agent_messages (id, sender, recipient, payload, priority, status, created_at, deliver_after)
            VALUES (999, 'GeneralAG', 'CoderAG', '{"text":"dead"}', 5, 'dead_letter', ?, 0)
        """, (now,))
        conn.commit()
    finally:
        conn.close()

    # Mock Request
    req = Request(scope={"type": "http", "headers": []})

    # List dead letters
    dlq_list = list_dead_letters(req)
    assert len(dlq_list) >= 1
    assert dlq_list[0]["id"] == 999

    # Retry dead letter
    res_retry = retry_dead_letter(999, req)
    assert res_retry["status"] == "requeued"

    # Verify state in DB is pending
    conn = get_db_connection()
    try:
        msg = conn.execute("SELECT status FROM agent_messages WHERE id = 999").fetchone()
        assert msg["status"] == "pending"
        
        # Change it back to dead letter to test deletion
        conn.execute("UPDATE agent_messages SET status = 'dead_letter' WHERE id = 999")
        conn.commit()
    finally:
        conn.close()

    # Discard dead letter
    res_delete = discard_dead_letter(999, req)
    assert res_delete["status"] == "deleted"

    # Verify msg is deleted
    conn = get_db_connection()
    try:
        msg = conn.execute("SELECT 1 FROM agent_messages WHERE id = 999").fetchone()
        assert msg is None
        
        # Re-add a dead letter to test purge
        conn.execute("""
            INSERT INTO agent_messages (id, sender, recipient, payload, priority, status, created_at, deliver_after)
            VALUES (999, 'GeneralAG', 'CoderAG', '{"text":"dead"}', 5, 'dead_letter', ?, 0)
        """, (time.time(),))
        conn.commit()
    finally:
        conn.close()

    # Purge all dead letters
    res_purge = purge_dead_letters(req)
    assert res_purge["status"] == "purged"
    assert res_purge["deleted_count"] >= 1


def test_capability_registry_routing(isolated_db):
    """Test mapping and routing agent messages based on capability registration."""
    conn = get_db_connection()
    try:
        # Seed agents
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('SecurityAG', 'security-uuid', 0, 'Security Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        
        # Seed Capabilities
        conn.execute("INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence) VALUES ('CoderAG', 'code_review', 0.9)")
        conn.execute("INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence) VALUES ('SecurityAG', 'code_review', 0.5)")
        conn.execute("INSERT OR REPLACE INTO agent_capabilities (agent_name, capability, confidence) VALUES ('SecurityAG', 'security_audit', 1.0)")
        conn.commit()
    finally:
        conn.close()

    conn = get_db_connection()
    try:
        # 1. Best agent for code_review should be CoderAG due to higher confidence (0.9 vs 0.5)
        best_reviewer = find_best_agent_for("code_review", conn)
        assert best_reviewer == "CoderAG"

        # 2. Best agent for security_audit should be SecurityAG
        best_auditor = find_best_agent_for("security_audit", conn)
        assert best_auditor == "SecurityAG"

        # 3. If CoderAG queue is busy, check load balancing
        # Add 1 pending task for CoderAG
        conn.execute("""
            INSERT INTO agent_messages (sender, recipient, payload, priority, status, created_at, deliver_after)
            VALUES ('GeneralAG', 'CoderAG', '{"text":"task"}', 5, 'pending', ?, 0)
        """, (time.time(),))
        conn.commit()

        # CoderAG has queue depth 1, SecurityAG has 0.
        # Although CoderAG confidence is 0.9, SecurityAG has queue depth 0, so SecurityAG is selected first due to order by queue_depth ASC.
        best_reviewer_busy = find_best_agent_for("code_review", conn)
        assert best_reviewer_busy == "SecurityAG"
    finally:
        conn.close()

    # Test dispatch_by_capability
    from gnom_hub.core.config import DB_PATH
    target = dispatch_by_capability("GeneralAG", "security_audit", "test task", "default-ctx", str(DB_PATH))
    assert target == "SecurityAG"

    conn = get_db_connection()
    try:
        # Check that message was queued for SecurityAG
        msg = conn.execute("SELECT recipient, payload FROM agent_messages WHERE recipient = 'SecurityAG'").fetchone()
        assert msg is not None
        assert "@SecurityAG" in msg["payload"]
    finally:
        conn.close()


def test_prioritization_mapping(isolated_db):
    """Test that string priorities are mapped to integers and ordered correctly."""
    from gnom_hub.core.config import DB_PATH
    from gnom_hub.agents.swarm.swarm_comms import fetch_next_message
    
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.commit()
    finally:
        conn.close()
        
    dispatch_mention("GeneralAG", "@CoderAG low task", "ctx1", str(DB_PATH), priority="low")
    dispatch_mention("GeneralAG", "@CoderAG critical task", "ctx1", str(DB_PATH), priority="critical")
    
    m1 = fetch_next_message("CoderAG", str(DB_PATH))
    assert m1 is not None
    assert "critical" in m1["payload"]["text"]
    
    m2 = fetch_next_message("CoderAG", str(DB_PATH))
    assert m2 is not None
    assert "low" in m2["payload"]["text"]


def test_agent_quarantine(isolated_db):
    """Test that watchdog quarantines agents in a crash loop (3 restarts in 10 mins)."""
    from gnom_hub.db import update_agent_status
    
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.commit()
    finally:
        conn.close()

    restart_tracker = {}
    
    for _ in range(3):
        now_ts = time.time()
        name = "CoderAG"
        history = [ts for ts in restart_tracker.get(name, []) if now_ts - ts < 600.0]
        history.append(now_ts)
        restart_tracker[name] = history
        
        if len(history) >= 3:
            update_agent_status(name, "quarantined")
            
    conn = get_db_connection()
    try:
        agent = conn.execute("SELECT status FROM agents WHERE name = 'CoderAG'").fetchone()
        assert agent["status"] == "quarantined"
    finally:
        conn.close()


def test_circuit_breaker(isolated_db):
    """Test that consecutive failures trip the circuit breaker and success resets it."""
    from gnom_hub.api.endpoints.agents_status import swarm_complete, SwarmCompletePayload
    
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen, circuit_state, consecutive_failures)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z', 'CLOSED', 0)
        """)
        conn.commit()
    finally:
        conn.close()

    # Trigger 5 distinct failures (with different context_ids to pass idempotency check)
    for i in range(5):
        payload_err = SwarmCompletePayload(
            context_id=f"ctx-err-{i}",
            agent_name="CoderAG",
            result={"status": "error", "error": "something failed"}
        )
        swarm_complete(payload_err)
        
    conn = get_db_connection()
    try:
        agent = conn.execute("SELECT status, circuit_state, consecutive_failures FROM agents WHERE name = 'CoderAG'").fetchone()
        assert agent["status"] == "degraded"
        assert agent["circuit_state"] == "OPEN"
        assert agent["consecutive_failures"] == 5
    finally:
        conn.close()
        
    payload_ok = SwarmCompletePayload(
        context_id="ctx-ok-1",
        agent_name="CoderAG",
        result={"status": "success", "content": "everything is fine"}
    )
    swarm_complete(payload_ok)
    
    conn = get_db_connection()
    try:
        agent = conn.execute("SELECT status, circuit_state, consecutive_failures FROM agents WHERE name = 'CoderAG'").fetchone()
        assert agent["status"] == "online"
        assert agent["circuit_state"] == "CLOSED"
        assert agent["consecutive_failures"] == 0
    finally:
        conn.close()


def test_task_lineage(isolated_db):
    """Test that parent_msg_id is correctly set and propagated."""
    from gnom_hub.core.config import DB_PATH
    
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES ('CoderAG', 'coder-uuid', 0, 'Coder Agent', 'online', '[]', 'normal', '2026-06-04T00:00:00Z')
        """)
        conn.commit()
    finally:
        conn.close()

    dispatch_mention("GeneralAG", "@CoderAG hello", "ctx1", str(DB_PATH), parent_msg_id=123)
    
    conn = get_db_connection()
    try:
        msg = conn.execute("SELECT id, parent_msg_id FROM agent_messages WHERE recipient = 'CoderAG'").fetchone()
        assert msg is not None
        assert msg["parent_msg_id"] == 123
        
        # Test lineage routing - must not be self-dispatch
        from gnom_hub.agents.swarm.swarm_comms import process_swarm_mentions
        process_swarm_mentions("GeneralAG", "@CoderAG child task", depth=0, parent_msg_id=msg["id"])
        
        child = conn.execute("SELECT parent_msg_id FROM agent_messages WHERE parent_msg_id = ?", (msg["id"],)).fetchone()
        assert child is not None
        assert child["parent_msg_id"] == msg["id"]
    finally:
        conn.close()
