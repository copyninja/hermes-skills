---
title: debci-logs
description: "Fetch and summarize Debian CI (debci) autopkgest test logs from ci.debian.net."
name: debci-logs
version: 1.0.0
author: Vasudev Kamath
license: GPL-3.0
hermes:
  tags: [debian, ci, debci, autopkgtest, test-logs]
  related_skills: [debian/debci-api, autopkgtest]
---

# debci-logs

Fetch and summarize the autopkgest log for a Debian package's CI test run
from [ci.debian.net](https://ci.debian.net). This skill is backed by a
single deterministic script: `scripts/debci-fetch-log.py`.

> Debian CI runs bpfcc results under suite `unstable` in the `/api/v1/test`
> results endpoint, but the autopkgest **log files live under the run's actual
> suite** (currently `testing`/`unstable`). The `suite` argument below is the
> value returned by the results API, and it is what the script uses to build
> the unambiguous log URL. Do not guess — use the `suite` field from the
> results API for that run.

## When to Use

- You need to inspect *why* a package's autopkgtest run failed (which test,
  and the failure reason).
- You want raw test logs for the failing builds or test runs, especially to
  distinguish test-environment failures (e.g. old testbed / missing test
  deps) from real package build failures.
- You are reproducing a failure locally (e.g. by re-running the exact ATE
  with the same testbed).

## When NOT to Use

- The package has **no autopkgtest** in the target suite (`debian/control`
  has no `Testsuite: autopkgtest` for that suite). In that case there is no
  test log to fetch — see the `debian-autopkgtest` skill instead.
- You only need the *status*, not the log text. Then use the `debian/debci-api`
  skill (`debci.sh pkg-results`) instead.

## Result Code Contract (read by scripts / parents)

- Exit `0` = log downloaded and summarized successfully.
- Exit `1` = HTTP != 200, or decompression/contention error.
- Exit `2` = usage error (not enough arguments).

## Usage

`scripts/debci-fetch-log.py <suite> <arch> <run_id> [package]`

Example — summary for the s390x ds-4 failing run `76489375` (suite `unstable`):

```bash
scripts/debci-fetch-log.py unstable s390x 76489375
```

Example for the s390x ds-4 retry `76489475` (suite `testing`, from your sample URL):

```bash
scripts/debci-fetch-log.py testing s390x 76489475
```

Common packages: `bpfcc`; also `libbpf-tools`, `libbpfcc`, `bpfcc-tools`,
`bpfcc-introspection`, `bpfcc-lua` for multi-binary source packages (`b/`).

## Deterministic Behaviour

The script is deterministic:

- It **never guesses** the log-suite: the caller passes the suite observed in
  the results API (or the value from a known-good URL).
- It pins the log URL pattern and the `Auth-Key` retrieval (gnome-keyring,
  never printed to output).
- It returns a stable text summary (per-test `[PASS|FAIL|SKIP]` + totals), so
  it can be scripted, diffed, or rendered by a parent.

## Resolving the log suite for any run (debci-logs-for-run.py)

The log-suite is not always identical to the results-API `suite` field. For
bpfcc this instance reports `unstable` in the API but the logs live under
`testing` for the s390x retry run. Use the runner to resolve it:

`scripts/debci-logs-for-run.py <run_id> [package]`

Example — resolve the log-suite and print the summary for a run:

```bash
scripts/debci-logs-for-run.py 76489375
# -> suite=unstable, arch=s390x, version=0.37.0+ds-4, status=fail
#    [FAIL] libbpf-tools-smoke  badpkg
#    [FAIL] bpfcc-introspection-smoke  badpkg
```

If a run is not present in the results API (e.g. a `testing`-suite retry), pass
the suite explicitly to `debci-fetch-log.py` or re-run the test and poll for its
new run_id.

## Auth

The API key lives in gnome-keyring under `ci-debian-net`/`api-key`. Never
print it; the script reads it via command substitution, consistent with the
`debian/debci-api` skill.

## What the log contains (stable fields)

- Testbed release (`testbed release detected to be: ...`)
- Per-test results: `test <name>: PASS|FAIL|SKIP`
- Final: `ALL SMOKE TESTS PASSED` / `X tests passed, Y failed`
