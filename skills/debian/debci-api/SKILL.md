---
description: "Submit, check, and retry CI test runs on Debian's debci."
name: debci-api
author: Vasudev Kamath (@vkamath), Hermes Agent
license: GPL-3.0
hermes:
  tags: [debian, ci, debci, autopkgtest, package-testing]
  related_skills: [autopkgtest]
---

# debci-api Skill

Interact with Debian Continuous Integration (debci) via its REST API.

## When to Use

Use this skill when you need to:

- Submit a package to debci for CI testing (any package, suite, or architecture).
- Check the status/results of debci test runs.
- Retry failed tests or publish private tests.
- List packages registered in debci or check the reject list.
- Integrate debci API calls into monitoring or automation scripts.

Do NOT use for ad-hoc test results without API access (use the web UI or getbuildlog).

## Prerequisites

- `hermes-agent` skill tooling installed (terminal, read_file, search_files, web_extract, patch).
- `ci-debian-net` API key accessible via the keyring (`gnome-keyring` service `ci-debian-net`).
- `debian-autopkgtest` skill available for ATE workflow references.

## How to Run

- Retrieve the API key via command substitution (`KEY=$(get_key) `). Never print or log the key.
- Authenticate requests with the `Auth-Key` header.
- Use the helper script `scripts/debci.sh` for common operations.

## Quick Reference

| Tool | Purpose |
| --- | --- |
| `read_file` | Inspect debci API responses / JSON |
| `terminal` | Run `getbuildlog` |
| `search_files` | Find CI results by package/version |
| `patch` | Edit `debian/control` `Testsuite:` field |
| `terminal` | curl the debci REST API |

## Procedure

1. Identify target
   - Package name, suite, architecture. Only `unstable` is accepted as a suite.
   - Verify `Testsuite: autopkgtest` is in `debian/control`.

2. Retrieve the API key
   - `KEY=$(get_key)` (gnome-keyring service `ci-debian-net`).

3. Submit a test
   - `bash scripts/debci.sh submit unstable amd64 <pkg> 8`.

4. Check results
   - `bash scripts/debci.sh pkg-results <pkg>`.
   - Pagination: `since`/`until` from responses; use `until` from previous response.

5. Retry a failed test
   - `bash scripts/debci.sh retry <run_id>`.

6. Publish private tests
   - `bash scripts/debci.sh publish <run_ids>`.

## Pitfalls

- `@` in autopkgest Depends can cause badpkg in null runner — not relevant to monitoring.
- API key must be captured via command substitution; never echo or log `$KEY`.
- Submitting a package without ATE is a waste of debci slots — check `debian/control` first.
- CI is a shared resource; do not submit repeated test runs.

## Monitoring Package Acceptance and Build Status (Cron Pattern)

Use cron jobs to automatically track a package from upload through acceptance to build results across architectures.

**IMPORTANT**: debci only tracks packages with `Testsuite: autopkgtest` in debian/control. For packages without autopkgtest, use the authoritative archive/buildd tools below.

### 1. Acceptance Check (every 30m)

```bash
# Via cronjob_manage or systemd timer
rmadison <package>
# Or check tracker.debian.org/pkg/<package> for version in unstable
```

**Trigger**: Run after uploading a new version. Stop when version appears under 'unstable' suite in rmadison output.

### 2. Build Status Across Architectures (hourly, after acceptance)

```bash
# For each architecture:
getbuildlog <package> <version> <arch>
# Parse log for 'Status: successful' or 'Status: failed'
# Architectures: amd64, arm64, armhf, ppc64el, s390x, riscv64, loong64, mips64el
```

**Report**: Table of architecture → status (PASSED/FAILED/PENDING/NOT SCHEDULED). For failures, fetch build logs via `getbuildlog`.

### 3. autopkgtest CI Status (debci) — only if Testsuite: autopkgtest exists

```bash
bash ~/.hermes/skills/debian/debci-api/scripts/debci.sh pkg-results <package>
# Parse output for version <ver> across arches
```

### Cron Job Configuration

- Acceptance check: `schedule: "30m"`, `skills: ["debci-api"]`, `continuity: true`, `script: "monitor-acceptance.sh"`
- Build status check: `schedule: "1h"`, `skills: ["debci-api"]`, `continuity: true`, `script: "monitor-buildd.sh"`
- debci CI check: `schedule: "1h"`, `skills: ["debci-api"]`, `continuity: true`, `script: "monitor-debci.sh"`
- Deliver to `origin` (the chat that created the job)
- Use `continuity: true` so each run sees previous output and can dedupe

## Monitoring Scripts

The skill includes three reusable scripts in `scripts/`:

| Script | Purpose | Usage |
|--------|---------|-------|
| `monitor-acceptance.sh` | Check if package version accepted in unstable | `./monitor-acceptance.sh <package> <version>` |
| `monitor-buildd.sh` | Check buildd status across all arches | `./monitor-buildd.sh <package> <version>` |
| `monitor-debci.sh` | Check debci autopkgtest CI status | `./monitor-debci.sh <package> [version]` |

All scripts:
- Exit 0 on success, 1 on failure, 2 on error
- Output summary table to stdout
- Can be used directly in cron jobs via `script:` field
- Respect `continuity: true` for deduping

## Autopkgtest Testbed Setup

When running autopkgtest locally with `-- unshare`, set a writable temp directory to avoid permission issues with `~/.hermes/cache/scratch`:

```bash
export AUTOPKGTEST_TMP=/tmp/autopkgtest-tmp
TMPDIR=/tmp/autopkgtest-tmp
autopkgtest <package>.dsc -- unshare --release=unstable
```

## Verification

- `hermes skills check debci-api` — section-order audit passes.
- `hermes skills verify debci-api` runs the pytest suite (`tests/skills/test_debian_debci-api_skill.py`).

## References

- `debian-autopkgtest` skill for ATE workflow references.
- `scripts/debci.sh` helper script.
