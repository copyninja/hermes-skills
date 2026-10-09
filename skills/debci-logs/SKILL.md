---
title: debci-logs
description: "Fetch Debian CI autopkgtest log output."
name: debci-logs
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: GPL-3.0
hermes:
  tags: [debian, ci, debci, autopkgtest, test-logs]
  related_skills: [debian/debci-api, autopkgtest]
---

# debci-logs Skill

Fetch and summarize the autopkgtest log for a Debian package's CI test run from
ci.debian.net using a single deterministic script: `scripts/debci-fetch-log.py`.

## When to Use

- Inspect why a package's autopkgtest run failed (which test, and the failure
  reason).
- Get raw test logs for failing builds or test runs, especially to distinguish
  test-environment failures from real package build failures.
- Reproduce a failure locally by re-running the exact ATE with the same testbed.

## Prerequisites

- Access to Debian CI results (ci.debian.net).
- The `debci-fetch-log.py` script in `scripts/`.
- gnome-keyring keyring `ci-debian-net`/`api-key` for the API key (never printed).

## How to Run

`scripts/debci-fetch-log.py <suite> <arch> <run_id> [package]`

Example, s390x ds-4 failing run `76489375` (suite `unstable`):

```bash
scripts/debci-fetch-log.py unstable s390x 76489375
```

Use the `suite` value returned by the results API; do not guess.

## Quick Reference

- Exit `0` = log downloaded and summarized successfully.
- Exit `1` = HTTP != 200, or decompression/contention error.
- Exit `2` = usage error (not enough arguments).
- Common packages: `bpfcc`; also `libbpf-tools`, `libbpfcc`, `bpfcc-tools`,
  `bpfcc-introspection`, `bpfcc-lua` for multi-binary source packages.

## Procedure

1. Fetch results via the results API for the package/run.
2. Use the `suite` field returned by the results API to build the log URL.
3. Call `scripts/debci-fetch-log.py` with that suite, the arch, and the run id.
4. Inspect the per-test summary.

## Pitfalls

- The package has no autopkgtest in the target suite (`debian/control` lacks
  `Testsuite: autopkgtest`) — there is no log to fetch. See `debian-autopkgtest`.
- You only need the status, not the log — use `debian/debci-api`
  (`debci.sh pkg-results`) instead.
- API key is captured via command substitution; never log it.

## Verification

- The script is deterministic: it does not guess the log-suite, it pins the log
  URL pattern and the `Auth-Key` retrieval (gnome-keyring, never printed), and it
  returns a stable text summary (`[PASS|FAIL|SKIP]` + totals).

## What the log contains (stable fields)

- Testbed release.
- Per-test results: `test <name>: PASS|FAIL|SKIP`.
- Final: `ALL SMOKE TESTS PASSED` / `X tests passed, Y failed`.
