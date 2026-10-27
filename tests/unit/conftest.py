"""Shared fixtures for the unit tests."""

import pytest

import cylera_auth


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """Keep every test away from the real ~/.config/cylera/, where a
    stored 'cylera auth login' would otherwise count as configured."""
    monkeypatch.setattr(cylera_auth, "CREDENTIALS_PATH", tmp_path / "credentials.json")
    monkeypatch.setattr(cylera_auth, "CONFIG_PATH", tmp_path / "config.json")
