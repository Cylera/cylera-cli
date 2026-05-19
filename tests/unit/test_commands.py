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
         patch("cylera.Organization", return_value=mock_org), \
         patch("cylera.time.sleep"):
        result = runner.invoke(app, ["switchorg", "org-1"])

    assert result.exit_code == 0
    parsed, _ = json.JSONDecoder().raw_decode(result.output)
    assert parsed == payload
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
# resetorg
# ---------------------------------------------------------------------------

def test_resetorg(mock_client):
    payload = {"reset": True}
    mock_org = MagicMock()
    mock_org.reset_organization.return_value = payload

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["resetorg"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_resetorg_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_org = MagicMock()
    mock_org.reset_organization.side_effect = CyleraAPIError("forbidden")

    with patch("cylera.get_client", return_value=mock_client), \
         patch("cylera.Organization", return_value=mock_org):
        result = runner.invoke(app, ["resetorg"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# device (error path)
# ---------------------------------------------------------------------------

def test_device_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("not found")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["device", "aa:bb:cc:dd:ee:ff"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# devices (error path)
# ---------------------------------------------------------------------------

def test_devices_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("server error")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["devices"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# deviceattributes
# ---------------------------------------------------------------------------

def test_deviceattributes(mock_client):
    payload = {"attributes": [{"label": "Department", "value": "Radiology"}]}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["deviceattributes", "aa:bb:cc:dd:ee:ff"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_deviceattributes_requires_mac():
    result = runner.invoke(app, ["deviceattributes"])
    assert result.exit_code != 0


def test_deviceattributes_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("not found")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["deviceattributes", "aa:bb:cc:dd:ee:ff"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# procedures
# ---------------------------------------------------------------------------

def test_procedures_no_filters(mock_client):
    payload = {"procedures": [], "total": 0}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["procedures"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_procedures_with_filters(mock_client):
    payload = {"procedures": [{"name": "MRI Scan"}], "total": 1}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["procedures", "--procedure-name", "MRI"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_procedures_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("server error")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["procedures"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# subnets
# ---------------------------------------------------------------------------

def test_subnets_no_filters(mock_client):
    payload = {"subnets": [], "total": 0}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["subnets"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_subnets_with_filters(mock_client):
    payload = {"subnets": [{"cidr": "10.0.0.0/24"}], "total": 1}  # NOSONAR(python:S1313)
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["subnets", "--cidr-range", "10.0.0"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_subnets_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("server error")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["subnets"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# riskmitigations
# ---------------------------------------------------------------------------

def test_riskmitigations(mock_client):
    payload = {"mitigations": [{"title": "Apply patch"}]}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["riskmitigations", "CVE-2021-1234"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_riskmitigations_requires_vulnerability():
    result = runner.invoke(app, ["riskmitigations"])
    assert result.exit_code != 0


def test_riskmitigations_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("not found")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["riskmitigations", "CVE-2021-1234"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# vulnerabilities
# ---------------------------------------------------------------------------

def test_vulnerabilities_no_filters(mock_client):
    payload = {"vulnerabilities": [], "total": 0}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["vulnerabilities"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_vulnerabilities_with_filters(mock_client):
    payload = {"vulnerabilities": [{"name": "Log4Shell"}], "total": 1}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["vulnerabilities", "--severity", "HIGH", "--status", "OPEN"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_vulnerabilities_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("server error")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["vulnerabilities"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# threats
# ---------------------------------------------------------------------------

def test_threats_no_filters(mock_client):
    payload = {"threats": [], "total": 0}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["threats"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_threats_with_filters(mock_client):
    payload = {"threats": [{"name": "Lateral Movement"}], "total": 1}
    mock_client._make_request.return_value = payload

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["threats", "--severity", "HIGH"])

    assert result.exit_code == 0
    assert json.loads(result.output) == payload


def test_threats_api_error(mock_client):
    from cylera_client import CyleraAPIError
    mock_client._make_request.side_effect = CyleraAPIError("server error")

    with patch("cylera.get_client", return_value=mock_client):
        result = runner.invoke(app, ["threats"])

    assert result.exit_code == 1


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
