---
name: debian-debci-monitor
version: 1
summary: Monitor Debian package autopkgtest CI status via debci
category: debian
description: Use when tracking ci.debian.net autopkgtest results for packages with Testsuite: autopkgtest. Uses debci REST API.
author: Vasudev Kamath
license: GPL-3.0
metadata:
  hermes:
    tags: [debian, debci, autopkgtest, ci, autopkgtest]
    related_skills: [debian-acceptance-monitor, debian-buildd-monitor, debci-api]
---

# Debian debci Autopkgtest CI Monitor

Monitor autopkgtest CI results on ci.debian.net (debci) for packages with `Testsuite: autopkgtest`.

## When to Use

- After package builds complete on buildd (use debian-buildd-monitor first)
- Track autopkgtest results across architectures
- Only works for packages with `Testsuite: autopkgtest` in debian/control
- Monitor both dh-golang-autopkgtest and custom test suites

## Prerequisites

- debci API key in gnome-keyring (`ci-debian-net` service)
- `debci-api` skill for helper script
- Package must have `Testsuite: autopkgtest` in debian/control

## Quick Reference

| Tool | Purpose |
|------|---------|
| `debci.sh` | debci API wrapper (from debci-api skill) |
| `terminal` | Run debci.sh pkg-results |
| `read_file` | Parse JSON responses |

## Monitoring Script

`scripts/monitor-debci.sh` — Check debci autopkgtest CI status.

**Usage:**
```bash
./monitor-debci.sh <package> [version]
```

**Exit codes:**
- 0 = all tests passed or pending (no failures)
- 1 = at least one test failed
- 2 = error (no API key, package not in debci, etc.)

**Example output:**
```
=== debci CI Status for smartctl-exporter ===
ARCH         STATUS       VERSION     RUN_ID
amd64        ✅ PASS      0.15.0-2    76241107
arm64        ⏳ QUEUED    0.15.0-2    -
...

Summary: 3 passed, 0 failed, 4 pending
```

## Cron Job Configuration

```yaml
schedule: "1h"
skills: ["debian-debci-monitor", "debci-api"]
script: "monitor-debci.sh"
continuity: true
deliver: "origin"
```

## Procedure

1. Verify package has `Testsuite: autopkgtest` in debian/control
2. Run `debci.sh pkg-results <package>` via debci-api
3. Parse output for target version across architectures
4. Report: PASS/FAIL/QUEUED/PENDING/NOT SCHEDULED
5. For failures, fetch details via debci API

## Test Types Monitored

- `dh-golang-autopkgtest` — Go package unit tests
- Custom suites (e.g., `smartctl-exporter-smoke`) — binary smoke tests
- Any test defined in `debian/tests/control`

## Pitfalls

- **Requires `Testsuite: autopkgtest`** — without it, debci ignores package
- API key must be in gnome-keyring (`ci-debian-net`)
- debci is shared resource — don't oversubmit
- Results may lag buildd completion by hours

## debci.sh Usage Lessons

- **Functions not exported** — call as subprocess: `"$DEBCI_SCRIPT" pkg-results "$PACKAGE"`
- **Output format** — `pkg-results` prints: `suite arch version status run_id=X` (space-separated, no headers)
- **Empty results** — No output means package lacks `Testsuite: autopkgtest` or no runs exist
- **API key** — Retrieved from gnome-keyring (`ci-debian-net`) via `get_key()`; never log it

**Monitoring pattern**:
```bash
DEBCI_SCRIPT="/path/to/debci.sh"
RESULTS=$("$DEBCI_SCRIPT" pkg-results "$PACKAGE" 2>&1)
# Parse: awk '{print $1, $2, $3, $4, $5}' etc.
```

## References

- `debian-buildd-monitor` — prerequisite: builds must complete first
- `debci-api` — API interaction details
- https://ci.debian.net/