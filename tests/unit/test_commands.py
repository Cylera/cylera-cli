"""
Tests for cylera.py CLI commands.

All tests mock the CyleraClient so no real API calls are made.
"""

import json
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from cylera import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    """A MagicMock that acts as a CyleraClient context manager."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


@pytest.fixture(autouse=True)
def env(monkeypatch):
    """Set required environment variables for every test."""
    monkeypatch.setenv("CYLERA_BASE_URL", "https://partner.demo.cylera.com/")
    monkeypatch.setenv("CYLERA_USERNAME", "test@example.com")
    monkeypatch.setenv("CYLERA_PASSWORD", "secret")


# ---------------------------------------------------------------------------
# organization
# ---------------------------------------------------------------------------

def test_organization(mock_client):
    payload = {"name": "Acme Hospital"}
    mock_org = MagicMock()
    mock_org.get_organization.return_value = payload

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["organization"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_organization_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_org = MagicMock()
    mock_org.get_organization.side_effect = CyleraAPIError("boom")

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["organization"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# organizations
# ---------------------------------------------------------------------------

def test_organizations(mock_client):
    payload = [{"id": "org-1", "name": "Acme"}, {"id": "org-2", "name": "Beta"}]
    mock_org = MagicMock()
    mock_org.get_available_organizations.return_value = payload

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["organizations"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_organizations_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_org = MagicMock()
    mock_org.get_available_organizations.side_effect = CyleraAPIError("unauthorized")

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["organizations"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# switchorg
# ---------------------------------------------------------------------------

def test_switchorg(mock_client):
    payload = {"switched": True}
    mock_org = MagicMock()
    mock_org.switch_organization.return_value = payload

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["switchorg", "org-1"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload
    mock_org.switch_organization.assert_called_once_with("org-1")


def test_switchorg_requires_org_id():
    result = runner.invoke(app, ["switchorg"])
    assert result.exit_code != 0


def test_switchorg_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_org = MagicMock()
    mock_org.switch_organization.side_effect = CyleraAPIError("not allowed")

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["switchorg", "org-bad"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# device
# ---------------------------------------------------------------------------

def test_device(mock_client):
    payload = {"device": {"mac_address": "aa:bb:cc:dd:ee:ff"}}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["device", "aa:bb:cc:dd:ee:ff"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


# ---------------------------------------------------------------------------
# devices
# ---------------------------------------------------------------------------

def test_devices_no_filters(mock_client):
    payload = {"devices": [], "total": 0, "page": 1}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["devices"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_devices_with_filters(mock_client):
    payload = {"devices": [{"vendor": "Philips"}], "total": 1, "page": 1}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["devices", "--vendor", "Philips", "--page-size", "10"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


# ---------------------------------------------------------------------------
# Missing config
# ---------------------------------------------------------------------------

def test_missing_config_exits(monkeypatch):
    monkeypatch.delenv("CYLERA_BASE_URL")
    monkeypatch.delenv("CYLERA_USERNAME")
    monkeypatch.delenv("CYLERA_PASSWORD")
    with patch("cylera.load_dotenv"):  # prevent .env from restoring credentials
        result = runner.invoke(app, ["organization"])
    assert result.exit_code == 1
