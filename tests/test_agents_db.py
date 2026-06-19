"""Tests for agent database operations."""
import uuid
from gnom_hub.db.legacy_db import (
    create_agent_record, get_all_agents, set_agent_status,
    delete_agent_by_id, update_agent_active_job, clear_agent_jobs,
    agent_exists
)


def test_create_agent(isolated_db):
    """Should create an agent record and return its data."""
    result = create_agent_record("TestBot", description="A test bot", role="normal")
    assert result is not None
    assert result["name"] == "TestBot"
    assert result["status"] == "offline"


def test_get_all_agents_empty(isolated_db):
    """Should return seeded agents or empty list."""
    agents = get_all_agents()
    assert isinstance(agents, list)


def test_agent_exists(isolated_db):
    """Should correctly report agent existence."""
    create_agent_record("ExistBot")
    assert agent_exists("ExistBot") is True
    assert agent_exists("NonExistBot") is False


def test_set_agent_status(isolated_db):
    """Should update agent status."""
    create_agent_record("StatusBot")
    result = set_agent_status("StatusBot", "online")
    assert result is not None
    assert result["status"] == "online"


def test_update_active_job(isolated_db):
    """Should update and clear active jobs."""
    create_agent_record("JobBot")
    update_agent_active_job("JobBot", "writing code")
    clear_agent_jobs("jobbot")


def test_delete_agent(isolated_db):
    """Should delete an agent."""
    result = create_agent_record("DeleteMe")
    delete_agent_by_id(result["name"])
    assert agent_exists("DeleteMe") is False
