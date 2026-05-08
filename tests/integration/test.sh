#!/usr/bin/env bash
# Test script for the Cylera CLI

set -e # Exit on first error

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIXTURES_DIR="$(cd "$(dirname "$0")/fixtures" && pwd)"

USE_DOPPLER=false
USE_OP=false
MIN_OP_VERSION="2.33.0-beta.02"

show_help() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run all tests for the Cylera CLI.

Options:
    --use-doppler              Use Doppler secrets management
    --use-op                   Use 1Password CLI secrets management (requires OP_ENVIRONMENT_ID env var)
    --help                     Show this help message and exit.

Examples:
    $(basename "$0")                                      # Run tests using local .env file
    $(basename "$0") --use-doppler                        # Run tests using Doppler secrets
    OP_ENVIRONMENT_ID=<env-id> $(basename "$0") --use-op  # Run tests using 1Password secrets
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  --use-doppler)
    USE_DOPPLER=true
    shift
    ;;
  --use-op)
    USE_OP=true
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

# Mutual exclusion check
if [[ "$USE_DOPPLER" = true && "$USE_OP" = true ]]; then
  echo "Error: --use-doppler and --use-op are mutually exclusive." >&2
  exit 1
fi

# Check for doppler CLI if --use-doppler was specified
if [[ "$USE_DOPPLER" = true ]] && ! doppler --version >/dev/null 2>&1; then
  echo "Error: Doppler CLI is not installed or not in PATH." >&2
  echo "Please install Doppler CLI: https://docs.doppler.com/docs/install-cli"
  exit 1
fi

version_gte() {
  local ver1="$1"
  local ver2="$2"
  # Returns 0 if ver1 >= ver2 using version sort
  printf '%s\n%s\n' "$ver2" "$ver1" | sort -V -C
}

# Check for 1Password CLI if --use-op was specified
if [[ "$USE_OP" = true ]]; then
  if ! op --version >/dev/null 2>&1; then
    echo "Error: 1Password CLI (op) is not installed or not in PATH." >&2
    echo "Please install 1Password CLI: https://developer.1password.com/docs/cli/get-started/"
    exit 1
  fi
  installed_op_version=$(op --version)
  if ! version_gte "$installed_op_version" "$MIN_OP_VERSION"; then
    echo "Error: 1Password CLI version $installed_op_version is too old." >&2
    echo "Please upgrade to version $MIN_OP_VERSION or later."
    exit 1
  fi
  if [[ -z "$OP_ENVIRONMENT_ID" ]]; then
    echo "Error: OP_ENVIRONMENT_ID environment variable must be set when using --use-op." >&2
    exit 1
  fi
fi

# Pin terminal width so rich renders help text consistently regardless of
# the actual terminal size the tests are run in.
export COLUMNS=80

# Wrapper: run cylera with secrets injected via Doppler, 1Password, or the local .env file.
run_cylera() {
  if [[ "$USE_DOPPLER" = true ]]; then
    doppler run -- uv run --directory "$REPO_ROOT" python cylera.py "$@"
  elif [[ "$USE_OP" = true ]]; then
    op run --environment "$OP_ENVIRONMENT_ID" -- uv run --directory "$REPO_ROOT" python cylera.py "$@"
  else
    uv run --directory "$REPO_ROOT" python cylera.py "$@"
  fi
}

# Helper function for tests that compare output against expected files
run_test() {
  local test_num=$1
  local test_name=$2
  shift 2
  local cmd_args=("$@")

  echo "Test $test_num: $test_name"
  output=$(run_cylera "${cmd_args[@]}" 2>&1)
  expected=$(cat "$FIXTURES_DIR/test${test_num}.expected")
  if [[ "$output" = "$expected" ]]; then
    echo "PASS: $test_name"
  else
    echo "FAIL: $test_name"
    echo "Expected:"
    echo "$expected"
    echo "Got:"
    echo "$output"
    exit 1
  fi
  echo
}

# Like run_test but strips volatile JSON fields (last_seen) before comparing.
# Used for live API tests where timestamps tick forward.
JQ_STRIP='walk(if type == "object" then del(.last_seen, .total, .total_devices, .count) else . end)'
run_api_test() {
  local test_num=$1
  local test_name=$2
  shift 2
  local cmd_args=("$@")

  echo "Test $test_num: $test_name"
  output=$(run_cylera "${cmd_args[@]}" | jq "$JQ_STRIP")
  expected=$(cat "$FIXTURES_DIR/test${test_num}.expected")
  if [[ "$output" = "$expected" ]]; then
    echo "PASS: $test_name"
  else
    echo "FAIL: $test_name"
    echo "Expected:"
    echo "$expected"
    echo "Got:"
    echo "$output"
    exit 1
  fi
  echo
}

echo "=== Cylera CLI Tests ==="
echo

# =============================================================================
# Test 1: Organization — live API query
# =============================================================================

run_api_test 1  "Organization"                                    organization

# =============================================================================
# Tests 2-10: Help output for each command
# =============================================================================

run_test 2  "Main help output"              --help
run_test 3  "Devices command help"          devices --help
run_test 4  "Device command help"           device --help
run_test 5  "Deviceattributes command help" deviceattributes --help
run_test 6  "Procedures command help"       procedures --help
run_test 7  "Subnets command help"          subnets --help
run_test 8  "Riskmitigations command help"  riskmitigations --help
run_test 9  "Vulnerabilities command help"  vulnerabilities --help
run_test 10 "Threats command help"          threats --help

# =============================================================================
# Test 11: Missing config — always runs without Doppler/env file so that
# the credential-checking logic itself is what's being tested.
# =============================================================================

echo "Test 11: Missing config error" >&2
exit_code=0
output=$(CYLERA_BASE_URL="" CYLERA_USERNAME="" CYLERA_PASSWORD="" uv run --no-env-file cylera devices 2>&1) || exit_code=$?
# Strip the dynamic "Current directory:" line before comparing
filtered=$(echo "$output" | grep -v "^Current directory:")
expected=$(grep -v "^exit:" "$FIXTURES_DIR/test11.expected")
expected_exit=$(grep "^exit:" "$FIXTURES_DIR/test11.expected" | cut -d: -f2)
if [[ "$filtered" = "$expected" && "$exit_code" = "$expected_exit" ]]; then
  echo "PASS: Missing config error" >&2
else
  echo "FAIL: Missing config error" >&2
  echo "Expected exit code $expected_exit, got: $exit_code"
  echo "Expected output (sans Current directory line):"
  echo "$expected"
  echo "Got (sans Current directory line):"
  echo "$filtered"
  exit 1
fi
echo

# =============================================================================
# Tests 12-18: Live API queries against the demo environment
# =============================================================================

run_api_test 12 "Devices default page"                            devices --page-size 1
run_api_test 13 "Devices filtered by vendor (Philips)"           devices --page-size 1 --vendor Philips
run_api_test 14 "Devices filtered by class and IP prefix"        devices --page-size 1 --class Medical --ip-address 10.30
run_api_test 15 "Vulnerabilities default page"                   vulnerabilities --page-size 1
run_api_test 16 "Threats default page"                           threats --page-size 1
run_api_test 17 "Subnets list"                                   subnets
run_api_test 18 "Vulnerabilities filtered by severity (MEDIUM)"  vulnerabilities --page-size 1 --severity MEDIUM

echo "=== All tests passed! ==="
