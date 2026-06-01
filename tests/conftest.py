import pytest
import sqlite3
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="session")
def setup_test_env():
    """Set test environment variables before anything imports config."""
    os.environ["GNOM_HUB_ENV"] = "test"
    os.environ["TESTING"] = "true"


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Provides each test with an isolated SQLite database.
    
    Patches Config.DB_PATH and connection module to use a temporary DB file.
    Schema is initialized fresh for each test.
    """
    db_file = tmp_path / "test_gnomhub.db"
    
    with patch("gnom_hub.core.config.DB_PATH", db_file), \
         patch("gnom_hub.core.config.Config.DB_PATH", db_file), \
         patch("gnom_hub.db.connection.Config") as mock_config:
        
        mock_config.DB_PATH = db_file
        
        # Initialize schema
        from gnom_hub.db.connection import get_db_conn
        from gnom_hub.db.schema import init_database
        
        # Create the data directory
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            init_database()
        except Exception:
            # Schema init might fail if it tries to import complex modules
            # Fall back to manual table creation
            with get_db_conn() as conn:
                with conn:
                    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS agents (
                            name TEXT PRIMARY KEY, id TEXT UNIQUE, port INTEGER DEFAULT 0,
                            description TEXT DEFAULT '', status TEXT DEFAULT 'offline',
                            capabilities TEXT DEFAULT '[]', role TEXT DEFAULT 'normal',
                            active_job TEXT, last_seen TEXT
                        );
                        CREATE TABLE IF NOT EXISTS chat (
                            id TEXT PRIMARY KEY, project TEXT DEFAULT 'default',
                            sender TEXT, agent_id TEXT, msg_type TEXT DEFAULT 'chat',
                            content TEXT, timestamp TEXT, metadata TEXT DEFAULT '{}'
                        );
                        CREATE TABLE IF NOT EXISTS state (
                            key TEXT PRIMARY KEY, value TEXT
                        );
                        CREATE TABLE IF NOT EXISTS soul_memory (
                            key TEXT PRIMARY KEY, value TEXT, timestamp TEXT,
                            priority TEXT DEFAULT 'medium', agent TEXT DEFAULT 'System'
                        );
                        CREATE TABLE IF NOT EXISTS showbox_presentations (
                            id TEXT, name TEXT UNIQUE, slides TEXT,
                            sender TEXT, updated_at TEXT
                        );
                        CREATE TABLE IF NOT EXISTS audit_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT, agent TEXT, event_type TEXT,
                            details TEXT, trace_id TEXT
                        );
                    """)
        
        yield db_file


@pytest.fixture
def sample_agent_data():
    """Provides sample agent data for tests."""
    return {
        "name": "TestAgent",
        "description": "A test agent",
        "status": "online",
        "role": "normal",
        "capabilities": ["test"]
    }
