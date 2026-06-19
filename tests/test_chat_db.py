"""Tests for chat message operations."""
from gnom_hub.db.legacy_db import (
    add_chat_message, get_chat_history, get_chat_count,
    clear_project_chat, delete_project_completely
)


def test_add_chat_message(isolated_db):
    """Should add a chat message and return its ID."""
    msg_id = add_chat_message("default", "user", "test-agent", "chat", "Hello world")
    assert msg_id is not None
    assert isinstance(msg_id, str)


def test_get_chat_history(isolated_db):
    """Should retrieve recent messages."""
    add_chat_message("default", "user", "test-agent", "chat", "Message 1")
    add_chat_message("default", "TestBot", "test-agent", "chat", "Message 2")
    history = get_chat_history("default", limit=10)
    assert len(history) >= 2


def test_get_chat_count(isolated_db):
    """Should count messages."""
    add_chat_message("default", "user", "test-agent", "chat", "Count me")
    count = get_chat_count()
    assert count >= 1


def test_delete_project(isolated_db):
    """Should delete all messages for a project."""
    add_chat_message("deleteme", "user", "agent", "chat", "Gone soon")
    delete_project_completely("deleteme")
    history = get_chat_history("deleteme")
    assert len(history) == 0
