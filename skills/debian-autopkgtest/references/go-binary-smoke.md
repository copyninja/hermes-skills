# Go Binary Smoke Test Pattern (Prometheus Exporters)

Reusable pattern for autopkgtest smoke tests on Go-based Prometheus exporters
(e.g., smartctl_exporter, node_exporter, etc.).

## Test Suite Structure

```
debian/
  control          # Testsuite: autopkgtest-pkg-go, autopkgtest
  tests/
    control        # Test definitions
    <binary>-smoke # Executable smoke test script
```

## debian/tests/control

```
Tests: <binary>-smoke
Restrictions: allow-stderr
Depends: @, <binary-package>, <runtime-deps>
Architecture: amd64 arm64 armhf ppc64el s390x riscv64 loong64
```

## Smoke Test Template (`debian/tests/<binary>-smoke`)

```bash
#!/bin/sh
set -e

export AUTOPKGTEST_TMP=${AUTOPKGTEST_TMP:-/tmp/adt-<binary>-smoke}
mkdir -p "$AUTOPKGTEST_TMP"

failed=0

check() {
    if [ $1 -eq 0 ]; then
        echo "  PASS: $2"
    else
        echo "  FAIL: $2 (exit $1)"
        failed=$((failed + 1))
    fi
}

echo "<binary> autopkgtest — smoke test"
echo "========================================="

# 1. Binary exists
BIN="/usr/bin/<binary>"
[ -x "$BIN" ] || BIN="/usr/sbin/<binary>"
if [ -x "$BIN" ]; then
    echo "  PASS: binary found at $BIN"
else
    echo "  FAIL: <binary> binary not found"
    failed=$((failed + 1))
fi

# 2. --help and --version
"$BIN" --help >/dev/null 2>&1; check $? "--help"
"$BIN" --version >/dev/null 2>&1; check $? "--version"

# 3. Flag parsing (start background, sleep, kill)
"$BIN" --web.listen-address=:0 --<device-flag>='^/dev/loop' >/dev/null 2>&1 &
PID=$!
sleep 1
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null || true
# kill returns 143 (SIGTERM) which is expected
if [ $? -eq 0 ] || [ $? -eq 143 ]; then
    echo "  PASS: flag parsing"
else
    echo "  FAIL: flag parsing"
    failed=$((failed + 1))
fi

# 4. Systemd unit (check both paths)
SYSTEMD_UNIT=""
for path in /lib/systemd/system/<service>.service /usr/lib/systemd/system/<service>.service; do
    if [ -f "$path" ]; then
        SYSTEMD_UNIT="$path"
        break
    fi
done
if [ -n "$SYSTEMD_UNIT" ]; then
    systemd-analyze verify "$SYSTEMD_UNIT" >/dev/null 2>&1
    check $? "systemd unit verification ($SYSTEMD_UNIT)"
else
    echo "  SKIP: systemd unit not found"
fi

# 5. Device/service dry-run (if loop devices available)
if ls /dev/loop* >/dev/null 2>&1; then
    LOOP_DEV=$(ls /dev/loop* | head -1)
    "$BIN" --<device-flag>="$LOOP_DEV" --web.listen-address=:0 --<interval-flag>=1s >/dev/null 2>&1 &
    PID=$!
    sleep 2
    kill $PID 2>/dev/null || true
    wait $PID 2>/dev/null || true
    if [ $? -eq 0 ] || [ $? -eq 143 ]; then
        echo "  PASS: device scan on $LOOP_DEV"
    else
        echo "  FAIL: device scan on $LOOP_DEV"
        failed=$((failed + 1))
    fi
else
    echo "  SKIP: no loop devices for device scan test"
fi

echo "========================================="
if [ $failed -gt 0 ]; then
    echo "FAILED: $failed test(s)"
    exit 1
else
    echo "ALL SMOKE TESTS PASSED"
fi
```

## Key Patterns

### Kill/Wait with set -e
```bash
kill $PID 2>/dev/null || true
wait $PID 2>/dev/null || true
# Exit 143 (SIGTERM) is expected — treat 0 or 143 as PASS
if [ $? -eq 0 ] || [ $? -eq 143 ]; then
    # PASS
fi
```

### Systemd Unit Path
Check both:
- `/lib/systemd/system/<service>.service`
- `/usr/lib/systemd/system/<service>.service`

### Loop Device Dry-Run
```bash
if ls /dev/loop* >/dev/null 2>&1; then
    LOOP_DEV=$(ls /dev/loop* | head -1)
    "$BIN" --device="$LOOP_DEV" ...
else
    echo "  SKIP: no loop devices"
fi
```

## Common Flags for Prometheus Exporters

| Exporter | Binary | Device Flag | Interval Flag | Service Name |
|----------|--------|-------------|---------------|--------------|
| smartctl_exporter | smartctl_exporter | `--smartctl.device` | `--smartctl.interval` | prometheus-smartctl-exporter |
| node_exporter | node_exporter | N/A | N/A | prometheus-node-exporter |

## Test Dependencies

```
Depends: @, <binary-package>, <runtime-deps>, linux-libc-dev
```
- `linux-libc-dev` for kernel UAPI headers (parity with bpfcc pattern)
- Runtime deps: e.g., `smartmontools` for smartctl_exporter

## Local Test Command

```bash
export AUTOPKGTEST_TMP=/tmp/autopkgtest-tmp
TMPDIR=/tmp/autopkgtest-tmp
autopkgtest ../<pkg>_<ver>.dsc -- unshare --release=unstable
```

## Lintian Note

`unnecessary-testsuite-autopkgtest-field` warns when `Testsuite: autopkgtest-pkg-go, autopkgtest`. This is a **false positive** — keep both:
- `autopkgtest-pkg-go` → runs Go unit tests (`dh_golang_autopkgtest`)
- `autopkgtest` → runs custom binary smoke tests

## Architecture List

```
Architecture: amd64 arm64 armhf ppc64el s390x riscv64 loong64
```
Matches Debian's release architectures for Go packages.
