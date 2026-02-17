#!/usr/bin/env python3
"""
Cylera CLI - Command line interface for the Cylera Partner API.

Usage: cylera <command> [arguments...]

This CLI provides read-only access to the Cylera Partner API for querying
device inventory, threats, vulnerabilities, and network information.
"""

import getpass
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from dotenv import load_dotenv

from cylera_client import (
    CyleraClient,
    Inventory,
    Network,
    Risk,
    Threat,
    Utilization,
    CyleraAPIError,
    CyleraAuthError,
)

# Available Cylera API endpoints
CYLERA_URLS = [
    "https://partner.us1.cylera.com/",
    "https://partner.uk1.cylera.com/",
    "https://partner.demo.cylera.com/",
]

app = typer.Typer(
    name="cylera",
    help="Cylera CLI - Command line interface for the Cylera Partner API",
    add_completion=False,
    no_args_is_help=True,
)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2))


def get_client() -> CyleraClient:
    """Create and return a CyleraClient using environment variables."""
    base_url = os.environ.get("CYLERA_BASE_URL")
    username = os.environ.get("CYLERA_USERNAME")
    password = os.environ.get("CYLERA_PASSWORD")

    if not base_url or not username or not password:
        print(
            "Error: Missing required environment variables.\n"
            "Please set CYLERA_BASE_URL, CYLERA_USERNAME, and CYLERA_PASSWORD\n"
            "in your environment or .env file.",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    return CyleraClient(username=username, password=password, base_url=base_url)


def check_environment() -> bool:
    """Check if required environment variables are set."""
    load_dotenv(Path.cwd() / ".env")
    base_url = os.environ.get("CYLERA_BASE_URL")
    username = os.environ.get("CYLERA_USERNAME")
    password = os.environ.get("CYLERA_PASSWORD")
    return bool(base_url and username and password)


def require_config() -> None:
    """Check that CLI is configured, exit with message if not."""
    if not check_environment():
        print(
            f"Cylera CLI is not configured.\n\n"
            f"Current directory: {Path.cwd()}\n\n"
            "Run 'cylera init' to set up your credentials.",
            file=sys.stderr,
        )
        raise typer.Exit(1)


# Common option types
PageOption = Annotated[Optional[int], typer.Option(
    help="Page number for pagination")]
PageSizeOption = Annotated[
    Optional[int], typer.Option(
        "--page-size", help="Results per page (max 100)")
]
MacAddressOption = Annotated[
    Optional[str], typer.Option("--mac-address", help="MAC address of device")
]
SeverityOption = Annotated[
    Optional[str],
    typer.Option(help="Severity level: INFO, LOW, MEDIUM, HIGH, CRITICAL"),
]
StatusOption = Annotated[
    Optional[str],
    typer.Option(help="Status: OPEN, IN_PROGRESS, RESOLVED, SUPPRESSED"),
]
DetectedAfterOption = Annotated[
    Optional[int], typer.Option(
        "--detected-after", help="Epoch timestamp filter")
]


def _check_existing_config() -> None:
    """Exit with error if Cylera environment variables are already set."""
    var_names = ["CYLERA_BASE_URL", "CYLERA_USERNAME", "CYLERA_PASSWORD"]
    existing_vars = [v for v in var_names if os.environ.get(v)]
    if existing_vars:
        print(
            "Error: The following environment variables are already set:\n"
            f"  {', '.join(existing_vars)}\n\n"
            "To reconfigure, unset these variables first or delete the .env file.\n"
            "Example: unset CYLERA_BASE_URL CYLERA_USERNAME CYLERA_PASSWORD",
            file=sys.stderr,
        )
        raise typer.Exit(1)


def _prompt_base_url() -> str:
    """Prompt user to select a Cylera API endpoint and return the URL."""
    print("Select your Cylera API endpoint:")
    for i, url in enumerate(CYLERA_URLS, 1):
        print(f"  {i}. {url}")
    print()

    while True:
        try:
            choice = input(f"Enter choice [1-{len(CYLERA_URLS)}]: ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(CYLERA_URLS):
                return CYLERA_URLS[choice_num - 1]
            print(f"Please enter a number between 1 and {len(CYLERA_URLS)}")
        except ValueError:
            print("Please enter a valid number")


def _test_auth(username: str, password: str, base_url: str) -> None:
    """Test authentication and print the response. Exits on failure."""
    print("Testing authentication...", end=" ", flush=True)
    try:
        client = CyleraClient(
            username=username, password=password, base_url=base_url)
        auth_response = client.test_authenticate()
        client.close()
    except CyleraAuthError as e:
        print("Failed!")
        print(f"\nAuthentication error: {e}", file=sys.stderr)
        print("\nPlease check your credentials and try again.", file=sys.stderr)
        raise typer.Exit(1)

    print("Success!")
    print()
    print("Authentication response:")
    for key, value in auth_response.items():
        if key != "token":
            print(f"  {key}: {value}")


def _save_env_config(base_url: str, username: str, password: str) -> Path:
    """Append Cylera config to the .env file and return the path."""
    env_path = Path.cwd() / ".env"

    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()
        if existing_content and not existing_content.endswith("\n"):
            existing_content += "\n"

    cylera_config = (
        f"\n# Cylera CLI Configuration\n"
        f"CYLERA_BASE_URL={base_url}\n"
        f"CYLERA_USERNAME={username}\n"
        f"CYLERA_PASSWORD={password}\n"
    )

    env_path.write_text(existing_content + cylera_config)
    return env_path


@app.command()
def init() -> None:
    """Initialize Cylera CLI configuration interactively."""
    load_dotenv()
    _check_existing_config()

    print("Cylera CLI Configuration")
    print("=" * 40)
    print()

    base_url = _prompt_base_url()
    print()

    username = input("Enter your Cylera username (email): ").strip()
    if not username:
        print("Error: Username cannot be empty", file=sys.stderr)
        raise typer.Exit(1)

    print()

    password = getpass.getpass("Enter your Cylera password: ")
    if not password:
        print("Error: Password cannot be empty", file=sys.stderr)
        raise typer.Exit(1)

    print()
    _test_auth(username, password, base_url)

    env_path = _save_env_config(base_url, username, password)

    print()
    print(f"Configuration saved to {env_path}")
    print()
    print("You can now use the Cylera CLI. Try:")
    print("  cylera devices --page-size 5")


@app.command()
def device(
    device_id: Annotated[str, typer.Argument(help="MAC address of the device")],
) -> None:
    """Get details for a specific device by MAC address."""
    require_config()
    try:
        with get_client() as client:
            result = Inventory(client).get_device(device_id)
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def devices(
    aetitle: Annotated[Optional[str], typer.Option(
        help="Complete AE Title")] = None,
    device_class: Annotated[
        Optional[str],
        typer.Option(
            "--class", help="Device class (Medical, Infrastructure, etc.)"),
    ] = None,
    hostname: Annotated[Optional[str], typer.Option(
        help="Complete hostname")] = None,
    ip_address: Annotated[
        Optional[str], typer.Option(
            "--ip-address", help="Partial or complete IP")
    ] = None,
    mac_address: MacAddressOption = None,
    model: Annotated[Optional[str], typer.Option(help="Device model")] = None,
    os: Annotated[Optional[str], typer.Option(help="Operating system")] = None,
    page: PageOption = None,
    page_size: PageSizeOption = None,
    serial_number: Annotated[
        Optional[str], typer.Option(
            "--serial-number", help="Complete serial number")
    ] = None,
    since_last_seen: Annotated[
        Optional[int],
        typer.Option("--since-last-seen",
                     help="[DEPRECATED] Seconds since last seen"),
    ] = None,
    device_type: Annotated[
        Optional[str], typer.Option(
            "--type", help="Device type (EEG, X-Ray, etc.)")
    ] = None,
    vendor: Annotated[Optional[str], typer.Option(
        help="Device vendor")] = None,
    first_seen_before: Annotated[
        Optional[int], typer.Option(
            "--first-seen-before", help="Epoch timestamp")
    ] = None,
    first_seen_after: Annotated[
        Optional[int], typer.Option(
            "--first-seen-after", help="Epoch timestamp")
    ] = None,
    last_seen_before: Annotated[
        Optional[int], typer.Option(
            "--last-seen-before", help="Epoch timestamp")
    ] = None,
    last_seen_after: Annotated[
        Optional[int], typer.Option(
            "--last-seen-after", help="Epoch timestamp")
    ] = None,
    attribute_label: Annotated[
        Optional[str], typer.Option(
            "--attribute-label", help="Attribute label filter")
    ] = None,
) -> None:
    """Get a list of devices with optional filters."""
    require_config()
    try:
        with get_client() as client:
            result = Inventory(client).get_devices(
                aetitle=aetitle,
                device_class=device_class,
                hostname=hostname,
                ip_address=ip_address,
                mac_address=mac_address,
                model=model,
                os=os,
                page=page,
                page_size=page_size,
                serial_number=serial_number,
                since_last_seen=since_last_seen,
                device_type=device_type,
                vendor=vendor,
                first_seen_before=first_seen_before,
                first_seen_after=first_seen_after,
                last_seen_before=last_seen_before,
                last_seen_after=last_seen_after,
                attribute_label=attribute_label,
            )
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def deviceattributes(
    mac_address: Annotated[str, typer.Argument(help="MAC address of the device")],
) -> None:
    """Get attributes for a device by MAC address."""
    require_config()
    try:
        with get_client() as client:
            result = Inventory(client).get_device_attributes(mac_address)
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def procedures(
    procedure_name: Annotated[
        Optional[str],
        typer.Option("--procedure-name",
                     help="Procedure name (partial match)"),
    ] = None,
    accession_number: Annotated[
        Optional[str], typer.Option(
            "--accession-number", help="Accession number")
    ] = None,
    device_uuid: Annotated[
        Optional[str], typer.Option("--device-uuid", help="Device UUID")
    ] = None,
    completed_after: Annotated[
        Optional[str], typer.Option(
            "--completed-after", help="Date (YYYY/MM/DD)")
    ] = None,
    page: PageOption = None,
    page_size: PageSizeOption = None,
) -> None:
    """Get a list of medical procedures."""
    require_config()
    try:
        with get_client() as client:
            result = Utilization(client).get_procedures(
                procedure_name=procedure_name,
                accession_number=accession_number,
                device_uuid=device_uuid,
                completed_after=completed_after,
                page=page,
                page_size=page_size,
            )
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def subnets(
    cidr_range: Annotated[
        Optional[str], typer.Option(
            "--cidr-range", help="CIDR range (partial match)")
    ] = None,
    description: Annotated[
        Optional[str], typer.Option(help="Subnet description")
    ] = None,
    vlan: Annotated[Optional[int], typer.Option(help="VLAN number")] = None,
    page: PageOption = None,
    page_size: PageSizeOption = None,
) -> None:
    """Get a list of network subnets."""
    require_config()
    try:
        with get_client() as client:
            result = Network(client).get_subnets(
                cidr_range=cidr_range,
                description=description,
                vlan=vlan,
                page=page,
                page_size=page_size,
            )
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def riskmitigations(
    vulnerability: Annotated[str, typer.Argument(help="Name of the vulnerability")],
) -> None:
    """Get mitigations for a specific vulnerability."""
    require_config()
    try:
        with get_client() as client:
            result = Risk(client).get_mitigations(vulnerability)
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def vulnerabilities(
    confidence: Annotated[
        Optional[str], typer.Option(help="Confidence: LOW, MEDIUM, HIGH")
    ] = None,
    detected_after: DetectedAfterOption = None,
    mac_address: MacAddressOption = None,
    name: Annotated[
        Optional[str], typer.Option(help="Vulnerability name (partial match)")
    ] = None,
    page: PageOption = None,
    page_size: PageSizeOption = None,
    severity: SeverityOption = None,
    status: StatusOption = None,
) -> None:
    """Get a list of vulnerabilities."""
    require_config()
    try:
        with get_client() as client:
            result = Risk(client).get_vulnerabilities(
                confidence=confidence,
                detected_after=detected_after,
                mac_address=mac_address,
                name=name,
                page=page,
                page_size=page_size,
                severity=severity,
                status=status,
            )
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def threats(
    detected_after: DetectedAfterOption = None,
    mac_address: MacAddressOption = None,
    name: Annotated[
        Optional[str], typer.Option(help="Threat name (partial match)")
    ] = None,
    page: PageOption = None,
    page_size: PageSizeOption = None,
    severity: SeverityOption = None,
    status: StatusOption = None,
) -> None:
    """Get a list of detected threats."""
    require_config()
    try:
        with get_client() as client:
            result = Threat(client).get_threats(
                detected_after=detected_after,
                mac_address=mac_address,
                name=name,
                page=page,
                page_size=page_size,
                severity=severity,
                status=status,
            )
        print_json(result)
    except CyleraAPIError as e:
        print(f"API error: {e}", file=sys.stderr)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
