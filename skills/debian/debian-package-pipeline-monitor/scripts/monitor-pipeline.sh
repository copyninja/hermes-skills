#!/usr/bin/env bash
# monitor-pipeline.sh — Complete Debian package monitoring pipeline
# Usage: ./monitor-pipeline.sh <package> <version>
# Runs: acceptance → buildd → debci CI

set -euo pipefail

PACKAGE="${1:-}"
VERSION="${2:-}"

if [ -z "$PACKAGE" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <package> <version>" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEBIAN_SKILLS_DIR="/home/vasudev/devel/hermes-skills/skills/debian"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== DEBIAN PACKAGE PIPELINE: $PACKAGE $VERSION ==="
echo ""

# ============================================================
# STAGE 1: ACCEPTANCE CHECK
# ============================================================
echo "[STAGE 1] ACCEPTANCE CHECK"
echo "────────────────────────────"

if "$DEBIAN_SKILLS_DIR/debian-acceptance-monitor/scripts/monitor-acceptance.sh" "$PACKAGE" "$VERSION"; then
    echo -e "${GREEN}✅ ACCEPTED${NC}: $PACKAGE $VERSION in unstable"
    echo ""
else
    echo -e "${YELLOW}⏳ NOT ACCEPTED${NC}: $PACKAGE $VERSION not yet in unstable"
    echo "Retry next cycle."
    exit 0  # Not an error, just not ready
fi

# ============================================================
# STAGE 2: BUILDD STATUS
# ============================================================
echo "[STAGE 2] BUILDD STATUS"
echo "────────────────────────────"

BUILDD_OUTPUT=$("$DEBIAN_SKILLS_DIR/debian-buildd-monitor/scripts/monitor-buildd.sh" "$PACKAGE" "$VERSION" 2>&1)
BUILDD_EXIT=$?
echo "$BUILDD_OUTPUT"
echo ""

if [ $BUILDD_EXIT -eq 1 ]; then
    echo -e "${RED}❌ BUILD FAILURES DETECTED${NC}"
    echo "Check build logs above. Continuing to CI check..."
elif [ $BUILDD_EXIT -eq 2 ]; then
    echo -e "${RED}ERROR${NC} in buildd check"
    exit 2
else
    echo -e "${GREEN}✅ BUILDS OK${NC} (passed or pending)"
fi

# ============================================================
# STAGE 3: DEBCI CI (only if Testsuite: autopkgtest)
# ============================================================
echo "[STAGE 3] DEBCI AUTOPKGTEST CI"
echo "────────────────────────────"

# Check if package has Testsuite: autopkgtest
if ! rmadison "$PACKAGE" 2>/dev/null | grep -q "$VERSION"; then
    echo "Package version not in archive, skipping CI check"
    exit 0
fi

# We need to check debian/control for Testsuite field
# For now, run debci check and handle "no results" gracefully
DEBCI_OUTPUT=$("$DEBIAN_SKILLS_DIR/debian-debci-monitor/scripts/monitor-debci.sh" "$PACKAGE" "$VERSION" 2>&1)
DEBCI_EXIT=$?
echo "$DEBCI_OUTPUT"
echo ""

if [ $DEBCI_EXIT -eq 1 ]; then
    echo -e "${RED}❌ CI TEST FAILURES${NC}"
elif [ $DEBCI_EXIT -eq 2 ]; then
    echo "No debci results (package may lack Testsuite: autopkgtest)"
elif [ $DEBCI_EXIT -eq 0 ]; then
    echo -e "${GREEN}✅ CI PASSED${NC} (or pending)"
fi

echo ""
echo "=== PIPELINE COMPLETE ==="
exit 0