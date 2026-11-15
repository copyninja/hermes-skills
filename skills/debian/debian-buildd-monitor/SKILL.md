---
name: debian-buildd-monitor
version: 1
summary: Monitor Debian package build status across architectures via buildd
category: debian
description: Use when tracking buildd.debian.org build status for a package across all architectures. Uses getbuildlog.
author: Vasudev Kamath
license: GPL-3.0
metadata:
  hermes:
    tags: [debian, buildd, build-status, getbuildlog, architecture]
    related_skills: [debian-acceptance-monitor, debian-debci-monitor, debci-api]
---

# Debian Buildd Status Monitor

Monitor build status of a package across all architectures on buildd.debian.org.

## When to Use

- After package accepted into unstable (use debian-acceptance-monitor first)
- Track build progress across all release architectures
- Identify failed builds and fetch error logs
- Monitor porter architectures (riscv64, mips64el, etc.)

## Prerequisites

- `getbuildlog` (from devscripts package)
- `rmadison` for suite verification
- Internet access to buildd.debian.org

## Quick Reference

| Tool | Purpose |
|------|---------|
| `getbuildlog` | Fetch build logs from buildd.debian.org |
| `rmadison` | Verify package in buildd-unstable |
| `terminal` | Run commands |

## Monitoring Script

`scripts/monitor-buildd.sh` — Check build status across all architectures.

**Usage:**
```bash
./monitor-buildd.sh <package> <version>
```

**Exit codes:**
- 0 = all builds passed or pending (no failures)
- 1 = at least one architecture failed
- 2 = error

**Example output:**
```
=== Buildd Status for smartctl-exporter 0.15.0-2 ===
ARCH         STATUS         DETAILS
amd64        ✅ PASSED      2026-11-14T15:28:13Z
arm64        ✅ PASSED      2026-11-14T15:27:25Z
...
riscv64      ⏳ PENDING     Needs-Build or not scheduled

Summary: 7 passed, 0 failed, 1 pending
```

## Cron Job Configuration

```yaml
schedule: "30m"
skills: ["debian-buildd-monitor"]
script: "monitor-buildd.sh"
continuity: true
deliver: "origin"
```

## Procedure

1. Verify package in `buildd-unstable` via `rmadison`
2. For each release architecture, run `getbuildlog <package> <version> <arch>`
3. Parse log for `Status: successful` / `Status: failed` / `Needs-Build`
4. Report summary table

## Architectures Monitored

Release arches: `amd64 arm64 armhf ppc64el s390x riscv64 loong64 i386`
Porter arches (if applicable): `mips64el alpha hppa ...`

## Pitfalls

- Builds can take hours to appear after archive acceptance
- `Needs-Build` = not yet scheduled, not a failure
- Porter arches often `BD-Uninstallable` due to missing build-deps
- Re-run with `--git-ignore-new` if source tree has uncommitted changes

## References

- `debian-acceptance-monitor` — prerequisite: package must be accepted first
- `debian-debci-monitor` — next step: autopkgtest CI after builds complete
- https://buildd.debian.org/