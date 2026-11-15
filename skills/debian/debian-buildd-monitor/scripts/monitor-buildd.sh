#!/usr/bin/env bash
# monitor-buildd.sh — Check buildd status across all architectures for a package version
# Usage: ./monitor-buildd.sh <package> <version>
# Returns: 0 on success, 1 if any arch failed, 2 on error

set -euo pipefail

PACKAGE="${1:-}"
VERSION="${2:-}"

if [ -z "$PACKAGE" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <package> <version>" >&2
    exit 2
fi

ARCHES="amd64 arm64 armhf ppc64el s390x riscv64 loong64 i386"
FAILED=0
PENDING=0
PASSED=0

echo "=== Buildd Status for $PACKAGE $VERSION ==="
printf "%-12s %-15s %s\n" "ARCH" "STATUS" "DETAILS"

for arch in $ARCHES; do
    echo "  Checking $arch..." >&2
    # getbuildlog saves to current directory, run from /tmp
    if timeout 60 bash -c "cd /tmp && getbuildlog '$PACKAGE' '$VERSION' '$arch'" >/dev/null 2>&1; then
        # Find the downloaded log file in /tmp
        LOGFILE=$(ls -t /tmp/${PACKAGE}_${VERSION}_${arch}.log* 2>/dev/null | head -1)
        if [ -n "$LOGFILE" ] && [ -s "$LOGFILE" ]; then
            if grep -q "Status: successful" "$LOGFILE"; then
                FINISHED=$(grep "Finished at" "$LOGFILE" | head -1 | sed 's/.*Finished at //')
                printf "%-12s %-15s %s\n" "$arch" "✅ PASSED" "$FINISHED"
                PASSED=$((PASSED + 1))
            elif grep -q "Status: failed" "$LOGFILE"; then
                ERROR=$(grep -A3 "Status: failed" "$LOGFILE" | head -4 | tr '\n' '; ')
                printf "%-12s %-15s %s\n" "$arch" "❌ FAILED" "$ERROR"
                FAILED=$((FAILED + 1))
            else
                printf "%-12s %-15s %s\n" "$arch" "⏳ UNKNOWN" "Log exists but no status"
            fi
        else
            echo "  $arch: log file empty or not found" >&2
        fi
    else
        # Check if it's Needs-Build or not scheduled
        if rmadison "$PACKAGE" 2>/dev/null | grep -q "$VERSION.*buildd-unstable"; then
            printf "%-12s %-15s %s\n" "$arch" "⏳ PENDING" "Needs-Build or not scheduled"
            PENDING=$((PENDING + 1))
        else
            printf "%-12s %-15s %s\n" "$arch" "❓ N/A" "Not in build queue"
        fi
    fi
done

echo ""
echo "Summary: $PASSED passed, $FAILED failed, $PENDING pending"

if [ $FAILED -gt 0 ]; then
    exit 1
elif [ $PENDING -gt 0 ]; then
    exit 0  # Not an error, just waiting
else
    exit 0
fi