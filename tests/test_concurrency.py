"""
tests/test_concurrency.py
Verifies that Gnom-Hub's database layer handles concurrent, multi-threaded
access cleanly under WAL mode without raising SQLITE_BUSY (database is locked) errors.
"""

import pytest
import threading
import queue
import time
import random
from gnom_hub.db import (
    add_chat_message,
    get_chat_history,
    set_state_value,
    get_state_value
)

def test_sqlite_concurrency(isolated_db):
    """
    Spawns 10 concurrent threads that perform intensive reads and writes
    to verify WAL concurrency configuration.
    """
    num_threads = 10
    ops_per_thread = 30
    exceptions = queue.Queue()

    def worker_run(thread_id):
        try:
            for i in range(ops_per_thread):
                # 1. Write a chat message
                msg_content = f"Thread-{thread_id} message {i}"
                msg_id = add_chat_message(
                    project="concurrency_test",
                    sender=f"Thread-{thread_id}",
                    agent_id=f"agent-{thread_id}",
                    msg_type="chat",
                    content=msg_content
                )
                assert msg_id is not None

                # 2. Read chat history
                history = get_chat_history(project="concurrency_test", limit=10)
                assert len(history) > 0

                # 3. Write a state value
                state_key = f"key_{thread_id}_{i}"
                set_state_value(state_key, {"val": i, "random": random.random()})

                # 4. Read state value
                val = get_state_value(state_key)
                assert val is not None
                assert val["val"] == i

                # Short random sleep to simulate realistic inter-agent workloads
                time.sleep(random.uniform(0.001, 0.005))
        except Exception as e:
            exceptions.put((thread_id, e))

    threads = []
    for t_id in range(num_threads):
        t = threading.Thread(target=worker_run, args=(t_id,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Assert that no threads raised exceptions
    raised = []
    while not exceptions.empty():
        raised.append(exceptions.get())

    if raised:
        pytest.fail(f"Concurrent database operations failed with: {raised}")
