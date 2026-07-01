"""Tests for admin authentication."""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from gnom_hub.api.endpoints.admin import verify_admin


def _make_request(host="127.0.0.1", headers=None):
    """Create a mock Request object."""
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = host
    req.headers = headers or {}
    return req


def test_localhost_allowed():
    """Localhost requests should be allowed."""
    req = _make_request(host="127.0.0.1")
    assert verify_admin(req) is True


def test_ipv6_localhost_allowed():
    """IPv6 localhost requests should be allowed."""
    req = _make_request(host="::1")
    assert verify_admin(req) is True


def test_remote_without_token_rejected():
    """Remote requests without auth should be rejected."""
    req = _make_request(host="192.168.1.100", headers={})
    with patch("gnom_hub.api.endpoints.admin._get_or_create_secret") as mock_secret:
        mock_secret.return_value = b"\x00" * 32
        with pytest.raises(HTTPException) as exc:
            verify_admin(req)
        assert exc.value.status_code == 403


def test_bearer_token_accepted():
    """Valid Bearer token should be accepted."""
    with patch.dict(os.environ, {"GNOM_ADMIN_TOKEN": "secret123"}):
        req = _make_request(host="192.168.1.100", headers={"Authorization": "Bearer secret123"})
        assert verify_admin(req) is True


def test_wrong_bearer_token_rejected():
    """Invalid Bearer token from remote should be rejected."""
    with patch.dict(os.environ, {"GNOM_ADMIN_TOKEN": "secret123"}):
        req = _make_request(host="192.168.1.100", headers={"Authorization": "Bearer wrongtoken"})
        with patch("gnom_hub.api.endpoints.admin._get_or_create_secret") as mock_secret:
            mock_secret.return_value = b"\x00" * 32
            with pytest.raises(HTTPException):
                verify_admin(req)
