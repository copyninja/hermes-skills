---
title: debian-ci-failure-analysis
description: "Check Debian CI (debci) status and failing-run logs."
name: debian-ci-failure-analysis
version: 1.0.0
author: Debian CI maintainers
hermes:
  tags: [debian, ci, debci, autopkgtest, buildlog, package-testing]
  related_skills: [debci-api, autopkgtest]
---

## When to Use
- Check a package CI test status on ci.debian.net.
- Pull failing CI runs logs and analyse why they fail (build FTBFS, test failure, arch-specific).

## Workflow
1. Check status with `scripts/debci.sh`: `auth`, then `pkg-results <pkg>`.
2. Resolve the key via gnome-keyring (service ci-debian-net, user api-key); never print it.
3. Read per-arch status. A fail needs a log.
4. Do NOT chase CI test-log URLs; the Debian CI SPA does not expose per-job test logs.
5. Fetch build logs from buildd.debian.org with getbuildlog, then analyse.

## Pitfalls
- Login walls: /package/, /status/, job pages, /data/autopkgtest/... all 404/redirect-to-login without auth.
- getbuildlog fails on wget/network; retry with wget to the fetch.php URL.
- FTBFS in the build log = architecture bug. Build OK + test fail = testbed issue (missing kernel headers).

## references
- references/buildlog-analysis.md