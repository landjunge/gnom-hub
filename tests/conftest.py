import os
import urllib.error
import urllib.request
from unittest.mock import patch

import pytest

# test_stress_50.py ist ein Live-Hub-Integrationstest (kein pytest-Test-File
# mit test_*-Funktionen, sondern ein Top-Level-Script das beim Import gegen
# den Live-Hub auf GNOM_HUB_TEST_URL feuert). Standardmäßig nicht in CI/Pre-Push
# ausführen — explizit aktivieren via `pytest tests/test_stress_50.py` lokal.
collect_ignore_glob = ["test_stress_50.py"]


def pytest_collection_modifyitems(config, items):
    """Skip tests mit marker 'requires_hub' wenn Hub nicht erreichbar.
    Erlaubt CI/Pre-Push ohne laufenden Hub (default skip), lokal mit
    `pytest -m requires_hub` für Live-Stresstest.
    """
    hub_url = os.environ.get("GNOM_HUB_TEST_URL", "http://127.0.0.1:3002")
    hub_up = False
    try:
        with urllib.request.urlopen(hub_url, timeout=1) as r:
            hub_up = (r.status == 200)
    except (urllib.error.URLError, ConnectionError, OSError):
        pass

    if hub_up:
        return  # Hub läuft — alles ausführen

    skip_marker = pytest.mark.skip(reason=f"requires_hub: Hub nicht erreichbar auf {hub_url}")
    for item in items:
        if "requires_hub" in item.keywords:
            item.add_marker(skip_marker)


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
                            active_job TEXT, last_seen TEXT,
                            circuit_state TEXT DEFAULT 'CLOSED',
                            consecutive_failures INTEGER DEFAULT 0
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
                        CREATE TABLE IF NOT EXISTS agent_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            sender TEXT, recipient TEXT, payload TEXT,
                            priority INTEGER DEFAULT 5, status TEXT DEFAULT 'pending',
                            retry_count INTEGER DEFAULT 0, created_at REAL,
                            deliver_after REAL DEFAULT 0, context_id TEXT, depth INTEGER DEFAULT 0,
                            processing_since REAL DEFAULT NULL,
                            parent_msg_id INTEGER DEFAULT NULL,
                            completed_at REAL DEFAULT NULL
                        );
                        CREATE TABLE IF NOT EXISTS workflows (
                            id TEXT PRIMARY KEY,
                            name TEXT NOT NULL,
                            status TEXT NOT NULL DEFAULT 'pending',
                            created_at REAL NOT NULL,
                            completed_at REAL
                        );
                        CREATE TABLE IF NOT EXISTS workflow_tasks (
                            workflow_id TEXT NOT NULL,
                            task_id TEXT NOT NULL,
                            capability TEXT NOT NULL,
                            input_template TEXT NOT NULL,
                            depends_on TEXT NOT NULL,
                            status TEXT NOT NULL DEFAULT 'pending',
                            msg_id INTEGER,
                            result_json TEXT,
                            PRIMARY KEY (workflow_id, task_id)
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


@pytest.fixture
def test_dir(tmp_path):
    """Per-test artifact directory for screenshots/videos."""
    d = tmp_path / "browser_artifacts"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def hub_url():
    """URL of running hub for browser tests."""
    return os.environ.get("GNOM_HUB_TEST_URL", "http://127.0.0.1:3002")


@pytest.fixture
def page(hub_url):
    """Playwright page fixture (chromium headless).

    Browser-Tests überspringen sich automatisch wenn der Hub nicht auf hub_url
    erreichbar ist. So laufen CI-Runs ohne laufenden Hub durch.
    """
    import urllib.error
    import urllib.request

    from playwright.sync_api import sync_playwright
    try:
        with urllib.request.urlopen(hub_url, timeout=2) as r:
            if r.status != 200:
                pytest.skip(f"Hub nicht erreichbar auf {hub_url} (Status {r.status})")
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        pytest.skip(f"Hub nicht erreichbar auf {hub_url}: {e}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        pg = context.new_page()
        try:
            yield pg
        finally:
            context.close()
            browser.close()
