---
name: debian-package-monitoring
description: Monitor Debian packages via cron for buildd and CI changes.
version: 0.1.0
author: Vasudev Kamath, Hermes Agent
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
- Set up version-pinned monitors for unstable/experimental.
- Replace manual `getbuildlog` checks with automated diff-based alerts.

Do NOT use for one-off checks — use direct `web_search`/`web_extract` or `getbuildlog` instead.

## Procedure

1. Identify target
   - Package name, suite, version, architectures.
   - For bpfcc, source package is `bpfcc`; binary `bpfcc-tools` belongs to same source.

2. Create a deterministic snapshot script under `~/.hermes/scripts/`
   - Output must be deterministic — no timestamps, no random order.
   - Fields are pipe-separated key:value pairs, one per line or in one line.
   - Example fields: `ft-version`, `buildd-amd64`, `buildd-arm64`, `debci`, `debci-ttl`.
   - Script should fetch:
     - Pool version from `ftp.debian.org/debian/dists/<suite>/main/binary-amd64/Packages.gz`
     - Buildd status page `https://buildd.debian.org/status/package.php?p=<pkg>&suite=<suite>&arch=<arch>`
     - ci.debian.net API for latest result for package+suite+version using keyring key `ci-debian-net` / `api-key`.

3. Create/update cron job
   - Use `cronjob_manage` action `create`/`update`.
   - Set `script` to the snapshot script name (relative to `~/.hermes/scripts/`).
   - Prompt must be self-contained: describe fields, version filter, change detection rules, and output format.
   - Deliver to `telegram:734769556` or user's home channel.
   - Schedule: 30m for CI/build status, 120m for build logs.
   - **Skill references must name a real loadable skill, not a category directory.** Cron resolves skill names through the skill loader; a category directory without a SKILL.md (e.g. `web`) is not a skill and causes the scheduler to skip the job. Pass `skills: []` when the job only needs built-in tools (web_extract, web_search, browser), or pass an installed skill name when that skill is genuinely required.

4. Version pinning
   - Prompt must explicitly track only the target version e.g. `0.37.0+ds-3`.
   - Report change only when ft-version becomes the target, changes away, or debci status changes for that version.
   - If nothing changed, output: "No change: <pkg> <version> <suite> status unchanged."

5. Build log checker
   - Separate job, no skill needed — uses built-in web tooling.
   - Query buildd status page, find buildlog link containing target version.
   - Report version + status + 1-2 line error snippet if failed.

6. ci.debian.net monitor
   - Separate job every 30m.
   - API key from keyring, never printed.
   - Fetch `/api/v1/test?since=<until>` and filter package+suite+version.
   - Track `status`, `run_id`, `updated_at`. Report only changes.

## Pitfalls

- Binary vs source package name mismatch — always resolve to source package before querying FTP, BTS, or buildd.
- Cron jobs are paused by default when created via previous runs; after changing script/prompt, resume with `cronjob_manage` action `resume`.
- Script output with timestamps makes every tick look changed — keep output deterministic.
- Suite acceptance: ci.debian.net only accepts `unstable` for submissions; querying is fine for any suite, but submissions will be rejected for experimental.
- API key must be captured via command substitution; never echo or log `$KEY`.
- `@` in autopkgtest Depends can cause badpkg in null runner — not relevant to monitoring but often confused with buildd.

## References

- `references/script-template.sh` — minimal snapshot script template.
