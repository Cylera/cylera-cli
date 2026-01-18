#!/bin/bash
#
# Test script for cylera.py CLI
# Assumes the CLI has been initialized via 'cy init'
#

set -e

SCRIPT_DIR="."
CY="uv run ${SCRIPT_DIR}/cylera.py"

echo "========================================"
echo "Testing Cylera CLI (cylera.py)"
echo "========================================"
echo

# Test help
echo ">>> cy --help"
$CY --help
echo
echo "----------------------------------------"
echo

# Test devices (list devices with pagination)
echo ">>> cy devices --page-size 2"
$CY devices --page-size 2
echo
echo "----------------------------------------"
echo

# Test devices with filters
echo ">>> cy devices --class Medical --page-size 2"
$CY devices --class Medical --page-size 2
echo
echo "----------------------------------------"
echo

# Test devices with vendor filter
echo ">>> cy devices --vendor Philips --page-size 2"
$CY devices --vendor Philips --page-size 2
echo
echo "----------------------------------------"
echo

# Get a device MAC from the previous results for further testing
echo ">>> Extracting a MAC address for further tests..."
MAC_ADDRESS=$($CY devices --page-size 1 | grep -o '"mac_address": "[^"]*"' | head -1 | cut -d'"' -f4)
echo "Using MAC address: $MAC_ADDRESS"
echo
echo "----------------------------------------"
echo

# Test device (single device)
echo ">>> cy device $MAC_ADDRESS"
$CY device "$MAC_ADDRESS"
echo
echo "----------------------------------------"
echo

# Test deviceattributes
echo ">>> cy deviceattributes $MAC_ADDRESS"
$CY deviceattributes "$MAC_ADDRESS"
echo
echo "----------------------------------------"
echo

# Test procedures
echo ">>> cy procedures --page-size 2"
$CY procedures --page-size 2
echo
echo "----------------------------------------"
echo

# Test subnets
echo ">>> cy subnets --page-size 2"
$CY subnets --page-size 2
echo
echo "----------------------------------------"
echo

# Test vulnerabilities
echo ">>> cy vulnerabilities --page-size 2"
$CY vulnerabilities --page-size 2
echo
echo "----------------------------------------"
echo

# Test vulnerabilities with filters
echo ">>> cy vulnerabilities --severity CRITICAL --page-size 2"
$CY vulnerabilities --severity CRITICAL --page-size 2
echo
echo "----------------------------------------"
echo

# Test vulnerabilities with status filter
echo ">>> cy vulnerabilities --status OPEN --page-size 2"
$CY vulnerabilities --status OPEN --page-size 2
echo
echo "----------------------------------------"
echo

# Test threats
echo ">>> cy threats --page-size 2"
$CY threats --page-size 2
echo
echo "----------------------------------------"
echo

# Test threats with filters
echo ">>> cy threats --severity HIGH --page-size 2"
$CY threats --severity HIGH --page-size 2
echo
echo "----------------------------------------"
echo

# Test riskmitigations (need a vulnerability name)
echo ">>> Extracting a vulnerability name for mitigations test..."
VULN_NAME=$($CY vulnerabilities --page-size 1 | grep -o '"vulnerability_name": "[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$VULN_NAME" ]; then
  echo "Using vulnerability: $VULN_NAME"
  echo
  echo ">>> cy riskmitigations '$VULN_NAME'"
  $CY riskmitigations "$VULN_NAME"
else
  echo "No vulnerabilities found, skipping riskmitigations test"
fi
echo
echo "----------------------------------------"
echo

echo "========================================"
echo "All tests completed successfully!"
echo "========================================"

exit 0
