---
title: debian-ci-failure-analysis
description: "Diagnose failing debci CI runs and their build logs."
name: debian-ci-failure-analysis
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: GPL-3.0
hermes:
  tags: [debian, ci, debci, autopkgtest, buildlog, package-testing]
  related_skills: [debci-api, autopkgtest]
---

# debian-ci-failure-analysis Skill

Diagnose why a Debian CI (debci) test run fails, and pull the failing log for
analysis (build FTBFS, test failure, or arch-specific).

## When to Use

- A CI test run is failing and you need the failure reason.
- You want per-arch status, then the build log when a run fails.
- You need to distinguish FTBFS (build/system bug) from a test failure (testbed
  or package issue).

## Prerequisites

- debci/ci.debian.net access (ci-debian-net keyring service).
- Buildd.debian.org build logs (via the buildlog helper).
- The `debci.sh` helper script for authentication and `pkg-results`.

## How to Run

1. Authenticate and check status:
   `bash scripts/debci.sh auth` then `bash scripts/debci.sh pkg-results <pkg>`.
2. Read per-arch status. A failing run needs a log.
3. Fetch the build log from buildd.debian.org. Do not chase CI test-log URLs — the
   Debian CI SPA does not expose per-job test logs.
4. Analyse the log: FTBFS in the build log = architecture bug. Build OK + test
   fail = testbed issue (missing kernel headers).

## Quick Reference

- Authenticate: `bash scripts/debci.sh auth`.
- Check results: `bash scripts/debci.sh pkg-results <pkg>`.
- Build log: buildd.debian.org (fetch via the buildlog helper).

## Procedure

1. Check status.
2. Resolve failing per-arch.
3. Fetch the build log.
4. Analyse the cause.

## Pitfalls

- Login walls: the Debian CI SPA does not expose per-job test logs without auth.
- A buildlog helper fetches build logs reliably, avoiding the network failures
  of raw HTTP retrieval.
- FTBFS in the build log = architecture bug. Build OK + test fail = testbed
  issue (missing kernel headers).

## Verification

- Confirm the build log parses and the failure cause is identifiable.
