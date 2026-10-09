#!/usr/bin/env bash
# Snapshot script template — used by the debian-package-monitoring skill.
# Output must be deterministic: no timestamps, no random order; pipe-separated
# key:value pairs, one per line.

PKG="${1:?usage: snapshot <pkg> [suite]}"
SUITE="${2:-unstable}"

# Package identifier (source package). The binary may differ.
if [ -n "${SOURCE:-}" ]; then
  echo "src=${SOURCE}"
else
  echo "src=${PKG}"
fi

echo "suite=${SUITE}"
echo "arch=$(uname -m)"
echo "ft-version=<fetch from ftp.debian.org dists>"

# Buildd status (page-scrape; summarize only)
echo "buildd-amd64=<status>"
echo "buildd-arm64=<status>"

# CI recent result for pkg+suite+version
echo "debci=<status>"
echo "debci-ttl=<updated_at>"

# Deterministic: no timestamps, no random order.
