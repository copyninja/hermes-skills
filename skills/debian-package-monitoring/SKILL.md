---
title: debian-package-monitoring
description: "Monitor Debian packages via cron for buildd and CI changes."
name: debian-package-monitoring
version: 0.1.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [debian, monitoring, cron, buildd, ci-debian-net, autopkgtest]
    related_skills: [debian-package-maintenance, debci-api]
---

# Debian Package Monitoring Skill

Monitor Debian packages via cron for buildd status, CI results, and package
acceptance for a specific Debian package version. Set up version-pinned monitors
for unstable/experimental, and replace manual build-log checks with
diff-based alerts.

## When to Use

- You want recurring alerts for buildd status, CI results, or package acceptance
  for a specific Debian package version.
- You want to set up version-pinned monitors for unstable/experimental.
- You want to replace manual build-log checks with automated diff-based alerts.

## Prerequisites

- cron availability on the host.
- A snapshot script under `~/.hermes/scripts/` (deterministic — no timestamps,
  no random order).
- Keyring service `ci-debian-net` / `api-key` for the CI API.
- The `cronjob_manage` tool for creating and resuming jobs.

## How to Run

1. Identify target — package name, suite, version, architectures.
2. Create a deterministic snapshot script under `~/.hermes/scripts/`; output must
   be deterministic with pipe-separated `key:value` fields.
3. Create or update a cron job with `cronjob_manage`; set `script` to the
   snapshot script name (relative to `~/.hermes/scripts/`).
4. Deliver the job to the home channel or user's Telegram.

## Quick Reference

- Snapshot script fields: `ft-version`, `buildd-amd64`, `buildd-arm64`,
  `debci`, `debci-ttl`.
- Pool version source: `ftp.debian.org/debian/dists/<suite>/main/binary-amd64/Packages.gz`.
- Buildd status: `https://buildd.debian.org/status/package.php?p=<pkg>&suite=<suite>&arch=<arch>`.
- ci.debian.net API: `/api/v1/test?since=<until>` (latest result for package + suite
  + version).
- Schedule: 30m for CI/build status; 120m for build logs.

## Procedure

1. Identify target — package name, suite, version, architectures.
2. Create a deterministic snapshot script under `~/.hermes/scripts/` (no timestamps,
   no random order).
3. Create or update a cron job with `cronjob_manage`.
4. Version-pin the monitor to the target version; report change only when
   `ft-version` becomes the target, changes away, or debci status changes.
5. Run a separate build-log checker job (no skill needed) that reports the
   version, status, and a 1-2 line error snippet when failed.
6. Run a separate `ci.debian.net` monitor every 30 minutes; track status, run_id,
   updated_at, and report only changes.

## Pitfalls

- Binary vs source package name mismatch — always resolve to source package
  before querying FTP, BTS, or buildd.
- Cron jobs are paused by default; resume with `cronjob_manage` after changing
  the script or prompt.
- Deterministic output only — timestamps make every tick look changed.
- Suite acceptance: ci.debian.net accepts only `unstable` for submissions.
- API key must be captured via command substitution; never echo or log it.
- Resolve to the source package before querying FTP, BTS, or buildd.

## Verification

- Check a new package version appears in the snapshot with `ft-version` set.
- Confirm the CI monitor reports only when status changes.
- Confirm the build-log checker reports version, status, and an error snippet.
