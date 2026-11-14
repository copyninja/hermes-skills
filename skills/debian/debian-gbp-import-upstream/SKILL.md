---
name: debian-gbp-import-upstream
version: '1.0'
author: 'Vasudev Kamath'
license: 'MIT'
category: debian
description: Import new upstream version via gbp import-orig.
tags:
  - debian
  - gbp
  - import-orig
  - upstream
  - package-maintenance
related_skills:
  - gbp-upstream-push
  - debian-quilt-patch-management
  - debian-package-monitor
---

# debian-gbp-import-upstream Skill

Import a new upstream release into a Debian source package using `gbp import-orig`,
handling the gbp workflow, post-import hooks, and common failure modes.

## When to Use

- A new upstream release is available for a Debian package you maintain.
- The package uses `gbp` workflow with `upstream` branch and `pristine-tar`.
- You need to update the Debian package to the new upstream version.

## Prerequisites

- Debian source tree with gbp layout (branches: `upstream`, `debian/sid`/`master`, `pristine-tar`).
- `debian/watch` file configured for upstream releases.
- `DEBEMAIL` or `EMAIL` environment variable set (required for `gbp dch` post-import hook).
- `gbp` and `devscripts` (for `uscan`) installed.

## Quick Reference

| Task | Command |
|------|---------|
| Check current version | `head debian/changelog` |
| Check upstream releases | `uscan --verbose` or GitHub releases page |
| Verify new version available | `uscan --verbose --package <pkg> --upstream-version <ver>` |
| Import new version | `gbp import-orig --uscan --upstream-branch=upstream --upstream-version=<ver>` |
| Verify patch applies | `quilt push -a` |
| Check changelog | `head debian/changelog` |

## Procedure

### 1. Check Current State
```bash
cd /path/to/package
head -10 debian/changelog          # Current version in Debian
cat VERSION                         # Upstream version file (if exists)
git log --oneline -5               # Recent commits
```

### 2. Verify New Upstream Version
```bash
# Check if new version is available via uscan
uscan --verbose --package <pkg>

# Or specify version explicitly
uscan --verbose --package <pkg> --upstream-version=<new-ver>
```

### 3. Ensure Clean Working Tree
```bash
git status
# If uncommitted changes exist from previous failed import:
git reset --hard HEAD
git clean -fd
```

### 4. Run gbp import-orig
```bash
# Export DEBEMAIL for the post-import gbp dch hook
export DEBEMAIL="your@email.org"

gbp import-orig --uscan --upstream-branch=upstream --upstream-version=<new-ver>
```

**Options explained:**
- `--uscan`: Use uscan to download the tarball (respects debian/watch)
- `--upstream-branch=upstream`: Target branch for upstream source (default varies)
- `--upstream-version=<ver>`: Explicit version to avoid interactive prompt

### 5. Verify Import Result
```bash
# Check git history
git log --oneline -5
# Should show: "Update upstream source from tag 'upstream/<ver>'" and "New upstream version <ver>"

# Check changelog (will be SNAPSHOT/UNRELEASED)
head -15 debian/changelog

# Check VERSION file updated
cat VERSION

# Verify patches still apply
quilt push -a
```

### 6. Prepare for Release (Post-Import)
```bash
# Update changelog from SNAPSHOT to proper release
# Edit debian/changelog:
#   smartctl-exporter (0.15.0-1) unstable; urgency=medium
#   
#   * New upstream version 0.15.0
#   * [List key upstream changes from release notes]
# 
#  -- Your Name <email>  Date

# Build test (install build-deps first)
dpkg-buildpackage -us -uc -b

# Run autopkgtest
autopkgtest . -- null
```

## Common Pitfalls

### Post-Import Hook Fails: "Either 'EMAIL' or 'DEBEMAIL' must be set"
**Cause**: `gbp dch` (run as post-import hook) needs an email for the changelog entry.
**Fix**: Export `DEBEMAIL` before running `gbp import-orig`:
```bash
export DEBEMAIL="vasudev@debian.org"
gbp import-orig ...
```

### Repository Has Uncommitted Changes
**Cause**: Previous failed import left upstream source changes in working tree.
**Fix**: Reset and clean before retry:
```bash
git reset --hard HEAD
git clean -fd
```

### Upstream Branch Not Found
**Cause**: Local `upstream` branch doesn't exist or isn't tracking `origin/upstream`.
**Fix**: Create it:
```bash
git checkout upstream  # creates from origin/upstream
# Then run import-orig from debian/sid branch
```

### Patch No Longer Applies After Import
**Cause**: Upstream changed the patched file; patch context shifted.
**Fix**: 
```bash
quilt pop -a
git checkout <patched-file>  # restore from new upstream
quilt push -a                # will fail on changed patch
# Update the patch:
quilt add <file>
# ... edit file to match new upstream + Debian fix ...
quilt refresh
quilt pop -a && quilt push -a  # verify clean
```

### Changelog Version Is SNAPSHOT/UNRELEASED
**Cause**: `gbp dch` creates a snapshot version by default.
**Fix**: Manually edit `debian/changelog` to proper release format before building:
```
smartctl-exporter (0.15.0-1) unstable; urgency=medium
```

## Upstream Changes to Watch For

After import, check for:
- New build dependencies (update `debian/control` Build-Depends)
- Changed import paths (may need new patches or updated patches)
- New files needing installation (update `debian/install`)
- License changes (update `debian/copyright`)
- Man page / systemd unit changes

## Integration with Other Skills

- After import, if `upstream` branch diverged from remote: use `gbp-upstream-push`
- If patches need updating: use `debian-quilt-patch-management`
- For monitoring when new versions appear: use `debian-package-monitor`

## Verification Checklist

- [ ] `git log --oneline` shows new upstream commit and merge commit
- [ ] `upstream/<ver>` tag exists
- [ ] `pristine-tar` committed new orig tarball
- [ ] `debian/changelog` has new entry (edit to release format)
- [ ] `VERSION` / version file updated
- [ ] All patches apply cleanly (`quilt push -a`)
- [ ] `dpkg-buildpackage -us -uc -b` succeeds
- [ ] `autopkgtest` passes
