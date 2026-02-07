# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cylera CLI is a Python command-line interface for the Cylera Partner API, providing read-only access to medical device inventory, threats, vulnerabilities, and network information for healthcare security.

## Development Commands

```bash
# Install as a tool (recommended for development)
uv tool install .

# Run without installing
uvx cylera --help

# Uninstall
uv tool uninstall cylera

# Enable debug output (shows API request details)
DEBUG=1 cylera devices --page-size 1
```

## Architecture

The codebase consists of two main Python modules at the root level:

- **cylera.py**: CLI entry point using Typer. Defines all commands (`init`, `device`, `devices`, `deviceattributes`, `procedures`, `subnets`, `riskmitigations`, `vulnerabilities`, `threats`). Handles configuration via `.env` file or environment variables.

- **cylera_client.py**: API client layer with:
  - `CyleraClient`: HTTP session management with automatic token refresh (23-hour expiry). Supports context manager usage.
  - Domain-specific helper classes: `Inventory`, `Utilization`, `Network`, `Risk`, `Threat` - each wraps API endpoints with typed parameters.

## Configuration

Requires three environment variables (stored in `.env` or set directly):
- `CYLERA_BASE_URL`: API endpoint (US, UK, or Demo)
- `CYLERA_USERNAME`: Email for authentication
- `CYLERA_PASSWORD`: Password

Run `cylera init` for interactive setup with credential validation.

## API Regions

- US: `https://partner.us1.cylera.com/`
- UK: `https://partner.uk1.cylera.com/`
- Demo: `https://partner.demo.cylera.com/`
