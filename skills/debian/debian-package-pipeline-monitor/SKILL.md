---
name: debian-package-pipeline-monitor
version: 1
summary: Complete Debian package monitoring pipeline: acceptance → buildd → debci CI
category: debian
description: Use when tracking a package from upload through acceptance, buildd status, and debci CI. Orchestrates acceptance, buildd, and debci monitors.
author: Vasudev Kamath
license: GPL-3.0
metadata:
  hermes:
    tags: [debian, package, pipeline, acceptance, buildd, debci, ci]
    related_skills: [debian-acceptance-monitor, debian-buildd-monitor, debian-debci-monitor, debci-api]
---

# Debian Package Pipeline Monitor

Complete monitoring pipeline: **Acceptance → Buildd → debci CI**

Orchestrates the three monitoring stages for a Debian package from upload to CI completion.

## When to Use

- After uploading a new package version
- Track full lifecycle: archive acceptance → buildd builds → autopkgtest CI
- Single cron job for end-to-end visibility
- Automatically transitions between stages

## Pipeline Stages

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. ACCEPTANCE  │───▶│    2. BUILDD    │───▶│  3. DEBCI CI    │
│  (rmadison)     │    │  (getbuildlog)  │    │  (debci API)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
   unstable suite       all arches              autopkgtest
   tracker.debian.org   buildd.debian.org       ci.debian.net
```

## Prerequisites

- `rmadison`, `getbuildlog` (devscripts)
- debci API key in gnome-keyring (`ci-debian-net`)
- Package must have `Testsuite: autopkgtest` for stage 3

## Quick Reference

| Stage | Skill | Tool | Target |
|-------|-------|------|--------|
| 1. Acceptance | debian-acceptance-monitor | rmadison | unstable suite |
| 2. Buildd | debian-buildd-monitor | getbuildlog | all arches |
| 3. debci | debian-debci-monitor | debci API | autopkgtest |

## Monitoring Script

`scripts/monitor-pipeline.sh` — Runs all three stages sequentially.

**Usage:**
```bash
./monitor-pipeline.sh <package> <version>
```

**Exit codes:**
- 0 = pipeline complete (all stages passed or pending)
- 1 = stage failed (build failure or test failure)
- 2 = error

**Example output:**
```
=== DEBIAN PACKAGE PIPELINE: smartctl-exporter 0.15.0-2 ===

[STAGE 1] ACCEPTANCE CHECK
────────────────────────────
✅ ACCEPTED: 0.15.0-2 in unstable, buildd-unstable

[STAGE 2] BUILDD STATUS
────────────────────────────
ARCH         STATUS         DETAILS
amd64        ✅ PASSED      2026-11-14T15:28:13Z
arm64        ✅ PASSED      2026-11-14T15:27:25Z
...
riscv64      ⏳ PENDING     Needs-Build
Summary: 7 passed, 0 failed, 1 pending

[STAGE 3] DEBCI CI (if Testsuite: autopkgtest)
────────────────────────────
ARCH         STATUS       VERSION     RUN_ID
amd64        ✅ PASS      0.15.0-2    76241107
...
```

## Cron Job Configuration

```yaml
schedule: "30m"
skills: ["debian-package-pipeline-monitor"]
script: "monitor-pipeline.sh"
continuity: true
deliver: "origin"
```

## Procedure

1. **Stage 1 — Acceptance**: Run `rmadison <package>`, check for version in `unstable` suite
   - If not accepted: report and stop (retry next cycle)
   - If accepted: proceed to Stage 2

2. **Stage 2 — Buildd**: Run `getbuildlog` for all release architectures
   - Parse `Status: successful` / `Status: failed` / `Needs-Build`
   - If any failed: report failure, continue to Stage 3
   - If all passed or pending: proceed to Stage 3

3. **Stage 3 — debci CI** (only if `Testsuite: autopkgtest` in control):
   - Run `debci.sh pkg-results <package>` via debci-api
   - Parse PASS/FAIL/QUEUED across arches
   - Report CI status

## Pipeline Logic

| Current Stage | Next Action |
|---------------|-------------|
| Not accepted | Retry acceptance next cycle |
| Accepted, builds pending | Retry buildd next cycle |
| Builds complete, CI pending | Retry debci next cycle |
| All complete | Report success, continue monitoring for regressions |

## Cron Job Configuration

```yaml
schedule: "30m"
skills: ["debian-package-pipeline-monitor"]
script: "monitor-pipeline.sh"
continuity: true
deliver: "origin"
```

## Monitoring Script

`scripts/monitor-pipeline.sh` — Complete pipeline runner.

**Usage:**
```bash
./monitor-pipeline.sh <package> <version>
```

## Sub-skills (Loaded Automatically)

| Skill | Purpose |
|-------|---------|
| `debian-acceptance-monitor` | Stage 1: rmadison/tracker acceptance |
| `debian-buildd-monitor` | Stage 2: getbuildlog build status |
| `debian-debci-monitor` | Stage 3: debci autopkgtest CI |
| `debci-api` | debci API helper (for stage 3) |

## Verification

- Each sub-skill has its own verification
- Pipeline integration test: run with a known package

## References

- `debian-acceptance-monitor` — stage 1 details
- `debian-buildd-monitor` — stage 2 details
- `debian-debci-monitor` — stage 3 details
- `debci-api` — debci API interaction