#!/usr/bin/env bash
# Test script for the Cylera CLI

set -e # Exit on first error

USE_DOPPLER=false

show_help() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Run all tests for the Cylera CLI.

Options:
    --use-doppler    Use Doppler secrets management
    --help           Show this help message and exit.

Examples:
    $(basename "$0")               # Run tests using local .env file
    $(basename "$0") --use-doppler # Run tests using Doppler secrets
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  --use-doppler)
    USE_DOPPLER=true
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

# Pin terminal width so rich renders help text consistently regardless of
# the actual terminal size the tests are run in.
export COLUMNS=80

# Wrapper: run cylera with secrets injected via Doppler or the local .env file.
run_cylera() {
  if [ "$USE_DOPPLER" = true ]; then
    doppler run -- uv run python cylera.py "$@"
  else
    uv run python cylera.py "$@"
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
  expected=$(cat "test${test_num}.expected")
  if [ "$output" = "$expected" ]; then
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
JQ_STRIP='walk(if type == "object" then del(.last_seen) else . end)'
run_api_test() {
  local test_num=$1
  local test_name=$2
  shift 2
  local cmd_args=("$@")

  echo "Test $test_num: $test_name"
  output=$(run_cylera "${cmd_args[@]}" 2>&1 | jq "$JQ_STRIP")
  expected=$(cat "test${test_num}.expected")
  if [ "$output" = "$expected" ]; then
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
# Tests 1-9: Help output for each command
# =============================================================================

run_test 1  "Main help output"              --help
run_test 2  "Devices command help"          devices --help
run_test 3  "Device command help"           device --help
run_test 4  "Deviceattributes command help" deviceattributes --help
run_test 5  "Procedures command help"       procedures --help
run_test 6  "Subnets command help"          subnets --help
run_test 7  "Riskmitigations command help"  riskmitigations --help
run_test 8  "Vulnerabilities command help"  vulnerabilities --help
run_test 9  "Threats command help"          threats --help

# =============================================================================
# Test 10: Missing config — always runs without Doppler/env file so that
# the credential-checking logic itself is what's being tested.
# =============================================================================

echo "Test 10: Missing config error"
exit_code=0
output=$(CYLERA_BASE_URL="" CYLERA_USERNAME="" CYLERA_PASSWORD="" uv run --no-env-file cylera devices 2>&1) || exit_code=$?
# Strip the dynamic "Current directory:" line before comparing
filtered=$(echo "$output" | grep -v "^Current directory:")
expected=$(cat "test10.expected" | grep -v "^exit:")
expected_exit=$(cat "test10.expected" | grep "^exit:" | cut -d: -f2)
if [ "$filtered" = "$expected" ] && [ "$exit_code" = "$expected_exit" ]; then
  echo "PASS: Missing config error"
else
  echo "FAIL: Missing config error"
  echo "Expected exit code $expected_exit, got: $exit_code"
  echo "Expected output (sans Current directory line):"
  echo "$expected"
  echo "Got (sans Current directory line):"
  echo "$filtered"
  exit 1
fi
echo

# =============================================================================
# Tests 11-17: Live API queries against the demo environment
# =============================================================================

run_api_test 11 "Devices default page"                            devices --page-size 1
run_api_test 12 "Devices filtered by vendor (Philips)"           devices --page-size 1 --vendor Philips
run_api_test 13 "Devices filtered by class and IP prefix"        devices --page-size 1 --class Medical --ip-address 10.30
run_api_test 14 "Vulnerabilities default page"                   vulnerabilities --page-size 1
run_api_test 15 "Threats default page"                           threats --page-size 1
run_api_test 16 "Subnets list"                                   subnets
run_api_test 17 "Vulnerabilities filtered by severity (MEDIUM)"  vulnerabilities --page-size 1 --severity MEDIUM

echo "=== All tests passed! ==="
