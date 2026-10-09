#!/usr/bin/env bash
# gbp-check-upstream.sh - diagnose gbp upstream divergence for a Debian package.
# Usage: gbp-check-upstream.sh <pkg>
# Prints: local upstream count, remote upstream count, divergence summary.
set -euo pipefail

PKG="${1:?usage: gbp-check-upstream.sh <pkg>}"

cd "$(git root 2>/dev/null || pwd)" || exit 1

local_count=$(git rev-list --count upstream 2>/dev/null || echo 0)
remote_count=$(git rev-list --count origin/upstream 2>/dev/null || echo 0)
merge_base=$(git merge-base upstream origin/upstream 2>/dev/null || echo "")

echo "pkg=${PKG}"
echo "local_upstream_commits=${local_count}"
echo "origin_upstream_commits=${remote_count}"
echo "merge_base=${merge_base:-<none>}"

if [ "${local_count}" -gt 0 ] && [ "${remote_count}" -gt 0 ]; then
  left=$(git rev-list --count "${merge_base}..upstream" 2>/dev/null || echo 0)
  right=$(git rev-list --count "${merge_base}..origin/upstream" 2>/dev/null || echo 0)
  echo "local_only=${left}"
  echo "remote_only=${right}"
fi
