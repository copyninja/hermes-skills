---
name: debian-acceptance-monitor
version: 1
summary: Monitor Debian package acceptance into unstable via tracker/rmadison
category: debian
description: Use when tracking if a package version has been accepted into Debian unstable. Uses rmadison and tracker.debian.org.
author: Vasudev Kamath
license: GPL-3.0
metadata:
  hermes:
    tags: [debian, package, acceptance, tracker, rmadison]
    related_skills: [debian-buildd-monitor, debian-debci-monitor, debci-api]
---

# Debian Package Acceptance Monitor

Monitor when a package version is accepted into Debian unstable (or other suites).

## When to Use

- After uploading a new package version to track acceptance
- Wait for version to appear in unstable before proceeding to buildd monitoring
- Verify upload was processed by ftp-master

## Prerequisites

- `rmadison` (from devscripts package)
- Internet access to tracker.debian.org

## Quick Reference

| Tool | Purpose |
|------|---------|
| `rmadison` | Authoritative archive query (primary) |
| `web_extract` | tracker.debian.org HTML parsing (fallback) |
| `terminal` | Run rmadison |

## Monitoring Script

`scripts/monitor-acceptance.sh` — Check if package version is in unstable.

**Usage:**
```bash
./monitor-acceptance.sh <package> <version>
```

**Exit codes:**
- 0 = accepted in unstable
- 1 = not accepted
- 2 = error

**Example output:**
```
ACCEPTED: smartctl-exporter 0.15.0-2 in unstable
smartctl-exporter | 0.15.0-2 | unstable               | source
smartctl-exporter | 0.15.0-2 | buildd-unstable        | source
```

## Cron Job Configuration

```yaml
schedule: "30m"
skills: ["debian-acceptance-monitor"]
script: "monitor-acceptance.sh"
continuity: true
deliver: "origin"
```

## Procedure

1. Run `rmadison <package>` to get authoritative archive state
2. Check if target version appears under `unstable` suite
3. Report acceptance status with suite breakdown

## Pitfalls

- `rmadison` may have slight delay after ftp-master acceptance
- Use `tracker.debian.org/pkg/<package>` as fallback for human-readable view
- Only `unstable` (not `buildd-unstable` or `experimental`) means fully accepted

## References

- `debian-buildd-monitor` — next step after acceptance
- `debian-debci-monitor` — autopkgtest CI after builds complete