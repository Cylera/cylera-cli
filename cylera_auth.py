"""
WorkOS sign-in for the Cylera CLI (`cylera auth login`).

Uses the WorkOS CLI Auth flow (the OAuth 2.0 Device Authorization Grant,
RFC 8628) as a public client: only a client ID, no API key or secret. The
WorkOS refresh token is stored per Partner API URL; each command refreshes
it for a WorkOS access token and exchanges that at the Partner API's
POST /auth/token_exchange for a Cylera token. The Partner API URL last
signed in to becomes the default, so commands work from any directory.

Prototype: the WorkOS client ID comes from CYLERA_WORKOS_CLIENT_ID rather
than being discovered from the Partner API.
"""

import json
import os
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable, Optional

import requests

WORKOS_API = "https://api.workos.com/user_management"
DEVICE_CODE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
CREDENTIALS_PATH = Path.home() / ".config" / "cylera" / "credentials.json"
CONFIG_PATH = Path.home() / ".config" / "cylera" / "config.json"


class CyleraLoginError(Exception):
    """Sign-in failed, or the stored sign-in no longer works."""


def _key(base_url: str) -> str:
    return base_url.rstrip("/")


def _read_credentials() -> dict[str, Any]:
    if not CREDENTIALS_PATH.exists():
        return {}
    return json.loads(CREDENTIALS_PATH.read_text())


def _write_credentials(credentials: dict[str, Any]) -> None:
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Created owner-only: the refresh token works on its own.
    fd = os.open(CREDENTIALS_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(credentials, f, indent=2)


def default_base_url() -> Optional[str]:
    """The Partner API URL last signed in to, or None."""
    if not CONFIG_PATH.exists():
        return None
    return json.loads(CONFIG_PATH.read_text()).get("base_url")


def _set_default_base_url(base_url: Optional[str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"base_url": base_url}, indent=2))


def stored_login(base_url: str) -> Optional[dict[str, Any]]:
    """The stored sign-in for this Partner API, or None."""
    return _read_credentials().get(_key(base_url))


def _store_login(base_url: str, login: dict[str, Any]) -> None:
    credentials = _read_credentials()
    credentials[_key(base_url)] = login
    _write_credentials(credentials)


def forget_login(base_url: str) -> bool:
    """Delete the stored sign-in for this Partner API. True if there was one."""
    credentials = _read_credentials()
    if credentials.pop(_key(base_url), None) is None:
        return False
    _write_credentials(credentials)
    if default_base_url() == base_url:
        _set_default_base_url(None)
    return True


def _post(path: str, data: dict[str, str]) -> requests.Response:
    return requests.post(f"{WORKOS_API}/{path}", data=data, timeout=30)


def device_login(
    client_id: str,
    show: Callable[[str], None] = print,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Run the device flow until the user confirms in the browser.

    Returns WorkOS's authentication response (user, access_token,
    refresh_token, ...). Raises CyleraLoginError if the user declines or
    the code expires.
    """
    response = _post("authorize/device", {"client_id": client_id})
    if not response.ok:
        raise CyleraLoginError(f"WorkOS refused the sign-in request: {response.text}")
    device = response.json()

    url = device["verification_uri_complete"]
    show(f"Open this page to sign in: {url}")
    show(f"Confirm this code matches: {device['user_code']}")
    if open_browser:
        webbrowser.open(url)

    interval = device.get("interval", 5)
    deadline = time.monotonic() + device.get("expires_in", 300)
    while time.monotonic() < deadline:
        time.sleep(interval)
        response = _post("authenticate", {
            "grant_type": DEVICE_CODE_GRANT,
            "device_code": device["device_code"],
            "client_id": client_id,
        })
        if response.ok:
            return response.json()
        error = response.json().get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "access_denied":
            raise CyleraLoginError("Sign-in was declined.")
        if error == "expired_token":
            break
        raise CyleraLoginError(f"WorkOS sign-in failed: {response.text}")
    raise CyleraLoginError("The sign-in code expired. Run 'cylera auth login' again.")


def exchange_token(base_url: str, workos_access_token: str, email: str, at_login: bool = False) -> str:
    """Exchange a WorkOS access token for a Cylera token.

    email is the WorkOS account it was issued for, named if Cylera
    refuses it. The exchange doesn't say why it refuses (no Cylera
    account, not migrated yet, disabled), so the message doesn't guess.
    """
    response = requests.post(
        f"{_key(base_url)}/auth/token_exchange",
        json={"token": workos_access_token},
        timeout=30,
    )
    if response.status_code == 404:
        raise CyleraLoginError(
            "This Cylera API doesn't support signing in through WorkOS yet.")
    if response.status_code == 401:
        if at_login:
            raise CyleraLoginError(
                f"Cylera didn't accept the WorkOS account you signed in with ({email}).\n"
                "If that's the wrong account, sign out of WorkOS in your browser, or open\n"
                "the link in a private window with --no-browser. If it's yours, sign in to\n"
                "the Cylera Portal once to finish setting up your account, or ask your\n"
                "Cylera administrator for access."
            )
        raise CyleraLoginError(
            f"Cylera no longer accepts the WorkOS account you signed in with ({email}).\n"
            "Ask your Cylera administrator for access, or run 'cylera auth login' to\n"
            "sign in with another account."
        )
    response.raise_for_status()
    return response.json()["token"]


def save_login(base_url: str, client_id: str, authentication: dict[str, Any]) -> None:
    """Store a fresh sign-in's refresh token, and make its Partner API the default."""
    _store_login(base_url, {
        "client_id": client_id,
        "email": authentication["user"]["email"],
        "refresh_token": authentication["refresh_token"],
    })
    _set_default_base_url(base_url)


def cylera_token(base_url: str) -> str:
    """A Cylera token from the stored sign-in.

    Refreshes the WorkOS session (saving the rotated refresh token) and
    exchanges the new access token. Raises CyleraLoginError if there's no
    stored sign-in, or WorkOS no longer accepts it.
    """
    login = stored_login(base_url)
    if login is None:
        raise CyleraLoginError("Not signed in. Run 'cylera auth login'.")
    response = _post("authenticate", {
        "grant_type": "refresh_token",
        "refresh_token": login["refresh_token"],
        "client_id": login["client_id"],
    })
    if not response.ok:
        if response.json().get("error") == "invalid_grant":
            forget_login(base_url)
            raise CyleraLoginError("Your sign-in has expired. Run 'cylera auth login'.")
        raise CyleraLoginError(f"WorkOS refresh failed: {response.text}")
    authentication = response.json()
    _store_login(base_url, {**login, "refresh_token": authentication["refresh_token"]})
    return exchange_token(base_url, authentication["access_token"], login["email"])
