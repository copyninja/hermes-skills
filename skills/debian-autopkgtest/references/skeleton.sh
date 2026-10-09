#!/bin/sh
# Generic autopkgtest smoke test skeleton
# Customize for your package: add runtime dep checks, test commands, etc.
set -e

export AUTOPKGTEST_TMP=${AUTOPKGTEST_TMP:-/tmp/adt-smoke}
mkdir -p "$AUTOPKGTEST_TMP"

# --- Runtime prerequisite checks (customize per package) ---
# Check for files that must exist at test time.
# Find what package provides a missing file: dpkg -S /path/to/file
#
# Example: kernel UAPI headers for libbpf-based packages
# if [ ! -f /usr/include/linux/bpf.h ]; then
#     echo "FAIL: /usr/include/linux/bpf.h not found — install linux-libc-dev"
#     exit 1
# fi
#
# Note: linux-libc-dev provides UAPI headers (/usr/include/linux/*.h).
# For packages needing full kernel build tree at runtime (e.g. bcc/Clang),
# use autopkgtest unshare runner with bind mounts instead:
#   autopkgtest ... -- unshare -r unstable -b /lib/modules /lib/modules -b /usr/src /usr/src
# Never add linux-headers-$(uname -r) to Depends: — it's kernel-release-specific.

# --- Test commands (customize per package) ---
# Example: import a Python module
# python3 -c "import <module>; print('OK')"

# Example: check a binary exists and --help works
# if [ -x /usr/sbin/<binary> ]; then
#     /usr/sbin/<binary> --help > /dev/null 2>&1
# else
#     echo "FAIL: /usr/sbin/<binary> not found"
#     exit 1
# fi

# Example: check a library .so exists
# if [ -f /usr/lib/*/lib<name>.so ]; then
#     echo "PASS: lib<name>.so found"
# else
#     echo "FAIL: lib<name>.so not found"
#     exit 1
# fi

echo "smoke: PASS"

# Note on @ in Depends: in null runner with -B (no-built-binaries),
# @ expands to ALL binary packages. If any is not installed on host,
# test fails with badpkg. Use explicit names if you only need some.
