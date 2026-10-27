"""
Tests for 'cylera auth' and the WorkOS sign-in in cylera_auth.py.

WorkOS and the Partner API's token exchange are mocked, so no real API
calls are made.
"""

import json
import stat
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

import cylera_auth
from cylera import app, get_client

runner = CliRunner()

BASE_URL = "https://partner.demo.cylera.com/"
AUTHENTICATION = {
    "user": {"email": "test@example.com"},
    "access_token": "workos-access",
    "refresh_token": "refresh-1",
}


def _response(status, body):
    response = MagicMock(status_code=status, ok=status < 400, text=json.dumps(body))
    response.json.return_value = body
    return response


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    """A base URL and WorkOS client ID, no password, and no stored sign-in."""
    monkeypatch.setenv("CYLERA_BASE_URL", BASE_URL)
    monkeypatch.setenv("CYLERA_WORKOS_CLIENT_ID", "client_123")
    monkeypatch.delenv("CYLERA_USERNAME", raising=False)
    monkeypatch.delenv("CYLERA_PASSWORD", raising=False)
    monkeypatch.setattr(cylera_auth, "CREDENTIALS_PATH", tmp_path / "credentials.json")
    monkeypatch.setattr(cylera_auth, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(cylera_auth.time, "sleep", lambda _: None)
    monkeypatch.chdir(tmp_path)  # no stray .env


@pytest.fixture
def device_flow():
    """WorkOS answers 'pending' once, then the sign-in."""
    responses = [
        _response(200, {
            "device_code": "dev", "user_code": "ABCD-EFGH",
            "verification_uri_complete": "https://auth/device?user_code=ABCD-EFGH",
            "expires_in": 300, "interval": 5,
        }),
        _response(400, {"error": "authorization_pending"}),
        _response(200, AUTHENTICATION),
    ]
    with patch.object(cylera_auth, "_post", side_effect=responses) as post:
        yield post


def _exchange(status=200):
    return patch.object(cylera_auth.requests, "post",
                        return_value=_response(status, {"token": "cylera-token"}))


def test_login_stores_refresh_token_owner_only(device_flow):
    with _exchange() as exchange, patch("cylera.CyleraClient"), \
         patch("cylera.Organization") as org:
        org.return_value.get_organization.return_value = {"name": "Acme"}
        result = runner.invoke(app, ["auth", "login", "--no-browser"])

    assert result.exit_code == 0, result.output
    assert "Signed in as test@example.com (Acme)" in result.output
    assert "ABCD-EFGH" in result.output
    exchange.assert_called_once_with(
        "https://partner.demo.cylera.com/auth/token_exchange",
        json={"token": "workos-access"}, timeout=30)
    assert cylera_auth.stored_login(BASE_URL)["refresh_token"] == "refresh-1"
    mode = stat.S_IMODE(cylera_auth.CREDENTIALS_PATH.stat().st_mode)
    assert mode == 0o600


def test_login_refused_by_cylera_stores_nothing(device_flow):
    with _exchange(401):
        result = runner.invoke(app, ["auth", "login", "--no-browser"])

    assert result.exit_code == 1
    assert "Sign in to the Cylera Portal" in result.output
    assert cylera_auth.stored_login(BASE_URL) is None


def test_login_declined():
    responses = [
        _response(200, {"device_code": "dev", "user_code": "X",
                        "verification_uri_complete": "https://auth/device"}),
        _response(400, {"error": "access_denied"}),
    ]
    with patch.object(cylera_auth, "_post", side_effect=responses):
        result = runner.invoke(app, ["auth", "login", "--no-browser"])

    assert result.exit_code == 1
    assert "declined" in result.output


def test_commands_use_stored_sign_in_and_save_rotated_refresh_token():
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)
    refreshed = _response(200, {"access_token": "workos-access-2",
                                "refresh_token": "refresh-2"})
    with patch.object(cylera_auth, "_post", return_value=refreshed) as post, \
         _exchange() as exchange, patch("cylera.CyleraClient") as client:
        get_client()

    assert post.call_args.args[1]["refresh_token"] == "refresh-1"
    assert exchange.call_args.kwargs["json"] == {"token": "workos-access-2"}
    client.assert_called_once_with(token="cylera-token", base_url=BASE_URL)
    assert cylera_auth.stored_login(BASE_URL)["refresh_token"] == "refresh-2"


def test_expired_sign_in_is_forgotten():
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)
    with patch.object(cylera_auth, "_post",
                      return_value=_response(400, {"error": "invalid_grant"})):
        result = runner.invoke(app, ["organization"])

    assert result.exit_code == 1
    assert "cylera auth login" in result.output
    assert cylera_auth.stored_login(BASE_URL) is None


def test_password_wins_over_stored_sign_in(monkeypatch):
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)
    monkeypatch.setenv("CYLERA_USERNAME", "test@example.com")
    monkeypatch.setenv("CYLERA_PASSWORD", "secret")
    with patch.object(cylera_auth, "_post") as post, patch("cylera.CyleraClient") as client:
        get_client()

    post.assert_not_called()
    client.assert_called_once_with(
        username="test@example.com", password="secret", base_url=BASE_URL)


def test_status_and_logout():
    assert runner.invoke(app, ["auth", "status"]).exit_code == 1
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)

    status = runner.invoke(app, ["auth", "status"])
    assert "Signed in through WorkOS as test@example.com" in status.output

    assert "Signed out" in runner.invoke(app, ["auth", "logout"]).output
    assert cylera_auth.stored_login(BASE_URL) is None


def test_not_configured_suggests_login():
    result = runner.invoke(app, ["organization"])

    assert result.exit_code == 1
    assert "cylera auth login" in result.output


def test_login_asks_for_region_and_remembers_it(device_flow, monkeypatch):
    monkeypatch.delenv("CYLERA_BASE_URL")
    with _exchange() as exchange, patch("cylera.CyleraClient"), patch("cylera.Organization"):
        result = runner.invoke(app, ["auth", "login", "--no-browser"], input="2\n")

    assert result.exit_code == 0, result.output
    assert "Select your Cylera API endpoint" in result.output
    uk = "https://partner.uk1.cylera.com/"
    assert exchange.call_args.args[0] == "https://partner.uk1.cylera.com/auth/token_exchange"
    assert cylera_auth.default_base_url() == uk

    # Later commands use it without CYLERA_BASE_URL, from any directory.
    assert "on https://partner.uk1.cylera.com/" in runner.invoke(app, ["auth", "status"]).output


def test_login_base_url_option_skips_question(device_flow, monkeypatch):
    monkeypatch.delenv("CYLERA_BASE_URL")
    with _exchange() as exchange, patch("cylera.CyleraClient"), patch("cylera.Organization"):
        result = runner.invoke(
            app, ["auth", "login", "--no-browser", "--base-url", "http://127.0.0.1:8123"])

    assert result.exit_code == 0, result.output
    assert "Select your Cylera API endpoint" not in result.output
    assert exchange.call_args.args[0] == "http://127.0.0.1:8123/auth/token_exchange"


def test_environment_wins_over_remembered_region(monkeypatch):
    cylera_auth.save_login("https://partner.uk1.cylera.com/", "client_123", AUTHENTICATION)
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)
    cylera_auth._set_default_base_url("https://partner.uk1.cylera.com/")

    assert f"on {BASE_URL}" in runner.invoke(app, ["auth", "status"]).output


def test_logout_forgets_remembered_region(monkeypatch):
    monkeypatch.delenv("CYLERA_BASE_URL")
    cylera_auth.save_login(BASE_URL, "client_123", AUTHENTICATION)

    assert "Signed out" in runner.invoke(app, ["auth", "logout"]).output
    assert cylera_auth.default_base_url() is None
    assert runner.invoke(app, ["organization"]).exit_code == 1
