import time
import json
import pytest
from gnom_hub.db.connection import get_db_connection
from gnom_hub.agents.swarm.swarm_comms import (
    dispatch_mention, recover_stuck_messages, MAX_QUEUE_DEPTH, get_agent_event
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
