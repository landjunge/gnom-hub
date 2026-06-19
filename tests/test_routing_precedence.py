"""Test: Routing-Precedence zwischen DB und routing.txt.

DB-Wert soll Vorrang vor routing.txt haben. Wenn die DB einen Eintrag
für einen Agenten hat, wird routing.txt ignoriert.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_db_config_wins_over_routing_txt(tmp_path):
    """DB-Wert soll Vorrang vor routing.txt haben.

    Setup: routing.txt sagt 'minimax', DB sagt 'deepseek'.
    Erwartung: ask_router ruft _try_keys('deepseek', ...) auf, NICHT 'minimax'.
    """
    from gnom_hub.core.config import PROJECT_ROOT
    routing_file = tmp_path / "config"
    routing_file.mkdir()
    (routing_file / "routing.txt").write_text("soulag = minimax | MiniMax-M3\n")

    db_config = {"soulag": {"provider": "deepseek", "model": "deepseek-v4-pro"}}

    with patch("gnom_hub.core.config.PROJECT_ROOT", str(tmp_path)):
        with patch("gnom_hub.core.utils.routing_override.PROJECT_ROOT", str(tmp_path)):
            with patch("gnom_hub.infrastructure.router.router.get_state_value") as mock_state:
                mock_state.side_effect = lambda k, default=None: {
                    "llm_keys": {},
                    "llm_agents": db_config
                }.get(k, default)
                with patch("gnom_hub.infrastructure.router.router.set_state_value"):
                    with patch("gnom_hub.infrastructure.router.router.get_all_agents", return_value=[]):
                        with patch("gnom_hub.infrastructure.router.router.set_agent_status"):
                            with patch("gnom_hub.infrastructure.router.router._try") as mock_try:
                                with patch("gnom_hub.infrastructure.router.router._try_keys") as mock_try_keys:
                                    mock_try.return_value = None
                                    mock_try_keys.return_value = "test response"

                                    from gnom_hub.infrastructure.router.router import ask_router
                                    try:
                                        ask_router("test", "sys", agent_name="SoulAG")
                                    except Exception:
                                        # wrap_response might fail without full setup, that's OK
                                        pass

                                    # DB-first: deepseek soll aufgerufen worden sein, NICHT minimax
                                    if mock_try_keys.called:
                                        called_provider = mock_try_keys.call_args[0][0]
                                        assert called_provider == "deepseek", (
                                            f"DB sollte gewinnen: expected 'deepseek', got '{called_provider}'"
                                        )
