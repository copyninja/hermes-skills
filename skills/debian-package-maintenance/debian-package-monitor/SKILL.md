---
name: debian-package-monitor
description: Monitor Debian package versions, buildd and CI status.
version: 0.1.0
author: Vasudev Kamath, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [debian, packages, monitoring, cronjobs, buildd]
    related_skills: []
---

# Debian Package Monitor Skill

Reusable workflow to monitor Debian package version progression across suites, buildd status, and ci.debian.net.

## When to Use
- Monitor a specific package version in unstable, testing, or experimental.
- Alert on acceptance into archive, buildd status changes, or CI status changes.
- Create recurring cron jobs that poll package tracker, FTP pool, buildd and CI API without manual checking.

Don't use for: one-off package queries.

## Prerequisites
- `cronjob_manage` available.
- Package name, target version, suite(s) and architecture(s) known.
- For ci.debian.net: API key stored in keyring service `ci-debian-net` user `api-key`.
- Optional monitor scripts in `~/.hermes/scripts/` for snapshot generation.

## How to Run
Create cron jobs with `cronjob_manage` action='create' using a script for deterministic snapshot and a prompt for change detection.

## Procedure
1. Choose monitor type:
   - FTP pool version check
   - Buildd status check
   - CI status check
2. Create or reuse a snapshot script that outputs pipe-separated key:value fields, no timestamps.
3. Create cron job:
   - name: `<pkg> <version> <suite> monitor`
   - schedule: `every 30m` or `every 2h`
   - script: path to snapshot script relative to `~/.hermes/scripts/`
   - prompt: instruct agent to report only meaningful changes vs previous tick.
   - deliver: `telegram:<chat_id>`
4. Resume job after creation with `cronjob_manage` action='resume' if created paused.
5. Verify by inspecting jobs with `cronjob_manage` action='list'.

## Quick Reference
- Create monitor: cronjob_manage action='create' schedule='every 30m' script='<name>.sh' prompt='...'
- Update version: cronjob_manage action='update' job_id='...' prompt='...' script='...'
- Pause/resume: cronjob_manage action='pause'/'resume' job_id='...'

## Pitfalls
- Snapshot script must be deterministic — no timestamps, otherwise every tick looks changed.
- CI API rate limits; avoid sub-30m intervals for CI checks.
- Keyring access fails silently in scripts; test script locally first.

## Verification
- Job appears in `cronjob_manage` list with enabled=true, state=scheduled.
- Next run time is in the future.
- First tick runs and delivers a baseline message.
