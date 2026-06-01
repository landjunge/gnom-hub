"""Tests for state get/set operations."""
from gnom_hub.db.legacy_db import get_state_value, set_state_value


def test_set_and_get_state_value(isolated_db):
    """Should store and retrieve a state value."""
    set_state_value("test_key", "test_value")
    result = get_state_value("test_key")
    assert result == "test_value"


def test_get_state_default(isolated_db):
    """Should return default when key doesn't exist."""
    result = get_state_value("nonexistent_key", "default_val")
    assert result == "default_val"


def test_set_state_overwrites(isolated_db):
    """Should overwrite existing values."""
    set_state_value("overwrite_key", "first")
    set_state_value("overwrite_key", "second")
    assert get_state_value("overwrite_key") == "second"


def test_set_state_complex_value(isolated_db):
    """Should handle complex JSON values (dicts, lists)."""
    complex_val = {"agents": [{"name": "Test", "status": "online"}], "count": 42}
    set_state_value("complex_key", complex_val)
    result = get_state_value("complex_key")
    assert result == complex_val
