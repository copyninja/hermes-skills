---
name: debian-package-monitoring
description: Monitor Debian packages via cron for buildd and CI status.
version: 0.1.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [debian, monitoring, cron, buildd, ci-debian-net, autopkgtest]
    related_skills: [debian-package-maintenance, debci-api]
---

# Debian Package Monitoring with Cron

## When to Use

- User wants recurring alerts for buildd status, CI results, or package acceptance for a specific Debian package version.
- Set up version-pinned monitors for unstable / experimental.
- Replace manual build-log checks with automated, diff-based alerts.

Do NOT use for one-off checks — use the `terminal` (getbuildlog) or `web_extract` directly instead.

## Prerequisites

- `hermes-agent` skill tooling installed (cronjob_manage, read_file, terminal, search_files, web_extract).
- `ci-debian-net` API key accessible via the keyring; never printed or logged.
- `~/.hermes/scripts/` writable for cron snapshot scripts.

## How to Run

- Create the snapshot script via `hermes scripts create`. Output must be deterministic (no timestamps, no random order); pipe-separated `key:value` on one or multiple lines.
- Install a cron job with `cronjob_manage action=create`. Set `script` to the snapshot script filename.
- Schedule: 30 min for CI/build status, 120 min for build logs.

## Quick Reference

| Tool | Purpose |
| --- | --- |
| `read_file` | Inspect snapshot scripts and Debian Packages.gz |
| `search_files` | Find buildd / ci links and version numbers |
| `terminal` | Run `getbuildlog` / `apt-file` or fetch URLs |
| `web_extract` | Pull README or wiki documentation |

## Procedure

1. Identify target
   - Package name, suite, version, architectures. For bpfcc the source package is `bpfcc`; the binary `bpfcc-tools` belongs to the same source.

2. Create a deterministic snapshot script under `~/.hermes/scripts/`
   - Output must be deterministic — no timestamps, no random order.
   - Fields are pipe-separated `key:value` pairs, one per line or in one line.
   - Example fields: `ft-version`, `buildd-amd64`, `buildd-arm64`, `debci`, `debci-ttl`.

3. Create / update the cron job
   - Use `cronjob_manage` action `create`.
   - Set `script` to the snapshot script name (relative to `~/.hermes/scripts/`).
   - Prompt must be self-contained: describe fields, version filter, change detection rules, output format.

4. Version pinning
   - Prompt must track only the target version (e.g. `0.37.0+ds-3`).
   - Report change only when ft-version becomes the target, changes away, or debci status changes for that version.

5. Build log checker
   - Separate job, no skill needed. Query buildd status page with `terminal` and `search_files`:
     1. `terminal`: run `getbuildlog` (Debian build log).
     2. `search_files`: locate the buildlog link for the target version on the buildd status page.
   - Report version + status + a 1-2 line error snippet if failed.

6. ci.debian.net monitor
   - Separate job every 30 minutes.
   - API key from keyring, never printed.
   - Fetch `/api/v1/test?since=<until>` and filter package+suite+version.
   - Track `status`, `run_id`, `updated_at`. Report only changes.

## Pitfalls

- Binary vs source package name mismatch — always resolve to source package before querying FTP, BTS, or buildd.
- Cron jobs are paused by default when created via previous runs; after changing script / prompt, resume with `cronjob_manage` action `resume`.
- Script output with timestamps makes every tick look changed — keep output deterministic.
- Suite acceptance: ci.debian.net only accepts `unstable` for submissions; querying is fine for any suite, but submissions will be rejected for experimental.
- API key must be captured via command substitution; never echo or log `$KEY`.
- `@` in autopkgest Depends can cause badpkg in null runner — not relevant to monitoring but often confused with buildd.

## Verification

- `hermes skills check <skill>` — section-order audit passes.
- `cronjob_manage action=show` lists the scheduled job.
- `hermes skills verify <skill>` runs the pytest suite (`tests/skills/test_debian_package_monitoring_skill.py`).

## References

- `references/script-template.sh` — minimal snapshot script template.
