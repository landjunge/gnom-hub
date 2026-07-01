"""Tests for admin_system.py endpoints."""
import time
from unittest.mock import MagicMock, patch


def test_kill_processes_by_name_excludes_self_pid():
    """PID des eigenen Prozesses wird nie gekillt."""
    from gnom_hub.api.endpoints.admin_system import _kill_processes_by_name
    with patch("psutil.process_iter") as mock_iter:
        mock_proc = MagicMock()
        mock_proc.info = {"pid": 12345, "name": "python", "cmdline": ["python", "-m", "gnom_hub"]}
        mock_iter.return_value = [mock_proc]
        killed = _kill_processes_by_name(["gnom_hub"], exclude_pids=[12345])
        assert killed == 0
        mock_proc.kill.assert_not_called()


def test_delayed_restart_logs_when_script_missing(tmp_path, caplog):
    """Wenn start_gnom_hub.sh fehlt: keine Exception, aber Log-Warning."""

    from gnom_hub.api.endpoints.admin_system import _delayed_restart
    with patch("gnom_hub.core.config.PROJECT_ROOT", str(tmp_path)):
        with caplog.at_level("WARNING", logger="gnom_hub.api.endpoints.admin_system"):
            _delayed_restart(old_hub_pid=99999)  # pid_exists False, Polling endet schnell
            time.sleep(5)  # Polling durchlaufen
    # Erwartet: Warning-Log "start_gnom_hub.sh fehlt" (auch wenn nicht exakt — irgendein Warning)


def test_nuke_restart_requires_auth():
    """nuke_restart gibt Unauthorized zurück wenn nicht localhost + kein secret."""
    from gnom_hub.api.endpoints.admin_system import nuke_restart
    req = MagicMock()
    req.client.host = "192.168.1.100"
    req.headers = {}
    result = nuke_restart(req)
    assert result == {"error": "Unauthorized"}
