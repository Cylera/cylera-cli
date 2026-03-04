#!/usr/bin/env bash
#
# Run all tests and quality checks for the Cylera CLI.
#

set -e

USE_DOPPLER=false
VERBOSE=false

show_help() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run all tests and quality checks for the Cylera CLI.

Options:
    --use-doppler    Use Doppler secrets management
    --verbose        Show pytest output (-s flag)
    --help           Show this help message and exit.

Examples:
    $(basename "$0")               # Run tests using local .env file
    $(basename "$0") --use-doppler # Run tests using Doppler secrets
    $(basename "$0") --verbose     # Run tests with output shown
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  --use-doppler)
    USE_DOPPLER=true
    shift
    ;;
  --verbose)
    VERBOSE=true
    shift
    ;;
  --help)
    show_help
    exit 0
    ;;
  *)
    echo "Unknown option: $1"
    echo "Use --help for usage information."
    exit 1
    ;;
  esac
done

# Check for doppler CLI if --use-doppler was specified
if [ "$USE_DOPPLER" = true ]; then
  if ! doppler --version >/dev/null 2>&1; then
    echo "Error: Doppler CLI is not installed or not in PATH."
    echo "Please install Doppler CLI: https://docs.doppler.com/docs/install-cli"
    exit 1
  fi
fi

check_environment_variables() {
  REQUIRED_VARS=(CYLERA_BASE_URL CYLERA_USERNAME CYLERA_PASSWORD)
  missing=()
  for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
      missing+=("$var")
    fi
  done
  if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: The following required environment variables are not set:"
    for var in "${missing[@]}"; do
      echo "  - $var"
    done
    echo "Run 'cylera init' or set them in your .env file."
    exit 1
  fi
}

run_pytest() {
  PYTEST_ARGS=(-v)
  if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=(-s)
  fi
  if [ "$USE_DOPPLER" = true ]; then
    doppler run -- uv run pytest "${PYTEST_ARGS[@]}" || exit 1
  else
    uv run pytest "${PYTEST_ARGS[@]}" || exit 1
  fi
}

run_integration_tests() {
  INTEGRATION_ARGS=()
  if [ "$USE_DOPPLER" = true ]; then
    INTEGRATION_ARGS+=(--use-doppler)
  fi
  bash "$(dirname "$0")/tests/integration/test.sh" "${INTEGRATION_ARGS[@]}"
}

lint_shellscripts() {
  shellcheck test.sh tests/integration/test.sh
}

check_app_security() {
  uvx bandit -c bandit.yaml ./*.py
}

if [ "$USE_DOPPLER" = false ]; then
  # Load .env if present so credentials don't need to be exported separately
  if [ -f "$(dirname "$0")/.env" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$(dirname "$0")/.env"
    set +a
  fi
  check_environment_variables
fi

echo "******** Running pytest (unit tests) **********"
run_pytest
echo "******** Running shellcheck **********"
lint_shellscripts
echo "******** Running bandit (security) **********"
check_app_security
echo "******** Running integration tests **********"
run_integration_tests

echo ""
echo "=== All checks passed! ==="
