# Developer Guide

## Setup

```bash
# Install uv (if not already installed)
brew install uv

# Install the CLI as a tool (recommended for development)
uv tool install .

# Or run without installing
uv run python cylera.py --help
```

## Project Structure

```
cylera.py                        # CLI entry point (Typer commands)
cylera_client.py                 # API client (bundled, not imported from package)
pyproject.toml                   # Dependencies and tool config
test.sh                          # Root test runner — run this
tests/
  unit/
    test_commands.py             # Pytest unit tests (mocked, no credentials)
  integration/
    test.sh                      # Live API integration tests
    fixtures/
      test1.expected             # Expected output snapshots for integration tests
      test2.expected
      ...
```

## Running Tests

### Everything (recommended)

```bash
./test.sh
```

Runs unit tests, shellcheck, and integration tests in sequence. Requires credentials
in `.env` or exported in the environment.

```bash
./test.sh --use-doppler                        # inject credentials via Doppler
OP_ENVIRONMENT_ID=<env-id> ./test.sh --use-op  # inject credentials via 1Password
./test.sh --verbose                            # show full pytest output (-s)
```

`--use-doppler` and `--use-op` are mutually exclusive. When using `--use-op`, the
`OP_ENVIRONMENT_ID` environment variable must be set and 1Password CLI `op` must be
installed (version >= 2.33.0-beta.02).

### Unit tests only (no credentials required)

```bash
uv run pytest
```

Fast, fully mocked — safe to run anywhere, anytime.

### Integration tests only

```bash
./tests/integration/test.sh
./tests/integration/test.sh --use-doppler
```

Requires `CYLERA_BASE_URL`, `CYLERA_USERNAME`, and `CYLERA_PASSWORD` to be set
(via `.env` or environment). Makes real API calls against the configured Cylera instance.

## Test Types

| Type | Location | Credentials | Speed |
|---|---|---|---|
| Unit | `tests/unit/test_commands.py` | Not required | Fast (~0.1s) |
| Integration | `tests/integration/test.sh` | Required | Slow (network) |

**Unit tests** use `typer.testing.CliRunner` and mock `CyleraClient` — they verify
command routing, argument wiring, error handling, and config checks without touching
the network.

**Integration tests** make real API calls and compare output against snapshot files
in `tests/integration/fixtures/`. Volatile fields (`last_seen`, `total`, etc.) are
stripped via `jq` before comparison so tests don't fail on data that changes between
runs.

## Updating Integration Test Snapshots

If you add a new command or change existing help text, regenerate the relevant fixture:

```bash
# Regenerate main help snapshot (test2)
COLUMNS=80 uv run python cylera.py --help > tests/integration/fixtures/test2.expected

# Regenerate a command help snapshot (e.g. test3 = devices --help)
COLUMNS=80 uv run python cylera.py devices --help > tests/integration/fixtures/test3.expected
```

`COLUMNS=80` is required to match the fixed terminal width the integration tests use.

## Credentials

Credentials are read from a `.env` file in the project root or from environment variables:

```
CYLERA_BASE_URL=https://partner.demo.cylera.com/
CYLERA_USERNAME=you@example.com
CYLERA_PASSWORD=yourpassword
```

Run `cylera init` for interactive setup with credential validation.

## Enabling Debug Output

```bash
DEBUG=1 cylera devices --page-size 1
```

Prints request URLs and headers (with the `Authorization` token redacted).
