#!/usr/bin/env bash
# monitor-debci.sh — Check debci autopkgtest CI status for a package
# Usage: ./monitor-debci.sh <package> [version]
# Returns: 0 on success, 1 if any test failed, 2 on error

set -euo pipefail

PACKAGE="${1:-}"
VERSION="${2:-}"

if [ -z "$PACKAGE" ]; then
    echo "Usage: $0 <package> [version]" >&2
    exit 2
fi

DEBIAN_SKILLS_DIR="/home/vasudev/devel/hermes-skills/skills/debian"
DEBCI_SCRIPT="$DEBIAN_SKILLS_DIR/debci-api/scripts/debci.sh"

# Get results by calling debci.sh as subprocess
RESULTS=$("$DEBCI_SCRIPT" pkg-results "$PACKAGE" 2>&1) || {
    echo "ERROR: debci query failed" >&2
    exit 2
}

if [ -z "$RESULTS" ]; then
    echo "No debci results for $PACKAGE (may lack Testsuite: autopkgtest)"
    exit 0
fi

echo "=== debci CI Status for $PACKAGE ==="
printf "%-12s %-10s %-20s %s\n" "ARCH" "STATUS" "VERSION" "RUN_ID"

FAILED=0
PASSED=0
PENDING=0

while IFS= read -r line; do
    if echo "$line" | grep -q "$PACKAGE"; then
        arch=$(echo "$line" | awk '{print $2}')
        status=$(echo "$line" | awk '{print $4}')
        ver=$(echo "$line" | awk '{print $3}')
        run_id=$(echo "$line" | sed -n 's/.*run_id=\([0-9]*\).*/\1/p')
        
        if [ -n "$VERSION" ] && [ "$ver" != "$VERSION" ]; then
            continue
        fi
        
        case "$status" in
            pass)   printf "%-12s %-10s %-20s %s\n" "$arch" "✅ PASS" "$ver" "$run_id"; PASSED=$((PASSED+1)) ;;
            fail)   printf "%-12s %-10s %-20s %s\n" "$arch" "❌ FAIL" "$ver" "$run_id"; FAILED=$((FAILED+1)) ;;
            *)      printf "%-12s %-10s %-20s %s\n" "$arch" "⏳ $status" "$ver" "$run_id"; PENDING=$((PENDING+1)) ;;
        esac
    fi
done <<< "$RESULTS"

echo ""
echo "Summary: $PASSED passed, $FAILED failed, $PENDING pending"

if [ $FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi