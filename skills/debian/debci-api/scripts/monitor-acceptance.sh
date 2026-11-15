#!/usr/bin/env bash
# monitor-acceptance.sh — Check if a package version is accepted into Debian unstable
# Usage: ./monitor-acceptance.sh <package> <version>
# Returns: 0 if accepted, 1 if not, 2 on error

set -euo pipefail

PACKAGE="${1:-}"
VERSION="${2:-}"

if [ -z "$PACKAGE" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <package> <version>" >&2
    exit 2
fi

# Check via rmadison (authoritative archive query)
OUTPUT=$(rmadison "$PACKAGE" 2>&1) || {
    echo "ERROR: rmadison failed" >&2
    exit 2
}

if echo "$OUTPUT" | awk -v ver="$VERSION" '$2 == ver && $4 == "unstable" {found=1} END {exit !found}'; then
    echo "ACCEPTED: $PACKAGE $VERSION in unstable"
    echo "$OUTPUT" | grep "$VERSION"
    exit 0
else
    echo "NOT ACCEPTED: $PACKAGE $VERSION not in unstable"
    echo "$OUTPUT" | head -5
    exit 1
fi